from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

try:
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, interrupt
except ModuleNotFoundError:  # pragma: no cover - dependency exists in production env
    InMemorySaver = None
    END = START = StateGraph = None
    Command = interrupt = None

from src.schemas.agent import AgentActionResumeRequest, AgentChatRequest, AgentChatResponse
from src.services.agent_action_commit_service import AgentActionCommitService
from src.services.agent_graph_contracts import (
    AgentCheckpointState,
    AgentInProgressError,
    AgentRouterUnavailableError,
    AgentSlots,
    PendingClarification,
    PolicyDecision,
    ToolResult,
)
from src.services.agent_memory_compaction_service import AgentMemoryCompactionService
from src.services.agent_pending_action_decision import AgentPendingActionDecisionService
from src.services.agent_policy_service import AgentPolicyService
from src.services.agent_response_composer import AgentResponseComposer
from src.services.agent_search_scope_service import AgentSearchScopeService
from src.services.agent_slot_resolver import AgentSlotResolver
from src.services.agent_thread_memory_state import AgentThreadMemoryStateStore
from src.services.agent_tool_nodes import AgentToolNodes


class _NoopLock:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _NoopThreadLock:
    def acquire(self, **kwargs):
        return _NoopLock()


class AgentGraphService:
    def __init__(
        self,
        search_service,
        requirement_service,
        router,
        graph_repo=None,
        thread_lock=None,
        conversation_repo=None,
        path_switch_service=None,
        action_commit_service=None,
        memory_compaction_service=None,
        action_db=None,
        action_user=None,
        checkpointer=None,
    ):
        self.search_service = search_service
        self.requirement_service = requirement_service
        self.router = router
        self.graph_repo = graph_repo
        self.thread_lock = thread_lock or _NoopThreadLock()
        self.conversation_repo = conversation_repo
        self.path_switch_service = path_switch_service
        self.action_commit_service = action_commit_service or AgentActionCommitService()
        self.memory_compaction = memory_compaction_service or AgentMemoryCompactionService()
        self.thread_memory = AgentThreadMemoryStateStore(
            conversation_repo,
            self.memory_compaction,
        )
        self.action_db = action_db
        self.action_user = action_user
        self.action_decisions = AgentPendingActionDecisionService(
            graph_repo=graph_repo,
            path_switch_service=path_switch_service,
            action_commit_service=self.action_commit_service,
            action_db=action_db,
            action_user=action_user,
        )
        self.policy = AgentPolicyService()
        self.composer = AgentResponseComposer()
        self.scope_service = AgentSearchScopeService()
        self.tools = AgentToolNodes(search_service, requirement_service)
        self._checkpointer = checkpointer or (InMemorySaver() if InMemorySaver is not None else None)
        self._graph = self._build_graph() if StateGraph is not None else None
        self._latest_checkpoint_ids: dict[str, str | None] = {}

    def _build_graph(self):
        if StateGraph is None:
            raise RuntimeError("langgraph_not_installed")
        graph = StateGraph(dict)
        graph.add_node("route_intent", self._route_intent)
        graph.add_node("canonicalize_slots", self._canonicalize_slots)
        graph.add_node("policy_guard", self._policy_guard)
        graph.add_node("dispatch", self._dispatch)
        graph.add_node("await_confirmation", self._await_confirmation)
        graph.add_node("commit_action", self._commit_action)
        graph.add_edge(START, "route_intent")
        graph.add_edge("route_intent", "canonicalize_slots")
        graph.add_edge("canonicalize_slots", "policy_guard")
        graph.add_edge("policy_guard", "dispatch")
        graph.add_conditional_edges(
            "dispatch",
            self._next_after_dispatch,
            {"await_confirmation": "await_confirmation", "end": END},
        )
        graph.add_edge("await_confirmation", "commit_action")
        graph.add_edge("commit_action", END)
        return graph.compile(checkpointer=self._checkpointer)

    def _next_after_dispatch(self, state: dict) -> str:
        result = state.get("tool_result")
        if isinstance(result, dict):
            result = ToolResult.model_validate(result)
        if isinstance(result, ToolResult) and any(
            getattr(action, "status", None) == "awaiting_confirmation" for action in result.actions
        ):
            return "await_confirmation"
        return "end"

    async def chat(
        self,
        request: AgentChatRequest,
        conversation_id: str,
        thread_id: str,
        user_id: str,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
    ) -> AgentChatResponse:
        if self.graph_repo is None:
            return await self._invoke_graph_and_compose(
                request=request,
                conversation_id=conversation_id,
                thread_id=thread_id,
                user_id=user_id,
                allowed_course_ids=allowed_course_ids,
                current_path_course_ids=current_path_course_ids,
            )

        completed = await self.graph_repo.get_completed_response_by_incoming_message(
            conversation_id=conversation_id,
            thread_id=thread_id,
            incoming_message_id=request.incoming_message_id,
        )
        if completed is not None:
            return completed

        active_run = await self.graph_repo.get_active_run(thread_id=thread_id)
        if active_run is not None:
            raise AgentInProgressError(conversation_id, thread_id, active_run.graph_run_id)

        run = await self.graph_repo.create_run(
            conversation_id=conversation_id,
            thread_id=thread_id,
            incoming_message_id=request.incoming_message_id,
        )
        async with self.thread_lock.acquire(
            conversation_id=conversation_id,
            thread_id=thread_id,
            graph_run_id=run.graph_run_id,
        ):
            await self.graph_repo.mark_run_running(run.graph_run_id)
            try:
                if self.conversation_repo is not None:
                    await self.conversation_repo.add_message(
                        conversation_id=UUID(str(conversation_id)),
                        user_id=UUID(str(user_id)),
                        role="user",
                        markdown=request.message,
                    )
                response = await self._invoke_graph_and_compose(
                    request=request,
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    user_id=user_id,
                    allowed_course_ids=allowed_course_ids,
                    current_path_course_ids=current_path_course_ids,
                )
                if self.conversation_repo is not None:
                    await self.conversation_repo.add_message(
                        conversation_id=UUID(str(conversation_id)),
                        user_id=UUID(str(user_id)),
                        role="assistant",
                        markdown=response.answer.markdown,
                        citations=[citation.model_dump(mode="json") for citation in response.citations],
                        actions=[action.model_dump(mode="json") for action in response.actions],
                    )
                    await self._compact_thread_memory_if_needed(
                        conversation_id=conversation_id,
                        user_id=user_id,
                    )
                response_ref = await self.graph_repo.store_response_payload(
                    graph_run_id=run.graph_run_id,
                    response=response,
                    deterministic_key=f"{thread_id}:{request.incoming_message_id}",
                )
                has_pending_action = any(
                    action.status == "awaiting_confirmation" for action in response.actions
                )
                if has_pending_action:
                    await self.graph_repo.mark_run_interrupted(
                        run.graph_run_id,
                        response_ref=response_ref,
                        checkpoint_id=self._latest_checkpoint_ids.get(thread_id),
                    )
                else:
                    await self.graph_repo.mark_run_succeeded(
                        run.graph_run_id,
                        response_ref=response_ref,
                        checkpoint_id=self._latest_checkpoint_ids.get(thread_id),
                    )
                return response
            except Exception as exc:
                await self.graph_repo.mark_run_failed(
                    run.graph_run_id,
                    error=str(exc),
                    retryable=True,
                )
                raise

    async def _invoke_graph_and_compose(
        self,
        *,
        request: AgentChatRequest,
        conversation_id: str,
        thread_id: str,
        user_id: str,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None,
    ) -> AgentChatResponse:
        state = AgentCheckpointState(
            thread_id=thread_id,
            conversation_id=conversation_id,
            user_id=user_id,
            incoming_message_id=request.incoming_message_id,
            route_context=request.route_context,
            trace_id=str(uuid4()),
        ).model_dump()
        state["message"] = request.message
        state["allowed_course_ids"] = allowed_course_ids
        state["current_path_course_ids"] = current_path_course_ids or allowed_course_ids
        state["pending_clarification"] = await self._load_pending_clarification(
            conversation_id,
            user_id,
            thread_id,
        )
        state["memory_ref"] = await self._load_memory_ref(conversation_id, user_id)
        if self._graph is None:
            raise RuntimeError("langgraph_not_installed")
        final_state = await self._graph.ainvoke(
            state,
            config={"configurable": {"thread_id": thread_id}},
        )
        self._latest_checkpoint_ids[thread_id] = await self._capture_checkpoint_id(thread_id)
        pending = self.thread_memory.coerce_pending_clarification(
            final_state.get("pending_clarification")
        )
        await self._persist_pending_clarification(
            conversation_id=conversation_id,
            user_id=user_id,
            thread_id=thread_id,
            pending=pending,
        )
        return self.composer.compose(
            conversation_id=conversation_id,
            message_id=str(uuid4()),
            result=final_state["tool_result"],
        )

    async def _route_intent(self, state: dict) -> dict:
        pending = state.get("pending_clarification")
        if isinstance(pending, dict):
            pending = PendingClarification.model_validate(pending)
        if self.scope_service.is_scope_expansion_approval(state["message"], pending):
            payload = pending.payload if pending else {}
            slots = AgentSlots(
                raw_topic=payload.get("original_message", state["message"]),
                search_scope="expanded_paths",
                scope_expansion_approved=True,
                resolved_search_path_ids=payload.get("allowed_path_ids", []),
            )
            return {
                **state,
                "intent": "find_content",
                "intent_confidence": 1.0,
                "slots": slots,
                "pending_clarification": None,
            }

        route = self.router.route(message=state["message"], route_context=state.get("route_context"))
        return {
            **state,
            "intent": route.intent,
            "intent_confidence": route.confidence,
            "slots": route.extracted_slots,
            "clarification_question": route.clarification_question,
        }

    async def _canonicalize_slots(self, state: dict) -> dict:
        slots = state["slots"]
        if isinstance(slots, dict):
            slots = AgentSlots.model_validate(slots)
        if state["intent_confidence"] < 0.65:
            return {**state, "slots": slots}
        resolver = AgentSlotResolver(self.search_service, self.scope_service)
        return {
            **state,
            "slots": await resolver.canonicalize(
                raw_slots=slots,
                intent=state["intent"],
                allowed_course_ids=state["allowed_course_ids"],
                current_path_course_ids=state.get("current_path_course_ids"),
            )
        }

    async def _policy_guard(self, state: dict) -> dict:
        slots = state["slots"]
        if isinstance(slots, dict):
            slots = AgentSlots.model_validate(slots)
        return {
            **state,
            "policy": self.policy.evaluate(
                intent=state["intent"],
                slots=slots,
                allowed_course_ids=state["allowed_course_ids"],
            )
        }

    async def _dispatch(self, state: dict) -> dict:
        policy = state["policy"]
        if isinstance(policy, dict):
            policy = PolicyDecision.model_validate(policy)
        slots = state["slots"]
        if isinstance(slots, dict):
            slots = AgentSlots.model_validate(slots)

        if not policy.allow:
            result = await self.tools.clarify(
                state["message"],
                reason=policy.user_safe_message or "Policy denied the request.",
            )
            return {**state, "tool_result": result}
        if state["intent_confidence"] < 0.65 or slots.ambiguity_options:
            result = await self.tools.clarify(
                state["message"],
                reason=state.get("clarification_question") or "ambiguous_target",
            )
            return {**state, "tool_result": result}

        if state["intent"] == "assistant_help":
            compose_help = getattr(self.router, "compose_assistant_help", None)
            if compose_help is None:
                raise AgentRouterUnavailableError("agent_assistant_help_model_missing")
            result = await self.tools.assistant_help(
                compose_help(state["message"], state.get("route_context"))
            )
            return {**state, "tool_result": result}

        if state["intent"] in {
            "find_content",
            "explain_concept",
            "general_course_question",
            "navigate_to_unit",
        }:
            result = await self.tools.find_content(
                state["message"],
                state["intent"],
                slots,
                state["allowed_course_ids"],
            )
            if result.requires_evidence and result.citations:
                compose_grounded = getattr(self.router, "compose_grounded_answer", None)
                if compose_grounded is not None:
                    answer_markdown = compose_grounded(
                        state["message"],
                        [citation.model_dump(mode="json") for citation in result.citations],
                    )
                    result = result.model_copy(update={"answer_markdown": answer_markdown})
            update: dict = {**state, "tool_result": result}
            if result.metadata.get("scope_expansion_offered"):
                allowed_paths = self.scope_service.path_ids_for_courses(state["allowed_course_ids"])
                update["pending_clarification"] = PendingClarification(
                    clarification_id=f"clar_{uuid4()}",
                    type="search_scope_expansion",
                    status="awaiting_response",
                    payload={
                        "original_message": state["message"],
                        "allowed_path_ids": allowed_paths,
                        "current_path_ids": slots.resolved_search_path_ids,
                    },
                    expires_at=datetime.now(UTC) + timedelta(minutes=30),
                )
            return update
        if state["intent"] == "explain_planner_decision":
            result = await self.tools.planner_decision(
                state["message"],
                slots,
                state["allowed_course_ids"],
                state["user_id"],
            )
            return {**state, "tool_result": result}
        if state["intent"] == "assess_knowledge":
            result = await self.tools.assessment_proposal(slots)
            result = await self._persist_pending_action_for_result(state, result, "start_assessment")
            return {**state, "tool_result": result}
        if state["intent"] == "request_replan":
            result = await self.tools.replan_proposal()
            result = await self._persist_pending_action_for_result(state, result, "request_replan")
            return {**state, "tool_result": result}
        if state["intent"] == "request_path_switch":
            if self.path_switch_service is not None:
                decision = await self.path_switch_service.validate_request(
                    UUID(str(state["user_id"])),
                    state.get("current_path_course_ids") or [],
                    slots.target_path,
                    state["allowed_course_ids"],
                )
                if not decision.allow:
                    result = await self.tools.clarify(
                        state["message"],
                        reason=decision.user_safe_message or "Path switch is not allowed.",
                    )
                    return {**state, "tool_result": result}
            result = await self.tools.path_switch_proposal(slots)
            result = await self._persist_pending_action_for_result(state, result, "request_path_switch")
            return {**state, "tool_result": result}

        return {**state, "tool_result": await self.tools.clarify(state["message"])}

    async def _await_confirmation(self, state: dict) -> dict:
        if interrupt is None:
            return {**state, "resume_decision": {"decision": "approve"}}
        result = state.get("tool_result")
        if isinstance(result, dict):
            result = ToolResult.model_validate(result)
        action = result.actions[0] if isinstance(result, ToolResult) and result.actions else None
        resume_decision = interrupt(
            {
                "type": "pending_action_confirmation",
                "action_id": getattr(action, "action_id", None),
                "action_type": getattr(action, "type", None),
                "summary": result.answer_markdown if isinstance(result, ToolResult) else None,
            }
        )
        return {**state, "resume_decision": resume_decision}

    async def _commit_action(self, state: dict) -> dict:
        decision = state.get("resume_decision") or {}
        action_id = decision.get("action_id")
        if not action_id or self.graph_repo is None:
            return {
                **state,
                "tool_result": ToolResult(
                    kind="clarification",
                    answer_markdown="That action can no longer be completed.",
                    requires_evidence=False,
                ),
            }
        pending = await self.graph_repo.get_pending_action(action_id=action_id)
        if pending is None:
            result = self.composer.compose_action_error(state["conversation_id"], "missing_action")
            return {
                **state,
                "tool_result": ToolResult(
                    kind="clarification",
                    answer_markdown=result.answer.markdown,
                    fallback=result.fallback,
                    requires_evidence=False,
                ),
            }
        result = await self._resolve_pending_action_decision(pending, decision)
        return {**state, "tool_result": result}

    async def _persist_pending_action_for_result(
        self,
        state: dict,
        result,
        action_type: str,
    ):
        if self.graph_repo is None or not result.actions:
            return result
        action = result.actions[0]
        expires_at = action.expires_at or datetime.now(UTC) + timedelta(minutes=30)
        payload = self._build_pending_action_payload(state, action, action_type)
        pending = await self.graph_repo.create_pending_action(
            conversation_id=state["conversation_id"],
            thread_id=state["thread_id"],
            user_id=state["user_id"],
            action_type=action_type,
            payload=payload,
            payload_version=1,
            idempotency_key=f"{state['thread_id']}:{state['incoming_message_id']}:{action_type}",
            expires_at=expires_at,
        )
        updated_action = action.model_copy(update={"action_id": pending.action_id})
        return result.model_copy(update={"actions": [updated_action, *result.actions[1:]]})

    def _build_pending_action_payload(self, state: dict, action, action_type: str) -> dict:
        slots = state["slots"]
        if isinstance(slots, dict):
            slots = AgentSlots.model_validate(slots)
        payload = {
            "payload_version": 1,
            "intent": state["intent"],
            "reason": state.get("message"),
        }
        if action_type == "start_assessment":
            payload.update(
                {
                    "canonical_unit_ids": action.canonical_unit_ids,
                    "phase": action.default_phase or "skip_verification",
                    "question_budget": action.question_budget or 15,
                }
            )
        elif action_type == "request_replan":
            payload.update(
                {
                    "assessment_session_id": None,
                    "source_canonical_unit_ids": action.source_canonical_unit_ids
                    or slots.canonical_unit_ids,
                    "dry_run": False,
                }
            )
        elif action_type == "request_path_switch":
            if self.path_switch_service is not None and slots.target_path:
                payload.update(
                    self.path_switch_service.build_proposal(
                        state.get("current_path_course_ids") or [],
                        slots.target_path,
                    )
                )
            else:
                payload["target_path_id"] = slots.target_path
        return payload

    async def resume_action(self, request: AgentActionResumeRequest, user_id: str) -> AgentChatResponse:
        if self.graph_repo is None:
            return AgentChatResponse(
                conversation_id=request.conversation_id,
                message_id=str(uuid4()),
                answer={"markdown": "Action confirmed.", "confidence": "partial"},
            )
        pending = await self.graph_repo.get_pending_action(action_id=request.action_id)
        if pending is None:
            return self.composer.compose_action_error(request.conversation_id, "missing_action")
        completed = await self.graph_repo.get_completed_response_by_incoming_message(
            conversation_id=str(pending.conversation_id),
            thread_id=str(pending.thread_id),
            incoming_message_id=request.incoming_message_id,
        )
        if completed is not None:
            return completed
        active_run = await self.graph_repo.get_active_non_interrupted_run(thread_id=str(pending.thread_id))
        if active_run is not None:
            raise AgentInProgressError(
                str(pending.conversation_id),
                str(pending.thread_id),
                active_run.graph_run_id,
            )
        if str(pending.user_id) != str(user_id):
            return self.composer.compose_action_error(request.conversation_id, "ownership_mismatch")
        if pending.status != "awaiting_confirmation":
            existing = await self.graph_repo.get_committed_action_result(pending.action_id)
            if existing is not None:
                return AgentChatResponse(
                    conversation_id=str(pending.conversation_id),
                    message_id=str(uuid4()),
                    answer={"markdown": "Action was already completed.", "confidence": "partial"},
                )
            return self.composer.compose_action_error(request.conversation_id, f"invalid_status:{pending.status}")
        run = await self.graph_repo.create_run(
            conversation_id=str(pending.conversation_id),
            thread_id=str(pending.thread_id),
            incoming_message_id=request.incoming_message_id,
        )
        async with self.thread_lock.acquire(
            conversation_id=str(pending.conversation_id),
            thread_id=str(pending.thread_id),
            graph_run_id=run.graph_run_id,
        ):
            await self.graph_repo.mark_run_running(run.graph_run_id)
            try:
                if self._graph is not None and Command is not None:
                    final_state = await self._graph.ainvoke(
                        Command(
                            resume={
                                "decision": request.decision,
                                "action_id": pending.action_id,
                                "user_id": user_id,
                                "edit_payload": request.edit_payload,
                            }
                        ),
                        config={"configurable": {"thread_id": str(pending.thread_id)}},
                    )
                    self._latest_checkpoint_ids[str(pending.thread_id)] = await self._capture_checkpoint_id(
                        str(pending.thread_id)
                    )
                    response = self.composer.compose(
                        conversation_id=str(pending.conversation_id),
                        message_id=str(uuid4()),
                        result=final_state["tool_result"],
                    )
                else:
                    result = await self._resolve_pending_action_decision(
                        pending,
                        {
                            "decision": request.decision,
                            "action_id": pending.action_id,
                            "user_id": user_id,
                            "edit_payload": request.edit_payload,
                        },
                    )
                    response = self.composer.compose(
                        conversation_id=str(pending.conversation_id),
                        message_id=str(uuid4()),
                        result=result,
                    )
                response_ref = await self.graph_repo.store_response_payload(
                    graph_run_id=run.graph_run_id,
                    response=response,
                    deterministic_key=f"{pending.thread_id}:{request.incoming_message_id}",
                )
                await self.graph_repo.mark_run_succeeded(
                    run.graph_run_id,
                    response_ref=response_ref,
                    checkpoint_id=self._latest_checkpoint_ids.get(str(pending.thread_id)),
                )
                return response
            except Exception as exc:
                await self.graph_repo.mark_run_failed(
                    run.graph_run_id,
                    error=str(exc),
                    retryable=True,
                )
                raise

    async def _finalize_interrupted_run(self, thread_id: str, status: str) -> None:
        await self.action_decisions.finalize_interrupted_run(thread_id, status)

    async def _resolve_pending_action_decision(self, pending, decision: dict) -> ToolResult:
        return await self.action_decisions.resolve(pending, decision)

    async def _load_memory_ref(self, conversation_id: str, user_id: str) -> str | None:
        return await self.thread_memory.load_memory_ref(conversation_id, user_id)

    def _coerce_pending_clarification(self, value) -> PendingClarification | None:
        return self.thread_memory.coerce_pending_clarification(value)

    async def _load_pending_clarification(
        self,
        conversation_id: str,
        user_id: str,
        thread_id: str,
    ) -> PendingClarification | None:
        return await self.thread_memory.load_pending_clarification(
            conversation_id,
            user_id,
            thread_id,
        )

    async def _persist_pending_clarification(
        self,
        *,
        conversation_id: str,
        user_id: str,
        thread_id: str,
        pending: PendingClarification | None,
    ) -> None:
        await self.thread_memory.persist_pending_clarification(
            conversation_id=conversation_id,
            user_id=user_id,
            thread_id=thread_id,
            pending=pending,
        )

    async def _compact_thread_memory_if_needed(self, conversation_id: str, user_id: str) -> None:
        await self.thread_memory.compact_if_needed(conversation_id, user_id)

    async def _capture_checkpoint_id(self, thread_id: str) -> str | None:
        if self._graph is None:
            return None
        try:
            snapshot = await self._graph.aget_state({"configurable": {"thread_id": thread_id}})
        except Exception:
            return None
        config = getattr(snapshot, "config", None) or {}
        configurable = config.get("configurable") if isinstance(config, dict) else None
        if not isinstance(configurable, dict):
            return None
        checkpoint_id = configurable.get("checkpoint_id")
        return str(checkpoint_id) if checkpoint_id else None
