from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from inspect import signature
from types import SimpleNamespace
from uuid import UUID, uuid4

try:
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, interrupt
except ModuleNotFoundError:  # pragma: no cover - dependency exists in production env
    InMemorySaver = None
    END = START = StateGraph = None
    Command = interrupt = None

from src.schemas.agent import (
    AgentAction,
    AgentActionResumeRequest,
    AgentAnswer,
    AgentChatRequest,
    AgentChatResponse,
    AgentCitation,
    AgentFallback,
)
from src.schemas.agent import AgentGuardrail
from src.services.agent_action_commit_service import AgentActionCommitService
from src.services.agent_external_research_service import AgentExternalResearchService
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
from src.services.agent_prerequisite_path_service import AgentPrerequisitePathService
from src.services.agent_response_composer import AgentResponseComposer
from src.services.agent_search_scope_service import AgentSearchScopeService
from src.services.agent_slot_resolver import AgentSlotResolver
from src.services.agent_thread_memory_state import AgentThreadMemoryStateStore
from src.services.agent_tool_nodes import AgentToolNodes
from src.services.agentic_rag_pipeline import AgenticRAGPipeline
from src.services.agentic_rag_tools import AgenticRAGToolExecutor
from src.services.guardrail_router import (
    GuardrailDecision,
    GuardrailRouterUnavailableError,
    GuardrailScopePacket,
    build_guardrail_router_client,
    guardrail_user_message,
)
from src.services.guardrails.pii_guardrail import PIIGuardrailService
from src.services.language_normalization import get_input_language_normalizer
from src.services.language_normalization import LanguageNormalizationResult


RAG_AGENT_INTENTS = {
    "find_content",
    "explain_concept",
    "general_course_question",
    "navigate_to_unit",
}


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
        external_research_service=None,
        pii_guardrail_service=None,
        guardrail_router=None,
        language_normalizer=None,
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
        self.external_research = external_research_service or AgentExternalResearchService(
            responder=router
        )
        self.pii_guardrail = pii_guardrail_service or PIIGuardrailService()
        self.guardrail_router = guardrail_router or build_guardrail_router_client()
        self.language_normalizer = language_normalizer or get_input_language_normalizer()
        prerequisite_path_service = None
        if hasattr(search_service, "repo"):
            prerequisite_path_service = AgentPrerequisitePathService(
                search_service.repo,
                getattr(search_service, "navigation_service", None),
            )
        self.tools = AgentToolNodes(
            search_service,
            requirement_service,
            prerequisite_path_service=prerequisite_path_service,
            user_id=getattr(action_user, "id", None),
        )
        self.agentic_rag_tools = AgenticRAGToolExecutor(self.tools)
        self.agentic_rag = AgenticRAGPipeline(
            router=router,
            tool_executor=self.agentic_rag_tools,
        )
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
        graph.add_node("agentic_rag", self._agentic_rag)
        # Compatibility path for tests/bootstrap routers that have not adopted
        # the DeepTutor-style Agentic RAG stage contract yet. Production
        # StructuredAgentRouter implements rag_think/rag_act/rag_observe/rag_respond
        # and routes to the single agentic_rag node above.
        graph.add_node("rag_decide_tool", self._rag_decide_tool)
        graph.add_node("rag_execute_tool", self._rag_execute_tool)
        graph.add_node("rag_observe", self._rag_observe)
        graph.add_node("dispatch", self._dispatch)
        graph.add_node("await_confirmation", self._await_confirmation)
        graph.add_node("commit_action", self._commit_action)
        graph.add_edge(START, "route_intent")
        graph.add_edge("route_intent", "canonicalize_slots")
        graph.add_edge("canonicalize_slots", "policy_guard")
        graph.add_conditional_edges(
            "policy_guard",
            self._next_after_policy,
            {
                "agentic_rag": "agentic_rag",
                "rag_decide_tool": "rag_decide_tool",
                "dispatch": "dispatch",
            },
        )
        graph.add_edge("agentic_rag", END)
        graph.add_edge("rag_decide_tool", "rag_execute_tool")
        graph.add_edge("rag_execute_tool", "rag_observe")
        graph.add_edge("rag_observe", END)
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

    def _next_after_policy(self, state: dict) -> str:
        if self._should_use_rag_react(state):
            if self._router_supports_agentic_rag():
                return "agentic_rag"
            return "rag_decide_tool"
        return "dispatch"

    def _router_supports_agentic_rag(self) -> bool:
        return all(
            callable(getattr(self.router, name, None))
            for name in ("rag_think", "rag_act", "rag_observe", "rag_respond")
        )

    def _should_use_rag_react(self, state: dict) -> bool:
        policy = state.get("policy")
        if isinstance(policy, dict):
            policy = PolicyDecision.model_validate(policy)
        slots = state.get("slots")
        if isinstance(slots, dict):
            slots = AgentSlots.model_validate(slots)
        return (
            isinstance(policy, PolicyDecision)
            and policy.allow
            and state.get("intent") in RAG_AGENT_INTENTS
            and float(state.get("intent_confidence") or 0.0) >= 0.65
            and isinstance(slots, AgentSlots)
            and not slots.ambiguity_options
            and bool((slots.raw_topic or "").strip())
        )

    async def chat(
        self,
        request: AgentChatRequest,
        conversation_id: str,
        thread_id: str,
        user_id: str,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
    ) -> AgentChatResponse:
        sanitized_request, input_guardrail = self._sanitize_request(request)
        if input_guardrail.should_block:
            return self.composer.compose_guardrail_block(
                conversation_id=conversation_id,
                block_reason=input_guardrail.block_reason or "pii_input_blocked",
                error_code=input_guardrail.error_code,
            )
        normalized_language = await self.language_normalizer.normalize(sanitized_request.message)
        sanitized_request = sanitized_request.model_copy(
            update={"message": normalized_language.normalized_text}
        )
        pending_for_guardrail = await self._load_pending_clarification(
            conversation_id,
            user_id,
            thread_id,
        )
        assistant_context_for_guardrail = await self._load_guardrail_assistant_context(
            conversation_id,
            user_id,
        )
        guardrail_decision = await self._route_guardrail(
            message=sanitized_request.message,
            route_context=sanitized_request.route_context,
            allowed_course_ids=allowed_course_ids,
            current_path_course_ids=current_path_course_ids,
            pending_clarification=pending_for_guardrail,
            assistant_context=assistant_context_for_guardrail,
        )
        guardrail_response = self._compose_guardrail_response(
            conversation_id=conversation_id,
            decision=guardrail_decision,
        )
        if guardrail_response is not None:
            return guardrail_response

        if self.graph_repo is None:
            response = await self._invoke_graph_and_compose(
                request=sanitized_request,
                conversation_id=conversation_id,
                thread_id=thread_id,
                user_id=user_id,
                allowed_course_ids=allowed_course_ids,
                current_path_course_ids=current_path_course_ids,
            )
            response = await self._enforce_response_language(response, normalized_language)
            return self._sanitize_response(response, input_guardrail)

        completed = await self.graph_repo.get_completed_response_by_incoming_message(
            conversation_id=conversation_id,
            thread_id=thread_id,
            incoming_message_id=sanitized_request.incoming_message_id,
        )
        if completed is not None:
            return completed

        existing_run = None
        get_run = getattr(self.graph_repo, "get_run_by_incoming_message", None)
        if get_run is not None:
            existing_run = await get_run(
                conversation_id=conversation_id,
                thread_id=thread_id,
                incoming_message_id=sanitized_request.incoming_message_id,
            )
        lock_graph_run_id = (
            str(existing_run.id)
            if existing_run is not None and getattr(existing_run, "id", None) is not None
            else f"pending:{sanitized_request.incoming_message_id}"
        )
        async with self.thread_lock.acquire(
            conversation_id=conversation_id,
            thread_id=thread_id,
            graph_run_id=lock_graph_run_id,
        ):
            retrying_failed_run = False
            if existing_run is not None and getattr(existing_run, "status", None) == "failed_retryable":
                active_run = await self.graph_repo.get_active_run(thread_id=thread_id)
                if active_run is not None and active_run.graph_run_id != str(existing_run.id):
                    raise AgentInProgressError(conversation_id, thread_id, active_run.graph_run_id)
                run = SimpleNamespace(graph_run_id=str(existing_run.id))
                retrying_failed_run = True
            else:
                active_run = await self.graph_repo.get_active_run(thread_id=thread_id)
                if active_run is not None:
                    raise AgentInProgressError(conversation_id, thread_id, active_run.graph_run_id)

                run = await self.graph_repo.create_run(
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    incoming_message_id=sanitized_request.incoming_message_id,
                )
                if getattr(run, "existing", False):
                    if getattr(run, "status", None) == "succeeded" and getattr(run, "response_ref", None):
                        completed_after_race = await self.graph_repo.load_response_payload(run.response_ref)
                        if completed_after_race is not None:
                            return completed_after_race
                    if getattr(run, "status", None) == "failed_retryable":
                        retrying_failed_run = True
                    else:
                        raise AgentInProgressError(conversation_id, thread_id, run.graph_run_id)
            await self.graph_repo.mark_run_running(run.graph_run_id)
            try:
                if self.conversation_repo is not None and not retrying_failed_run:
                    await self.conversation_repo.add_message(
                        conversation_id=UUID(str(conversation_id)),
                        user_id=UUID(str(user_id)),
                        role="user",
                        markdown=sanitized_request.message,
                    )
                response = await self._invoke_graph_and_compose(
                    request=sanitized_request,
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    user_id=user_id,
                    allowed_course_ids=allowed_course_ids,
                    current_path_course_ids=current_path_course_ids,
                )
                response = await self._enforce_response_language(response, normalized_language)
                response = self._sanitize_response(response, input_guardrail)
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
                        thread_id=thread_id,
                    )
                response_ref = await self.graph_repo.store_response_payload(
                    graph_run_id=run.graph_run_id,
                    response=response,
                    deterministic_key=f"{thread_id}:{sanitized_request.incoming_message_id}",
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
                if isinstance(exc, AgentRouterUnavailableError):
                    await self._persist_failed_request_retry_clarification(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        thread_id=thread_id,
                        request=sanitized_request,
                        error=exc,
                    )
                raise

    def _sanitize_request(
        self,
        request: AgentChatRequest,
    ) -> tuple[AgentChatRequest, object]:
        result = self.pii_guardrail.sanitize_input(request.message)
        sanitized_request = request.model_copy(update={"message": result.sanitized_text})
        return sanitized_request, result

    async def _route_guardrail(
        self,
        *,
        message: str,
        route_context,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None,
        pending_clarification: PendingClarification | None = None,
        assistant_context: list[dict[str, Any]] | None = None,
    ) -> GuardrailDecision:
        try:
            decision = await self.guardrail_router.route(
                message=message,
                scope=self._build_agent_guardrail_scope(
                    route_context=route_context,
                    allowed_course_ids=allowed_course_ids,
                    current_path_course_ids=current_path_course_ids,
                    pending_clarification=pending_clarification,
                    assistant_context=assistant_context,
                ),
            )
            if self._should_allow_pending_retrieval_guardrail_followup(
                message=message,
                pending_clarification=pending_clarification,
                decision=decision,
            ):
                return GuardrailDecision.allow()
            if self._should_allow_recent_assistant_guardrail_followup(
                message=message,
                assistant_context=assistant_context or [],
                decision=decision,
            ):
                return GuardrailDecision.allow()
            return decision
        except GuardrailRouterUnavailableError as exc:
            raise AgentRouterUnavailableError(
                "guardrail_router_unavailable",
                exc.error_code,
            ) from exc

    @staticmethod
    def _build_agent_guardrail_scope(
        *,
        route_context,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None,
        pending_clarification: PendingClarification | None = None,
        assistant_context: list[dict[str, Any]] | None = None,
    ) -> GuardrailScopePacket:
        allowed_scope_summary = "Agent guardrail scope: current user query only."
        recent_context: list[dict[str, Any]] = []
        if assistant_context:
            allowed_scope_summary = (
                f"{allowed_scope_summary} Recent assistant context is provided only "
                "to interpret safe follow-up questions."
            )
            recent_context.extend(assistant_context[:2])
        if (
            pending_clarification is not None
            and pending_clarification.type == "slot_disambiguation"
            and pending_clarification.payload.get("kind") == "retrieval_query"
        ):
            proposed_topic = str(
                pending_clarification.payload.get("proposed_raw_topic") or ""
            ).strip()
            if proposed_topic:
                allowed_scope_summary = (
                    f"{allowed_scope_summary} Active pending retrieval topic is provided only "
                    "to interpret short follow-up refinements."
                )
                recent_context.append(
                    {
                        "type": "pending_retrieval_query",
                        "proposed_raw_topic": proposed_topic,
                        "original_intent": pending_clarification.payload.get("original_intent")
                        or "find_content",
                    }
                )
        return GuardrailScopePacket(
            feature="agent",
            scope_level="query",
            scope_id="agent",
            allowed_scope_summary=allowed_scope_summary,
            candidate_kps=[],
            recent_context=recent_context,
            selected_text="",
        )

    def _should_allow_pending_retrieval_guardrail_followup(
        self,
        *,
        message: str,
        pending_clarification: PendingClarification | None,
        decision: GuardrailDecision,
    ) -> bool:
        if decision.safety_label != "SAFE" or decision.action != "ASK_CLARIFY":
            return False
        if (
            pending_clarification is None
            or pending_clarification.type != "slot_disambiguation"
            or pending_clarification.payload.get("kind") != "retrieval_query"
        ):
            return False
        proposed_topic = str(
            pending_clarification.payload.get("proposed_raw_topic") or ""
        ).strip()
        return (
            self._coerce_pending_retrieval_detail_refinement(
                message=message,
                proposed_topic=proposed_topic,
                decision_action="clarify",
            )
            is not None
        )

    def _should_allow_recent_assistant_guardrail_followup(
        self,
        *,
        message: str,
        assistant_context: list[dict[str, Any]],
        decision: GuardrailDecision,
    ) -> bool:
        if decision.safety_label != "SAFE" or decision.action != "ASK_CLARIFY":
            return False
        if not assistant_context or len(str(message or "").split()) > 12:
            return False
        message_terms = self._normalized_terms(message)
        if not message_terms:
            return False

        context_parts: list[str] = []
        for item in assistant_context[:2]:
            if not isinstance(item, dict):
                continue
            context_parts.append(str(item.get("markdown") or ""))
            for citation in item.get("citations") or []:
                if not isinstance(citation, dict):
                    continue
                context_parts.extend(
                    str(citation.get(key) or "")
                    for key in ("course_id", "unit_name", "lecture_title")
                )
            for action in item.get("actions") or []:
                if not isinstance(action, dict):
                    continue
                context_parts.extend(
                    str(action.get(key) or "")
                    for key in ("type", "label", "canonical_unit_id")
                )
        context_terms = self._normalized_terms(" ".join(context_parts))
        return bool(message_terms & context_terms)

    @staticmethod
    def _compose_guardrail_response(
        *,
        conversation_id: str,
        decision: GuardrailDecision,
    ) -> AgentChatResponse | None:
        if decision.action == "ALLOW_LESSON_ANSWER":
            return None
        return AgentChatResponse(
            conversation_id=conversation_id,
            message_id=str(uuid4()),
            answer=AgentAnswer(
                markdown=guardrail_user_message(decision),
                confidence="fallback",
            ),
            fallback=AgentFallback(
                reason="unsafe_action",
                message="The request was stopped by the guardrail router before agent routing.",
            ),
            guardrail=AgentGuardrail(
                blocked=True,
                blockReason=decision.action,
            ),
        )

    def _sanitize_response(
        self,
        response: AgentChatResponse,
        input_guardrail,
    ) -> AgentChatResponse:
        output_guardrail = self.pii_guardrail.sanitize_output(response.answer.markdown)
        sanitized_answer = response.answer.model_copy(update={"markdown": output_guardrail.sanitized_text})

        existing_guardrail = response.guardrail or AgentGuardrail()
        merged_guardrail = existing_guardrail.model_copy(
            update={
                "input_redacted": existing_guardrail.input_redacted or input_guardrail.was_redacted,
                "output_redacted": existing_guardrail.output_redacted or output_guardrail.was_redacted,
                "blocked": existing_guardrail.blocked or output_guardrail.should_block,
                "block_reason": existing_guardrail.block_reason or output_guardrail.block_reason,
                "error_code": existing_guardrail.error_code or input_guardrail.error_code or output_guardrail.error_code,
            }
        )

        return response.model_copy(
            update={
                "answer": sanitized_answer,
                "guardrail": merged_guardrail,
            }
        )

    async def _enforce_response_language(
        self,
        response: AgentChatResponse,
        language: LanguageNormalizationResult,
    ) -> AgentChatResponse:
        if language.target_language != "en" or not response.answer.markdown.strip():
            return response
        detect = getattr(self.language_normalizer, "detect", None)
        if detect is None or detect(response.answer.markdown) == "en":
            return response
        translator = getattr(self.language_normalizer, "translator", None)
        translate = getattr(translator, "translate_to_english", None)
        if translate is None:
            return response
        try:
            translated = await translate(response.answer.markdown)
        except Exception:
            return response
        if not translated.strip():
            return response
        return response.model_copy(
            update={"answer": response.answer.model_copy(update={"markdown": translated})}
        )

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
        state["recent_messages"] = await self._load_recent_message_context(
            conversation_id,
            user_id,
        )
        state["pending_clarification"] = await self._load_pending_clarification(
            conversation_id,
            user_id,
            thread_id,
        )
        state["memory_ref"] = await self._load_memory_ref(conversation_id, user_id, thread_id)
        if request.tool_mode == "web_papers":
            result = await self.external_research.answer(
                message=request.message,
                recent_messages=state["recent_messages"],
            )
            return self.composer.compose(
                conversation_id=conversation_id,
                message_id=str(uuid4()),
                result=result,
            )
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
        if (
            pending is not None
            and pending.type == "slot_disambiguation"
            and pending.payload.get("kind") == "failed_request_retry"
        ):
            pending_result = self._resolve_pending_failed_request_retry(state, pending)
            if pending_result is not None:
                return pending_result
        if (
            pending is not None
            and pending.type == "slot_disambiguation"
            and pending.payload.get("kind") == "retrieval_query"
        ):
            pending_result = self._resolve_pending_retrieval_query(state, pending)
            if pending_result is not None:
                return pending_result
        if (
            pending is not None
            and pending.type == "slot_disambiguation"
            and pending.payload.get("kind") == "path_selection"
        ):
            pending_result = self._resolve_pending_path_selection(state, pending)
            if pending_result is not None:
                return pending_result
        if (
            pending is not None
            and pending.type == "slot_disambiguation"
            and pending.payload.get("kind") == "topic_selection"
        ):
            pending_result = self._resolve_pending_topic_selection(state, pending)
            if pending_result is not None:
                return pending_result
        if pending is not None and pending.type == "search_scope_expansion":
            pending_result = self._resolve_pending_scope_expansion(state, pending)
            if pending_result is not None:
                return pending_result

        route = self._promote_contextual_rag_followup(
            self._route_with_recent_context(state["message"], state),
            state,
        )
        return {
            **state,
            "intent": route.intent,
            "intent_confidence": route.confidence,
            "slots": route.extracted_slots,
            "clarification_question": route.clarification_question,
            "candidate_intent": route.candidate_intent,
        }

    def _resolve_pending_failed_request_retry(
        self,
        state: dict,
        pending: PendingClarification,
    ) -> dict | None:
        payload = pending.payload
        decision = self._resolve_pending_followup_decision(state, pending)

        if decision.action == "new_request":
            return self._route_new_request_after_pending(state)
        if decision.action == "clarify":
            return {
                **state,
                "intent": "clarify",
                "intent_confidence": 0.0,
                "slots": AgentSlots(),
                "pending_clarification": pending,
                "clarification_question": decision.clarification_question
                or "Please clarify whether you want me to retry the failed request or ask something new.",
            }
        if decision.action == "reject":
            return {
                **state,
                "intent": "assistant_help",
                "intent_confidence": 1.0,
                "slots": AgentSlots(),
                "pending_clarification": None,
                "clarification_question": None,
            }

        retry_message = (
            decision.refined_query
            if decision.action == "refine" and decision.refined_query
            else payload.get("original_message")
        )
        retry_message = str(retry_message or "").strip()
        if not retry_message:
            return {
                **state,
                "intent": "clarify",
                "intent_confidence": 0.0,
                "slots": AgentSlots(),
                "pending_clarification": pending,
                "clarification_question": "Please restate the request you want me to retry.",
            }

        route = self._route_with_recent_context(retry_message, state)
        return {
            **state,
            "message": retry_message,
            "intent": route.intent,
            "intent_confidence": route.confidence,
            "slots": route.extracted_slots,
            "clarification_question": route.clarification_question,
            "candidate_intent": route.candidate_intent,
            "pending_clarification": None,
        }

    def _route_with_recent_context(self, message: str, state: dict):
        route = self.router.route
        try:
            parameters = signature(route).parameters
        except (TypeError, ValueError):
            parameters = {}
        if "recent_messages" in parameters:
            return route(
                message=message,
                route_context=state.get("route_context"),
                recent_messages=state.get("recent_messages") or [],
            )
        return route(message=message, route_context=state.get("route_context"))

    def _promote_contextual_rag_followup(self, route: AgentRoute, state: dict) -> AgentRoute:
        if route.intent != "clarify" or route.candidate_intent not in RAG_AGENT_INTENTS:
            return route
        if len(str(state.get("message") or "").split()) > 8:
            return route
        active = self._active_recent_citation(state)
        if active is None:
            return route
        if self._message_names_unmatched_explicit_topic(state.get("message"), active):
            return route
        return route.model_copy(
            update={
                "intent": route.candidate_intent or "find_content",
                "confidence": max(route.confidence, 0.8),
                "extracted_slots": AgentSlots(
                    raw_topic=active.unit_name,
                    search_queries=[active.unit_name],
                    search_scope="current_path",
                ),
                "clarification_question": None,
            }
        )

    def _resolve_pending_retrieval_query(
        self,
        state: dict,
        pending: PendingClarification,
    ) -> dict | None:
        payload = pending.payload
        message = state["message"].strip()
        proposed = str(payload.get("proposed_raw_topic") or "").strip()
        decision = self._resolve_pending_followup_decision(state, pending)

        if decision.action == "new_request":
            return self._route_new_request_after_pending(state)
        if decision.action == "reject":
            return {
                **state,
                "intent": "clarify",
                "intent_confidence": 0.0,
                "slots": AgentSlots(),
                "pending_clarification": None,
                "clarification_question": (
                    "Okay. Please describe the topic or concept you want me to search for."
                ),
            }
        force_short_detail_refinement = decision.action == "clarify" or (
            decision.action == "refine"
            and len(str(getattr(decision, "refined_query", "") or "").split()) > 8
        )
        forced_refinement = (
            self._coerce_pending_retrieval_detail_refinement(
                message=message,
                proposed_topic=proposed,
                decision_action=decision.action,
            )
            if force_short_detail_refinement
            else None
        )
        short_detail_refinement = bool(forced_refinement and proposed)
        if forced_refinement:
            decision = SimpleNamespace(
                action="refine",
                refined_query=forced_refinement,
                clarification_question=None,
            )
        if decision.action == "clarify":
            return {
                **state,
                "intent": "clarify",
                "intent_confidence": 0.0,
                "slots": AgentSlots(),
                "pending_clarification": pending,
                "clarification_question": decision.clarification_question
                or "Please clarify what you want me to search for.",
            }
        if decision.action == "approve" and not proposed:
            return {
                **state,
                "intent": "clarify",
                "intent_confidence": 0.0,
                "slots": AgentSlots(),
                "pending_clarification": pending,
                "clarification_question": (
                    "Please add the topic or concept name so I can search accurately."
                ),
            }

        if decision.action == "approve":
            raw_topic = proposed or message
            scope_expansion_approved = True
        elif decision.action == "refine":
            raw_topic = (decision.refined_query or message).strip()
            scope_expansion_approved = False
        else:
            raw_topic = message
            scope_expansion_approved = False
        search_queries = [raw_topic] if raw_topic else []
        if proposed and proposed.casefold() not in {query.casefold() for query in search_queries}:
            search_queries.append(proposed)
        return {
            **state,
            "intent": payload.get("original_intent") or "find_content",
            "intent_confidence": 1.0,
            "slots": AgentSlots(
                raw_topic=raw_topic,
                search_queries=search_queries,
                target_path=payload.get("target_path"),
                requested_path_id=payload.get("requested_path_id"),
                search_scope=payload.get("search_scope") or "current_path",
                resolved_search_path_ids=payload.get("resolved_search_path_ids") or [],
                excluded_search_path_ids=payload.get("excluded_search_path_ids") or [],
                scope_expansion_approved=scope_expansion_approved,
                show_top_results_approved=decision.action == "approve" or short_detail_refinement,
            ),
            "pending_clarification": None,
            "clarification_question": None,
        }

    def _coerce_pending_retrieval_detail_refinement(
        self,
        *,
        message: str,
        proposed_topic: str,
        decision_action: str,
    ) -> str | None:
        detail = re.sub(r"\s+", " ", message).strip(" .")
        if decision_action not in {"clarify", "refine"} or not proposed_topic or not detail:
            return None
        if len(detail.split()) > 8:
            return None
        if "?" in detail:
            return None
        if re.search(r"\b(yes|no|ok|okay|sure|show|see|cancel|stop|retry)\b", detail, re.IGNORECASE):
            return None
        return f"{proposed_topic} {detail}"

    def _resolve_pending_scope_expansion(
        self,
        state: dict,
        pending: PendingClarification,
    ) -> dict | None:
        payload = pending.payload
        decision = self._resolve_pending_followup_decision(state, pending)
        if decision.action == "new_request":
            return self._route_new_request_after_pending(state)
        if decision.action == "approve":
            slots = AgentSlots(
                raw_topic=payload.get("raw_topic") or payload.get("original_message", state["message"]),
                search_queries=[query for query in [payload.get("raw_topic")] if query],
                search_scope="expanded_paths",
                scope_expansion_approved=True,
                resolved_search_path_ids=payload.get("allowed_path_ids", []),
                excluded_search_path_ids=payload.get("current_path_ids", []),
            )
            return {
                **state,
                "intent": "find_content",
                "intent_confidence": 1.0,
                "slots": slots,
                "pending_clarification": None,
            }
        if decision.action == "refine":
            slots = AgentSlots(
                raw_topic=decision.refined_query or payload.get("raw_topic") or state["message"],
                search_queries=[decision.refined_query] if decision.refined_query else [],
                search_scope="current_path",
                resolved_search_path_ids=payload.get("current_path_ids", []),
            )
            return {
                **state,
                "intent": "find_content",
                "intent_confidence": 1.0,
                "slots": slots,
                "pending_clarification": None,
            }
        if decision.action == "reject":
            return {
                **state,
                "intent": "clarify",
                "intent_confidence": 0.0,
                "slots": AgentSlots(),
                "pending_clarification": None,
                "clarification_question": (
                    "Okay, I will keep the search scoped to your current path. "
                    "Please add a course, unit, or topic if you want me to try again there."
                ),
            }
        return {
            **state,
            "intent": "clarify",
            "intent_confidence": 0.0,
            "slots": AgentSlots(),
            "pending_clarification": pending,
            "clarification_question": decision.clarification_question
            or "Please clarify whether you want me to expand the search or refine the topic.",
        }

    def _route_new_request_after_pending(self, state: dict) -> dict:
        route = self._route_with_recent_context(state["message"], state)
        return {
            **state,
            "intent": route.intent,
            "intent_confidence": route.confidence,
            "slots": route.extracted_slots,
            "clarification_question": route.clarification_question,
            "candidate_intent": route.candidate_intent,
            "pending_clarification": None,
        }

    def _resolve_pending_followup_decision(self, state: dict, pending: PendingClarification):
        resolver = getattr(self.router, "resolve_pending_followup", None)
        if resolver is None:
            raise AgentRouterUnavailableError("agent_pending_followup_model_missing")
        try:
            parameters = signature(resolver).parameters
        except (TypeError, ValueError):
            parameters = {}
        if "recent_messages" in parameters:
            return resolver(
                state["message"],
                pending.payload,
                state.get("route_context"),
                recent_messages=state.get("recent_messages") or [],
            )
        return resolver(
            state["message"],
            pending.payload,
            state.get("route_context"),
        )

    def _resolve_pending_path_selection(
        self,
        state: dict,
        pending: PendingClarification,
    ) -> dict | None:
        payload = pending.payload
        message = state["message"].strip()
        normalized = message.lower()
        options = [str(path_id) for path_id in payload.get("path_options", [])]
        selected_path_id = ""
        if normalized.startswith("choose_path:"):
            selected_path_id = normalized.split(":", 1)[1].strip()
        else:
            selected_path_id = next(
                (
                    path_id
                    for path_id in options
                    if normalized == path_id.lower()
                    or normalized == self.scope_service.path_label(path_id).lower()
                ),
                "",
            )
        if selected_path_id not in options:
            return {
                **state,
                "intent": "clarify",
                "intent_confidence": 0.0,
                "slots": AgentSlots(),
                "pending_clarification": pending,
                "clarification_question": "Please choose one of the paths shown below.",
            }
        raw_topic = str(payload.get("raw_topic") or payload.get("original_message") or "").strip()
        return {
            **state,
            "intent": payload.get("original_intent") or "find_content",
            "intent_confidence": 1.0,
            "slots": AgentSlots(
                raw_topic=raw_topic,
                target_path=selected_path_id,
                requested_path_id=selected_path_id,
                search_scope="explicit_path",
                resolved_search_path_ids=[selected_path_id],
            ),
            "pending_clarification": None,
            "clarification_question": None,
        }

    def _resolve_pending_topic_selection(
        self,
        state: dict,
        pending: PendingClarification,
    ) -> dict | None:
        payload = pending.payload
        message = state["message"].strip()
        normalized = message.lower()
        options = [str(unit_id) for unit_id in payload.get("topic_options", [])]
        selected_unit_id = ""
        if normalized.startswith("choose_topic:"):
            selected_unit_id = message.split(":", 1)[1].strip()
        if selected_unit_id not in options:
            return self._route_new_request_after_pending(state)
        unit_names = payload.get("topic_names") or {}
        unit_name = str(unit_names.get(selected_unit_id) or payload.get("raw_topic") or "").strip()
        return {
            **state,
            "intent": payload.get("original_intent") or "find_content",
            "intent_confidence": 1.0,
            "slots": AgentSlots(
                raw_topic=unit_name or selected_unit_id,
                search_queries=[query for query in [unit_name] if query] or [selected_unit_id],
                canonical_unit_ids=[selected_unit_id],
                target_path=payload.get("target_path"),
                requested_path_id=payload.get("requested_path_id"),
                search_scope=payload.get("search_scope") or "current_path",
                resolved_search_path_ids=payload.get("resolved_search_path_ids") or [],
                excluded_search_path_ids=payload.get("excluded_search_path_ids") or [],
                topic_choice_approved=True,
            ),
            "pending_clarification": None,
            "clarification_question": None,
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

    async def _agentic_rag(self, state: dict) -> dict:
        slots = state["slots"]
        if isinstance(slots, dict):
            slots = AgentSlots.model_validate(slots)
        slots = self._slots_with_active_citation_for_followup(state, slots)
        result = await self.agentic_rag.run(
            message=state["message"],
            intent=state["intent"],
            slots=slots,
            route_context=state.get("route_context"),
            recent_messages=state.get("recent_messages") or [],
            allowed_course_ids=state["allowed_course_ids"],
        )
        update: dict = {**state, "slots": slots, "tool_result": result}
        return self._attach_rag_pending_clarification(update, result, slots)

    def _slots_with_active_citation_for_followup(
        self,
        state: dict,
        slots: AgentSlots,
    ) -> AgentSlots:
        if len(str(state.get("message") or "").split()) > 12:
            return slots
        active = self._active_recent_citation(state)
        if active is None or not active.canonical_unit_id:
            return slots
        if self._message_names_unmatched_explicit_topic(state.get("message"), active):
            return slots
        if not self._active_citation_matches_rag_query({**state, "slots": slots}, active):
            return slots

        canonical_unit_ids = [
            active.canonical_unit_id,
            *[
                unit_id
                for unit_id in slots.canonical_unit_ids
                if unit_id != active.canonical_unit_id
            ],
        ]
        search_queries = [
            active.unit_name,
            *[query for query in slots.search_queries if query != active.unit_name],
        ]
        return slots.model_copy(
            update={
                "raw_topic": active.unit_name,
                "search_queries": search_queries[:5],
                "canonical_unit_ids": canonical_unit_ids[:3],
            }
        )

    async def _rag_decide_tool(self, state: dict) -> dict:
        slots = state["slots"]
        if isinstance(slots, dict):
            slots = AgentSlots.model_validate(slots)
        planner = getattr(self.router, "plan_rag_tool", None)
        observations = state.get("rag_observations") or []
        if planner is None:
            fallback_queries = slots.search_queries or [slots.raw_topic or state["message"]]
            tool_call = SimpleNamespace(
                tool="search_units_by_title",
                query=fallback_queries[0],
                search_queries=fallback_queries,
                clarification_question=None,
                rationale="Compatibility fallback: search title-level units for the routed topic.",
                preserve_raw_topic=True,
            )
        else:
            tool_call = planner(
                message=state["message"],
                intent=state["intent"],
                slots=slots,
                route_context=state.get("route_context"),
                recent_messages=state.get("recent_messages") or [],
                observations=observations,
            )
        tool_call = self._override_rag_clarification_with_active_citation(state, tool_call)
        return {
            **state,
            "slots": slots,
            "rag_tool_call": self._model_dump_like(tool_call),
            "rag_observations": observations,
        }

    def _override_rag_clarification_with_active_citation(self, state: dict, tool_call):
        if self._value_from(tool_call, "tool", "") != "ask_clarification":
            return tool_call
        if len(str(state.get("message") or "").split()) > 8:
            return tool_call
        active = self._active_recent_citation(state)
        if active is None:
            return tool_call
        if self._message_names_unmatched_explicit_topic(state.get("message"), active):
            return tool_call
        return {
            "tool": "search_units_by_title",
            "query": active.unit_name,
            "search_queries": [active.unit_name],
            "clarification_question": None,
            "rationale": (
                "Graph guard: a short follow-up has an active cited source, so search the "
                "active source title before asking for clarification."
            ),
        }

    async def _rag_execute_tool(self, state: dict) -> dict:
        slots = state["slots"]
        if isinstance(slots, dict):
            slots = AgentSlots.model_validate(slots)
        tool_call = state.get("rag_tool_call") or {}
        tool_name = self._value_from(tool_call, "tool", "")
        if tool_name == "ask_clarification":
            question = self._value_from(
                tool_call,
                "clarification_question",
                "Could you clarify the topic you want me to search for?",
            )
            result = await self.tools.clarify(state["message"], reason=question)
            return {
                **state,
                "tool_result": result,
                "rag_observations": self._append_rag_observation(
                    state.get("rag_observations") or [],
                    result,
                    tool_name,
                ),
            }
        if tool_name != "search_units_by_title":
            result = await self.tools.clarify(
                state["message"],
                reason="The agent selected an unsupported retrieval tool.",
            )
            return {
                **state,
                "tool_result": result,
                "rag_observations": self._append_rag_observation(
                    state.get("rag_observations") or [],
                    result,
                    "unsupported_tool",
                ),
            }

        search_queries = [
            str(query).strip()
            for query in self._value_from(tool_call, "search_queries", []) or []
            if str(query).strip()
        ]
        query = str(self._value_from(tool_call, "query", "") or "").strip()
        if query and query.casefold() not in {item.casefold() for item in search_queries}:
            search_queries.insert(0, query)
        if not search_queries:
            search_queries = slots.search_queries or [slots.raw_topic or state["message"]]
        search_slots = slots.model_copy(
            update={
                "raw_topic": slots.raw_topic
                if self._value_from(tool_call, "preserve_raw_topic", False)
                else query or slots.raw_topic,
                "search_queries": search_queries[:5],
            }
        )
        result = await self.tools.find_content(
            state["message"],
            state["intent"],
            search_slots,
            state["allowed_course_ids"],
        )
        active_result = self._recent_citation_result(
            {**state, "slots": search_slots, "rag_tool_call": tool_call},
            result,
        )
        if active_result is not None and result.citations:
            active = active_result.citations[0]
            matched_citations = [
                citation
                for citation in result.citations
                if self._citation_matches_active_context(citation, active)
            ]
            if matched_citations:
                matched_ids = {citation.canonical_unit_id for citation in matched_citations}
                result = result.model_copy(
                    update={
                        "citations": matched_citations[:3],
                        "actions": [
                            action
                            for action in result.actions
                            if not action.canonical_unit_id or action.canonical_unit_id in matched_ids
                        ][:3],
                        "metadata": {
                            **result.metadata,
                            "discarded_context_mismatched_results": len(matched_citations)
                            < len(result.citations),
                        },
                        "trace": result.trace.model_copy(
                            update={
                                "selected_unit_ids": [
                                    citation.canonical_unit_id for citation in matched_citations[:3]
                                ]
                            }
                        )
                        if result.trace
                        else result.trace,
                    }
                )
            else:
                result = active_result.model_copy(
                    update={
                        "metadata": {
                            **active_result.metadata,
                            "discarded_context_mismatched_results": True,
                        }
                    }
                )
        if not result.citations:
            active_result = self._recent_citation_result(
                {**state, "slots": search_slots, "rag_tool_call": tool_call},
                result,
            )
            if active_result is not None:
                result = active_result
        return {
            **state,
            "slots": search_slots,
            "tool_result": result,
            "rag_observations": self._append_rag_observation(
                state.get("rag_observations") or [],
                result,
                tool_name,
            ),
        }

    async def _rag_observe(self, state: dict) -> dict:
        result = state["tool_result"]
        if isinstance(result, dict):
            result = ToolResult.model_validate(result)
        slots = state["slots"]
        if isinstance(slots, dict):
            slots = AgentSlots.model_validate(slots)
        if result.citations and (
            result.requires_evidence or result.metadata.get("evidence_verdict") == "related_match"
        ):
            result = self._compose_rag_final_answer(state, result)
        if result.citations and self._is_followup_question_text(result.answer_markdown):
            result = result.model_copy(
                update={
                    "answer_markdown": self._compose_source_limited_answer(state, result),
                    "requires_evidence": False,
                    "metadata": {
                        **result.metadata,
                        "answer_confidence": "partial",
                        "replaced_followup_question": True,
                    },
                }
            )
        update: dict = {**state, "slots": slots, "tool_result": result}
        return self._attach_rag_pending_clarification(update, result, slots)

    def _compose_rag_final_answer(self, state: dict, result: ToolResult) -> ToolResult:
        composer = getattr(self.router, "compose_react_final", None)
        if composer is not None:
            answer = composer(
                message=state["message"],
                tool_result=result,
                route_context=state.get("route_context"),
                recent_messages=state.get("recent_messages") or [],
                observations=state.get("rag_observations") or [],
            )
        else:
            compose_grounded = getattr(self.router, "compose_grounded_answer", None)
            if compose_grounded is None:
                return result
            answer = compose_grounded(
                state["message"],
                [citation.model_dump(mode="json") for citation in result.citations],
            )
        if isinstance(answer, str):
            return result.model_copy(update={"answer_markdown": answer})
        if getattr(answer, "evidence_sufficient", False):
            return result.model_copy(update={"answer_markdown": answer.answer_markdown})
        answer_markdown = (
            getattr(answer, "clarification_question", None)
            or getattr(answer, "answer_markdown", None)
            or "I could not find a direct grounded source for that request."
        )
        confidence = getattr(answer, "confidence", "no_source")
        if result.citations and self._is_followup_question_text(answer_markdown):
            return result.model_copy(
                update={
                    "answer_markdown": self._compose_source_limited_answer(state, result),
                    "requires_evidence": False,
                    "metadata": {
                        **result.metadata,
                        "answer_confidence": "partial",
                        "grounding_evidence_sufficient": False,
                        "replaced_followup_question": True,
                    },
                }
            )
        if confidence == "partial":
            return result.model_copy(
                update={
                    "answer_markdown": answer_markdown,
                    "requires_evidence": False,
                    "metadata": {
                        **result.metadata,
                        "answer_confidence": "partial",
                        "grounding_evidence_sufficient": False,
                    },
                }
            )
        return result.model_copy(
            update={
                "answer_markdown": answer_markdown,
                "citations": [],
                "actions": [],
                "requires_evidence": confidence == "no_source",
                "metadata": {
                    **result.metadata,
                    "grounding_evidence_sufficient": False,
                },
            }
        )

    def _is_followup_question_text(self, text: str | None) -> bool:
        value = str(text or "").strip().lower()
        if not value:
            return False
        return value.endswith("?") or value.startswith(
            (
                "do you want",
                "would you like",
                "which ",
                "what ",
                "bạn muốn",
                "bạn có muốn",
                "bạn cần",
            )
        )

    def _compose_source_limited_answer(self, state: dict, result: ToolResult) -> str:
        composer = getattr(self.router, "compose_source_limited_answer", None)
        if composer is None:
            raise AgentRouterUnavailableError("agent_source_limited_model_missing")
        answer = composer(
            message=state["message"],
            tool_result=result,
            route_context=state.get("route_context"),
            recent_messages=state.get("recent_messages") or [],
            observations=state.get("rag_observations") or [],
        )
        if isinstance(answer, str):
            return answer
        return getattr(answer, "answer_markdown", str(answer))

    def _attach_rag_pending_clarification(
        self,
        update: dict,
        result: ToolResult,
        slots: AgentSlots,
    ) -> dict:
        if result.metadata.get("too_many_results_offered"):
            compose_refinement = getattr(self.router, "compose_retrieval_refinement", None)
            if compose_refinement is None:
                raise AgentRouterUnavailableError("agent_retrieval_refinement_model_missing")
            result = result.model_copy(
                update={
                    "answer_markdown": compose_refinement(
                        message=update["message"],
                        raw_topic=result.metadata.get("raw_topic") or slots.raw_topic,
                        result_count=int(result.metadata.get("result_count") or 0),
                        route_context=update.get("route_context"),
                    ),
                    "warning": None,
                }
            )
            update["tool_result"] = result
            update["pending_clarification"] = PendingClarification(
                clarification_id=f"clar_{uuid4()}",
                type="slot_disambiguation",
                status="awaiting_response",
                payload={
                    "kind": "retrieval_query",
                    "original_intent": update["intent"],
                    "original_message": update["message"],
                    "proposed_raw_topic": slots.raw_topic,
                    "target_path": slots.target_path,
                    "requested_path_id": slots.requested_path_id,
                    "search_scope": slots.search_scope,
                    "resolved_search_path_ids": slots.resolved_search_path_ids,
                    "excluded_search_path_ids": slots.excluded_search_path_ids,
                    "show_top_results_allowed": True,
                    "result_count": result.metadata.get("result_count"),
                },
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        if result.metadata.get("scope_expansion_offered"):
            allowed_paths = self.scope_service.path_ids_for_courses(update["allowed_course_ids"])
            update["pending_clarification"] = PendingClarification(
                clarification_id=f"clar_{uuid4()}",
                type="search_scope_expansion",
                status="awaiting_response",
                payload={
                    "original_message": update["message"],
                    "raw_topic": slots.raw_topic,
                    "allowed_path_ids": allowed_paths,
                    "current_path_ids": slots.resolved_search_path_ids,
                },
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        if result.metadata.get("path_selection_offered"):
            update["pending_clarification"] = PendingClarification(
                clarification_id=f"clar_{uuid4()}",
                type="slot_disambiguation",
                status="awaiting_response",
                payload={
                    "kind": "path_selection",
                    "original_intent": update["intent"],
                    "original_message": update["message"],
                    "raw_topic": slots.raw_topic,
                    "path_options": result.metadata.get("path_options", []),
                },
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        if result.metadata.get("topic_selection_offered"):
            topic_actions = [
                action
                for action in result.actions
                if action.type == "choose_topic" and action.canonical_unit_id
            ]
            update["pending_clarification"] = PendingClarification(
                clarification_id=f"clar_{uuid4()}",
                type="slot_disambiguation",
                status="awaiting_response",
                payload={
                    "kind": "topic_selection",
                    "original_intent": update["intent"],
                    "original_message": update["message"],
                    "raw_topic": slots.raw_topic,
                    "target_path": slots.target_path,
                    "requested_path_id": slots.requested_path_id,
                    "search_scope": slots.search_scope,
                    "resolved_search_path_ids": slots.resolved_search_path_ids,
                    "excluded_search_path_ids": slots.excluded_search_path_ids,
                    "topic_options": [action.canonical_unit_id for action in topic_actions],
                    "topic_names": {
                        action.canonical_unit_id: action.label.removeprefix("Learn about ").strip()
                        for action in topic_actions
                        if action.canonical_unit_id
                    },
                },
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        return update

    def _append_rag_observation(
        self,
        observations: list,
        result: ToolResult,
        tool_name: str,
    ) -> list[dict]:
        return [
            *observations,
            {
                "tool": tool_name,
                "result_kind": result.kind,
                "citation_count": len(result.citations),
                "action_count": len(result.actions),
                "metadata": result.metadata,
                "citations": [
                    {
                        "course_id": citation.course_id,
                        "unit_name": citation.unit_name,
                        "learn_href": citation.learn_href,
                    }
                    for citation in result.citations[:5]
                ],
            },
        ]

    def _recent_citation_result(self, state: dict, original_result: ToolResult) -> ToolResult | None:
        if len(str(state.get("message") or "").split()) > 8:
            return None
        active = self._active_recent_citation(state)
        if active is None:
            return None
        if self._message_names_unmatched_explicit_topic(state.get("message"), active):
            return None
        if not self._active_citation_matches_rag_query(state, active):
            return None
        citations: list[AgentCitation] = [active]
        actions: list[AgentAction] = []
        for message in reversed(state.get("recent_messages") or []):
            for action_payload in message.get("actions") or []:
                try:
                    actions.append(AgentAction.model_validate(action_payload))
                except Exception:
                    continue
            if actions:
                break
        citation_ids = {citation.canonical_unit_id for citation in citations}
        metadata = {
            key: value
            for key, value in original_result.metadata.items()
            if key
            not in {
                "too_many_results_offered",
                "result_count",
                "top_results_allowed",
                "scope_expansion_offered",
                "path_selection_offered",
            }
        }
        return ToolResult(
            kind="find_content",
            answer_markdown=None,
            citations=citations[:3],
            actions=[
                action
                for action in actions
                if not action.canonical_unit_id or action.canonical_unit_id in citation_ids
            ][:3],
            requires_evidence=True,
            metadata={
                **metadata,
                "evidence_verdict": "active_context_reuse",
                "reused_recent_citations": True,
            },
            trace=original_result.trace,
        )

    def _active_citation_matches_rag_query(self, state: dict, active: AgentCitation) -> bool:
        active_text = " ".join(
            part
            for part in [
                active.unit_name,
                active.lecture_title,
            ]
            if part
        )
        active_terms = self._normalized_terms(active_text)
        active_compact = re.sub(r"[^a-z0-9]+", "", active_text.lower())
        if not active_terms and not active_compact:
            return False

        candidates: list[str] = []
        slots = state.get("slots")
        if isinstance(slots, dict):
            slots = AgentSlots.model_validate(slots)
        if isinstance(slots, AgentSlots):
            candidates.extend(slots.search_queries or [])
            if slots.raw_topic:
                candidates.append(slots.raw_topic)

        tool_call = state.get("rag_tool_call") or {}
        query = self._value_from(tool_call, "query", None)
        if query:
            candidates.append(str(query))
        candidates.extend(
            str(item)
            for item in self._value_from(tool_call, "search_queries", []) or []
            if str(item).strip()
        )

        for candidate in candidates:
            candidate_terms = self._normalized_terms(candidate)
            if not candidate_terms:
                continue
            candidate_compact = re.sub(r"[^a-z0-9]+", "", str(candidate).lower())
            if candidate_compact and candidate_compact in active_compact:
                return True
            if any(term in active_terms for term in candidate_terms):
                return True
        return False

    def _citation_matches_active_context(
        self,
        citation: AgentCitation,
        active: AgentCitation,
    ) -> bool:
        if citation.canonical_unit_id == active.canonical_unit_id:
            return True
        active_terms = self._normalized_terms(active.unit_name)
        citation_terms = self._normalized_terms(citation.unit_name)
        if active_terms and citation_terms and active_terms.intersection(citation_terms):
            return True
        active_compact = re.sub(r"[^a-z0-9]+", "", active.unit_name.lower())
        citation_compact = re.sub(r"[^a-z0-9]+", "", citation.unit_name.lower())
        return bool(
            active_compact
            and citation_compact
            and (active_compact in citation_compact or citation_compact in active_compact)
        )

    def _normalized_terms(self, text: str | None) -> set[str]:
        terms: set[str] = set()
        for raw_term in re.findall(r"[a-zA-Z0-9]+", str(text or "")):
            raw = raw_term.lower()
            if len(raw) > 3 or (len(raw) > 2 and raw_term.isupper()):
                terms.add(raw)
        for compactable in re.findall(r"[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)+", str(text or "").lower()):
            compacted = re.sub(r"[^a-z0-9]+", "", compactable)
            if len(compacted) > 2:
                terms.add(compacted)
        return terms

    def _active_recent_citation(self, state: dict) -> AgentCitation | None:
        candidates: list[AgentCitation] = []
        for message in reversed(state.get("recent_messages") or []):
            for citation_payload in message.get("citations") or []:
                try:
                    candidates.append(AgentCitation.model_validate(citation_payload))
                except Exception:
                    continue
            if candidates:
                break
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda citation: self._citation_message_match_score(
                state.get("message"),
                citation,
            ),
        )

    def _citation_message_match_score(
        self,
        message: str | None,
        citation: AgentCitation,
    ) -> int:
        message_terms = self._normalized_terms(message)
        if not message_terms:
            return 0
        citation_text = " ".join(
            part
            for part in [
                citation.unit_name,
                citation.lecture_title,
            ]
            if part
        )
        citation_terms = self._normalized_terms(citation_text)
        return len(message_terms.intersection(citation_terms))

    def _message_names_unmatched_explicit_topic(
        self,
        message: str | None,
        active: AgentCitation,
    ) -> bool:
        active_terms = self._normalized_terms(active.unit_name)
        for raw_term in re.findall(r"[a-zA-Z][a-zA-Z0-9]*", str(message or "")):
            if len(raw_term) <= 2 or not raw_term.isupper():
                continue
            if raw_term.lower() not in active_terms:
                return True
        return False

    def _model_dump_like(self, value):
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "__dict__"):
            return dict(value.__dict__)
        return value

    def _value_from(self, value, key: str, default=None):
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

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
            update = {**state, "tool_result": result}
            if (
                state.get("candidate_intent")
                in {"find_content", "explain_concept", "general_course_question", "navigate_to_unit"}
                and not (slots.raw_topic or "").strip()
            ):
                update["pending_clarification"] = self._build_retrieval_query_clarification(
                    state,
                    slots,
                    original_intent=state["candidate_intent"],
                )
            return update

        if state["intent"] == "assistant_help":
            compose_help = getattr(self.router, "compose_assistant_help", None)
            if compose_help is None:
                raise AgentRouterUnavailableError("agent_assistant_help_model_missing")
            try:
                parameters = signature(compose_help).parameters
            except (TypeError, ValueError):
                parameters = {}
            if "recent_messages" in parameters:
                help_markdown = compose_help(
                    state["message"],
                    state.get("route_context"),
                    recent_messages=state.get("recent_messages") or [],
                )
            else:
                help_markdown = compose_help(state["message"], state.get("route_context"))
            result = await self.tools.assistant_help(help_markdown)
            return {**state, "tool_result": result}

        if state["intent"] in {
            "find_content",
            "explain_concept",
            "general_course_question",
            "navigate_to_unit",
        }:
            if not (slots.raw_topic or "").strip():
                result = await self.tools.clarify(
                    state["message"],
                    reason=state.get("clarification_question")
                    or "Which topic or concept should I search for?",
                )
                return {
                    **state,
                    "tool_result": result,
                    "pending_clarification": self._build_retrieval_query_clarification(
                        state,
                        slots,
                        original_intent=state["intent"],
                    ),
                }
            result = await self.tools.find_content(
                state["message"],
                state["intent"],
                slots,
                state["allowed_course_ids"],
            )
            if result.citations and (
                result.requires_evidence or result.metadata.get("evidence_verdict") == "related_match"
            ):
                compose_grounded = getattr(self.router, "compose_grounded_answer", None)
                if compose_grounded is not None:
                    grounded_answer = compose_grounded(
                        state["message"],
                        [citation.model_dump(mode="json") for citation in result.citations],
                    )
                    if isinstance(grounded_answer, str):
                        result = result.model_copy(update={"answer_markdown": grounded_answer})
                    elif getattr(grounded_answer, "evidence_sufficient", False):
                        result = result.model_copy(
                            update={"answer_markdown": grounded_answer.answer_markdown}
                        )
                    else:
                        answer_markdown = (
                            getattr(grounded_answer, "clarification_question", None)
                            or getattr(grounded_answer, "answer_markdown", None)
                            or "I could not find a direct grounded source for that request."
                        )
                        if slots.search_scope in {"explicit_path", "expanded_paths"}:
                            result = result.model_copy(
                                update={
                                    "answer_markdown": answer_markdown,
                                    "requires_evidence": False,
                                    "metadata": {
                                        **result.metadata,
                                        "answer_confidence": "partial",
                                        "grounding_evidence_sufficient": False,
                                    },
                                }
                            )
                        elif slots.search_scope == "current_path" and len(state["allowed_course_ids"]) > len(
                            state.get("current_path_course_ids") or []
                        ):
                            result = ToolResult(
                                kind="clarification",
                                answer_markdown=(
                                    "I could not find a direct match in your current path. "
                                    "Do you want me to expand the search to other allowed paths?"
                                ),
                                warning=result.warning,
                                fallback=result.fallback,
                                requires_evidence=False,
                                metadata={
                                    **result.metadata,
                                    "scope_expansion_offered": True,
                                    "grounding_evidence_sufficient": False,
                                },
                                trace=result.trace,
                            )
                        elif getattr(grounded_answer, "confidence", "no_source") == "partial":
                            result = result.model_copy(
                                update={
                                    "answer_markdown": answer_markdown,
                                    "requires_evidence": False,
                                    "metadata": {
                                        **result.metadata,
                                        "answer_confidence": "partial",
                                        "grounding_evidence_sufficient": False,
                                    },
                                }
                            )
                        else:
                            result = result.model_copy(
                                update={
                                    "answer_markdown": answer_markdown,
                                    "citations": [],
                                    "actions": [],
                                    "requires_evidence": getattr(
                                        grounded_answer,
                                        "confidence",
                                        "no_source",
                                    )
                                    == "no_source",
                                    "metadata": {
                                        **result.metadata,
                                        "grounding_evidence_sufficient": False,
                                    },
                                }
                            )
            update: dict = {**state, "tool_result": result}
            if result.metadata.get("too_many_results_offered"):
                compose_refinement = getattr(self.router, "compose_retrieval_refinement", None)
                if compose_refinement is None:
                    raise AgentRouterUnavailableError("agent_retrieval_refinement_model_missing")
                result = result.model_copy(
                    update={
                        "answer_markdown": compose_refinement(
                            message=state["message"],
                            raw_topic=result.metadata.get("raw_topic") or slots.raw_topic,
                            result_count=int(result.metadata.get("result_count") or 0),
                            route_context=state.get("route_context"),
                        ),
                        "warning": None,
                    }
                )
                update["tool_result"] = result
            if result.metadata.get("scope_expansion_offered"):
                allowed_paths = self.scope_service.path_ids_for_courses(state["allowed_course_ids"])
                update["pending_clarification"] = PendingClarification(
                    clarification_id=f"clar_{uuid4()}",
                    type="search_scope_expansion",
                    status="awaiting_response",
                    payload={
                        "original_message": state["message"],
                        "raw_topic": slots.raw_topic,
                        "allowed_path_ids": allowed_paths,
                        "current_path_ids": slots.resolved_search_path_ids,
                    },
                    expires_at=datetime.now(UTC) + timedelta(minutes=30),
                )
            if result.metadata.get("path_selection_offered"):
                update["pending_clarification"] = PendingClarification(
                    clarification_id=f"clar_{uuid4()}",
                    type="slot_disambiguation",
                    status="awaiting_response",
                    payload={
                        "kind": "path_selection",
                        "original_intent": state["intent"],
                        "original_message": state["message"],
                        "raw_topic": slots.raw_topic,
                        "path_options": result.metadata.get("path_options", []),
                    },
                    expires_at=datetime.now(UTC) + timedelta(minutes=30),
                )
            if result.metadata.get("topic_selection_offered"):
                topic_actions = [
                    action
                    for action in result.actions
                    if action.type == "choose_topic" and action.canonical_unit_id
                ]
                update["pending_clarification"] = PendingClarification(
                    clarification_id=f"clar_{uuid4()}",
                    type="slot_disambiguation",
                    status="awaiting_response",
                    payload={
                        "kind": "topic_selection",
                        "original_intent": state["intent"],
                        "original_message": state["message"],
                        "raw_topic": slots.raw_topic,
                        "target_path": slots.target_path,
                        "requested_path_id": slots.requested_path_id,
                        "search_scope": slots.search_scope,
                        "resolved_search_path_ids": slots.resolved_search_path_ids,
                        "excluded_search_path_ids": slots.excluded_search_path_ids,
                        "topic_options": [action.canonical_unit_id for action in topic_actions],
                        "topic_names": {
                            action.canonical_unit_id: action.label.removeprefix("Learn about ").strip()
                            for action in topic_actions
                            if action.canonical_unit_id
                        },
                    },
                    expires_at=datetime.now(UTC) + timedelta(minutes=30),
                )
            if result.metadata.get("too_many_results_offered"):
                update["pending_clarification"] = PendingClarification(
                    clarification_id=f"clar_{uuid4()}",
                    type="slot_disambiguation",
                    status="awaiting_response",
                    payload={
                        "kind": "retrieval_query",
                        "original_intent": state["intent"],
                        "original_message": state["message"],
                        "proposed_raw_topic": slots.raw_topic,
                        "target_path": slots.target_path,
                        "requested_path_id": slots.requested_path_id,
                        "search_scope": slots.search_scope,
                        "resolved_search_path_ids": slots.resolved_search_path_ids,
                        "excluded_search_path_ids": slots.excluded_search_path_ids,
                        "show_top_results_allowed": True,
                        "result_count": result.metadata.get("result_count"),
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
            if self.path_switch_service is not None and slots.target_path:
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

    def _build_retrieval_query_clarification(
        self,
        state: dict,
        slots: AgentSlots,
        *,
        original_intent: str,
    ) -> PendingClarification:
        return PendingClarification(
            clarification_id=f"clar_{uuid4()}",
            type="slot_disambiguation",
            status="awaiting_response",
            payload={
                "kind": "retrieval_query",
                "original_intent": original_intent,
                "original_message": state["message"],
                "proposed_raw_topic": slots.raw_topic,
                "target_path": slots.target_path,
                "requested_path_id": slots.requested_path_id,
                "search_scope": slots.search_scope,
                "resolved_search_path_ids": slots.resolved_search_path_ids,
                "clarification_question": state.get("clarification_question"),
            },
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )

    async def _persist_failed_request_retry_clarification(
        self,
        *,
        conversation_id: str,
        user_id: str,
        thread_id: str,
        request: AgentChatRequest,
        error: Exception,
    ) -> None:
        pending = PendingClarification(
            clarification_id=f"clar_{uuid4()}",
            type="slot_disambiguation",
            status="awaiting_response",
            payload={
                "kind": "failed_request_retry",
                "original_message": request.message,
                "original_incoming_message_id": request.incoming_message_id,
                "error": str(error),
            },
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        await self._persist_pending_clarification(
            conversation_id=conversation_id,
            user_id=user_id,
            thread_id=thread_id,
            pending=pending,
        )

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
            payload["current_course_ids"] = state.get("current_path_course_ids") or []
            payload["allowed_course_ids"] = state.get("allowed_course_ids") or []
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

    async def _load_memory_ref(self, conversation_id: str, user_id: str, thread_id: str) -> str | None:
        return await self.thread_memory.load_memory_ref(conversation_id, user_id, thread_id)

    async def _load_recent_message_context(self, conversation_id: str, user_id: str) -> list[dict]:
        if self.conversation_repo is None or not hasattr(self.conversation_repo, "list_messages"):
            return []
        messages = await self.conversation_repo.list_messages(
            UUID(str(conversation_id)),
            UUID(str(user_id)),
            limit=8,
        )
        recent = messages[-8:]
        context: list[dict] = []
        for message in recent:
            markdown = str(getattr(message, "markdown", "") or "")
            context.append(
                {
                    "role": getattr(message, "role", "unknown"),
                    "markdown": markdown[:1200],
                    "citations": getattr(message, "citations_json", None) or [],
                    "actions": getattr(message, "actions_json", None) or [],
                }
            )
        return context

    async def _load_guardrail_assistant_context(
        self,
        conversation_id: str,
        user_id: str,
    ) -> list[dict[str, Any]]:
        if self.conversation_repo is None or not hasattr(self.conversation_repo, "list_messages"):
            return []
        messages = await self.conversation_repo.list_messages(
            UUID(str(conversation_id)),
            UUID(str(user_id)),
            limit=4,
        )
        context: list[dict] = []
        for message in reversed(messages):
            if getattr(message, "role", "") != "assistant":
                continue
            markdown = str(getattr(message, "markdown", "") or "").strip()
            citations = [
                {
                    key: citation.get(key)
                    for key in ("course_id", "unit_name", "lecture_title")
                    if citation.get(key)
                }
                for citation in (getattr(message, "citations_json", None) or [])[:5]
                if isinstance(citation, dict)
            ]
            actions = [
                {
                    key: action.get(key)
                    for key in ("type", "label", "canonical_unit_id")
                    if action.get(key)
                }
                for action in (getattr(message, "actions_json", None) or [])[:5]
                if isinstance(action, dict)
            ]
            if not markdown and not citations and not actions:
                continue
            context.append(
                {
                    "type": "recent_assistant_response",
                    "markdown": markdown[:800],
                    "citations": citations,
                    "actions": actions,
                }
            )
            if len(context) >= 2:
                break
        return list(reversed(context))

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

    async def _compact_thread_memory_if_needed(
        self,
        conversation_id: str,
        user_id: str,
        thread_id: str,
    ) -> None:
        await self.thread_memory.compact_if_needed(conversation_id, user_id, thread_id)

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
