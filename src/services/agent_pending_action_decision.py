from __future__ import annotations

from datetime import UTC, datetime

from src.services.agent_graph_contracts import ToolResult


class AgentPendingActionDecisionService:
    def __init__(
        self,
        *,
        graph_repo,
        path_switch_service,
        action_commit_service,
        action_db,
        action_user,
    ):
        self.graph_repo = graph_repo
        self.path_switch_service = path_switch_service
        self.action_commit_service = action_commit_service
        self.action_db = action_db
        self.action_user = action_user

    async def finalize_interrupted_run(self, thread_id: str, status: str) -> None:
        finalize = getattr(self.graph_repo, "mark_latest_interrupted_run_final", None)
        if finalize is None:
            return
        await finalize(thread_id=thread_id, status=status)

    async def resolve(self, pending, decision: dict) -> ToolResult:
        if str(pending.user_id) != str(decision.get("user_id")):
            return ToolResult(
                kind="clarification",
                answer_markdown="That action can no longer be completed.",
                fallback={"reason": "action_error", "message": "ownership_mismatch"},
            )
        if pending.status != "awaiting_confirmation":
            existing = await self.graph_repo.get_committed_action_result(pending.action_id)
            if existing is not None:
                return ToolResult(
                    kind="what_next",
                    answer_markdown="Action was already completed.",
                    metadata={"result": existing},
                )
            return ToolResult(
                kind="clarification",
                answer_markdown="That action can no longer be completed.",
                fallback={"reason": "action_error", "message": f"invalid_status:{pending.status}"},
            )
        if pending.expires_at <= datetime.now(UTC):
            await self.graph_repo.mark_action_expired(pending.action_id)
            await self.finalize_interrupted_run(str(pending.thread_id), "cancelled")
            return ToolResult(
                kind="clarification",
                answer_markdown="That action expired. Please ask me to generate a fresh proposal.",
                fallback={"reason": "action_error", "message": "expired"},
            )
        if decision.get("decision") == "reject":
            await self.graph_repo.mark_action_cancelled(pending.action_id)
            await self.finalize_interrupted_run(str(pending.thread_id), "cancelled")
            return ToolResult(kind="clarification", answer_markdown="Cancelled.")
        if decision.get("decision") == "edit":
            return ToolResult(
                kind="clarification",
                answer_markdown="I need to generate a fresh proposal for that edit before committing it.",
                fallback={"reason": "action_error", "message": "edit_requires_new_proposal"},
            )

        existing = await self.graph_repo.get_committed_action_result(pending.action_id)
        if existing is not None:
            return ToolResult(
                kind="what_next",
                answer_markdown="Action was already completed.",
                metadata={"result": existing},
            )
        if pending.type in {"request_path_switch", "start_assessment", "request_replan"} and (
            self.action_db is None or self.action_user is None
        ):
            return ToolResult(
                kind="clarification",
                answer_markdown="That action can no longer be completed.",
                fallback={"reason": "action_error", "message": "missing_action_context"},
            )

        if pending.type == "request_path_switch":
            if self.path_switch_service is None:
                return ToolResult(
                    kind="clarification",
                    answer_markdown="That action can no longer be completed.",
                    fallback={"reason": "action_error", "message": "missing_path_switch_service"},
                )
            edit_payload = decision.get("edit_payload") or {}
            target_path_id = (
                pending.payload_json.get("target_path_id")
                or edit_payload.get("targetPathId")
                or edit_payload.get("target_path_id")
            )
            if not target_path_id:
                return ToolResult(
                    kind="clarification",
                    answer_markdown="Choose a target learning path first.",
                    fallback={"reason": "action_error", "message": "missing_target_path"},
                )
            validate_request = getattr(self.path_switch_service, "validate_request", None)
            if validate_request is not None:
                decision_result = await validate_request(
                    self.action_user.id,
                    pending.payload_json.get("current_course_ids") or [],
                    target_path_id,
                    pending.payload_json.get("allowed_course_ids") or [],
                )
                if not decision_result.allow:
                    return ToolResult(
                        kind="clarification",
                        answer_markdown=decision_result.user_safe_message
                        or "That learning path is not available.",
                        fallback={
                            "reason": "action_error",
                            "message": ",".join(decision_result.codes) or "path_switch_rejected",
                        },
                    )
            result = await self.path_switch_service.commit(
                self.action_db,
                self.action_user,
                target_path_id,
                pending.idempotency_key,
            )
            message = (
                "I switched your active path and recalculated the learning plan. "
                "Open the plan view to continue with the updated recommendation."
            )
        elif pending.type == "start_assessment":
            result = await self.action_commit_service.commit_start_assessment(
                self.action_db,
                user_id=self.action_user.id,
                payload=pending.payload_json,
                idempotency_key=pending.idempotency_key,
            )
            message = "Assessment is ready. You can start it now."
        elif pending.type == "request_replan":
            result = await self.action_commit_service.commit_replan(
                self.action_db,
                user=self.action_user,
                payload=pending.payload_json,
                idempotency_key=pending.idempotency_key,
            )
            if not result.get("accepted", True):
                await self.graph_repo.mark_action_cancelled(pending.action_id)
                await self.finalize_interrupted_run(str(pending.thread_id), "cancelled")
                return ToolResult(
                    kind="clarification",
                    answer_markdown="I could not safely replan from that proposal.",
                    fallback={
                        "reason": "action_error",
                        "message": result.get("rejectedReason") or "replan_rejected",
                    },
                    metadata={"result": result},
                )
            message = "I recalculated your learning plan from the latest assessment evidence."
        else:
            result = {"type": pending.type, "status": "confirmed"}
            message = "Action confirmed."

        await self.graph_repo.mark_action_committed(pending.action_id, result=result)
        await self.finalize_interrupted_run(str(pending.thread_id), "succeeded")
        return ToolResult(kind="what_next", answer_markdown=message, metadata={"result": result})
