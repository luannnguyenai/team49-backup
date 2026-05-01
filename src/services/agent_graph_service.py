from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

try:
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, StateGraph
except ModuleNotFoundError:  # pragma: no cover - dependency exists in production env
    InMemorySaver = None
    END = START = StateGraph = None

from src.schemas.agent import AgentActionResumeRequest, AgentChatRequest, AgentChatResponse
from src.services.agent_graph_contracts import (
    AgentCheckpointState,
    AgentInProgressError,
    AgentSlots,
    PendingClarification,
    PolicyDecision,
)
from src.services.agent_policy_service import AgentPolicyService
from src.services.agent_response_composer import AgentResponseComposer
from src.services.agent_search_scope_service import AgentSearchScopeService
from src.services.agent_slot_resolver import AgentSlotResolver
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
        action_db=None,
        action_user=None,
    ):
        self.search_service = search_service
        self.requirement_service = requirement_service
        self.router = router
        self.graph_repo = graph_repo
        self.thread_lock = thread_lock or _NoopThreadLock()
        self.conversation_repo = conversation_repo
        self.path_switch_service = path_switch_service
        self.action_db = action_db
        self.action_user = action_user
        self.policy = AgentPolicyService()
        self.composer = AgentResponseComposer()
        self.scope_service = AgentSearchScopeService()
        self.tools = AgentToolNodes(search_service, requirement_service)
        self._checkpointer = InMemorySaver() if InMemorySaver is not None else None
        self._graph = self._build_graph() if StateGraph is not None else None
        self._pending_clarifications: dict[str, PendingClarification] = {}

    def _build_graph(self):
        if StateGraph is None:
            raise RuntimeError("langgraph_not_installed")
        graph = StateGraph(dict)
        graph.add_node("route_intent", self._route_intent)
        graph.add_node("canonicalize_slots", self._canonicalize_slots)
        graph.add_node("policy_guard", self._policy_guard)
        graph.add_node("dispatch", self._dispatch)
        graph.add_edge(START, "route_intent")
        graph.add_edge("route_intent", "canonicalize_slots")
        graph.add_edge("canonicalize_slots", "policy_guard")
        graph.add_edge("policy_guard", "dispatch")
        graph.add_edge("dispatch", END)
        return graph.compile(checkpointer=self._checkpointer)

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
                        citations=[citation.model_dump() for citation in response.citations],
                        actions=[action.model_dump() for action in response.actions],
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
                    )
                else:
                    await self.graph_repo.mark_run_succeeded(
                        run.graph_run_id,
                        response_ref=response_ref,
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
        state["pending_clarification"] = self._pending_clarifications.get(thread_id)
        if self._graph is None:
            raise RuntimeError("langgraph_not_installed")
        final_state = await self._graph.ainvoke(
            state,
            config={"configurable": {"thread_id": thread_id}},
        )
        pending = final_state.get("pending_clarification")
        if isinstance(pending, PendingClarification):
            self._pending_clarifications[thread_id] = pending
        elif pending is None:
            self._pending_clarifications.pop(thread_id, None)
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
            result = await self.tools.clarify(state["message"])
            return {**state, "tool_result": result}

        if state["intent"] in {"find_content", "explain_concept", "general_course_question"}:
            result = await self.tools.find_content(
                state["message"],
                state["intent"],
                slots,
                state["allowed_course_ids"],
            )
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
            result = await self.tools.path_switch_proposal(slots)
            result = await self._persist_pending_action_for_result(state, result, "request_path_switch")
            return {**state, "tool_result": result}

        return {**state, "tool_result": await self.tools.clarify(state["message"])}

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
        payload = {
            "payload_version": 1,
            "canonical_unit_ids": action.canonical_unit_ids,
            "target_path_id": state["slots"].target_path if hasattr(state["slots"], "target_path") else None,
            "intent": state["intent"],
        }
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
        if pending.expires_at <= datetime.now(UTC):
            await self.graph_repo.mark_action_expired(pending.action_id)
            return self.composer.compose_action_error(request.conversation_id, "expired")
        if request.decision == "reject":
            await self.graph_repo.mark_action_cancelled(pending.action_id)
            return self.composer.compose_action_cancelled(str(pending.conversation_id))
        existing = await self.graph_repo.get_committed_action_result(pending.action_id)
        if existing is not None:
            return AgentChatResponse(
                conversation_id=str(pending.conversation_id),
                message_id=str(uuid4()),
                answer={"markdown": "Action was already completed.", "confidence": "partial"},
            )
        if pending.type == "request_path_switch" and self.path_switch_service is not None:
            if self.action_db is None or self.action_user is None:
                return self.composer.compose_action_error(request.conversation_id, "missing_action_context")
            result = await self.path_switch_service.commit(
                self.action_db,
                self.action_user,
                pending.payload_json["target_path_id"],
                pending.idempotency_key,
            )
            await self.graph_repo.mark_action_committed(pending.action_id, result=result)
            return AgentChatResponse(
                conversation_id=str(pending.conversation_id),
                message_id=str(uuid4()),
                answer={
                    "markdown": (
                        "I switched your active path and recalculated the learning plan. "
                        "Open the plan view to continue with the updated recommendation."
                    ),
                    "confidence": "partial",
                },
            )
        await self.graph_repo.mark_action_committed(
            pending.action_id,
            result={"type": pending.type, "status": "confirmed"},
        )
        return AgentChatResponse(
            conversation_id=str(pending.conversation_id),
            message_id=str(uuid4()),
            answer={"markdown": "Action confirmed.", "confidence": "partial"},
        )
