from __future__ import annotations

from typing import Any
from uuid import UUID

from src.schemas.learning_path import GeneratePathRequest
from src.services.agent_graph_contracts import PolicyDecision


SUPPORTED_AGENT_PATHS: dict[str, dict[str, Any]] = {
    "computer_vision": {
        "label": "Computer Vision",
        "selected_course_ids": ["CS230", "CS231n"],
    },
    "nlp": {
        "label": "Natural Language Processing",
        "selected_course_ids": ["CS230", "CS224n"],
    },
}


class AgentPathSwitchService:
    def __init__(self, goal_repo, planner):
        self.goal_repo = goal_repo
        self.planner = planner
        self._commit_cache: dict[str, dict[str, Any]] = {}

    async def validate_request(
        self,
        user_id: UUID,
        current_course_ids: list[str],
        target_path_id: str | None,
        allowed_course_ids: list[str],
    ) -> PolicyDecision:
        if target_path_id not in SUPPORTED_AGENT_PATHS:
            return PolicyDecision(
                allow=False,
                codes=["TARGET_PATH_NOT_FOUND"],
                user_safe_message="That learning path is not available.",
                audit_context={"targetPathId": target_path_id},
            )
        target_courses = SUPPORTED_AGENT_PATHS[target_path_id]["selected_course_ids"]
        if sorted(current_course_ids) == sorted(target_courses):
            return PolicyDecision(
                allow=False,
                codes=["SAME_PATH_SWITCH"],
                user_safe_message="You are already on that learning path.",
                audit_context={"targetPathId": target_path_id},
            )
        missing = [course_id for course_id in target_courses if course_id not in allowed_course_ids]
        if missing:
            return PolicyDecision(
                allow=False,
                codes=["TARGET_PATH_OUT_OF_SCOPE"],
                user_safe_message="That learning path is outside your current access scope.",
                audit_context={"missingCourseIds": missing},
            )
        return PolicyDecision(allow=True)

    def build_proposal(self, current_course_ids: list[str], target_path_id: str) -> dict[str, Any]:
        target = SUPPORTED_AGENT_PATHS[target_path_id]
        return {
            "current_course_ids": current_course_ids,
            "target_path_id": target_path_id,
            "target_course_ids": target["selected_course_ids"],
            "reuse_profile": True,
            "recompute_plan": True,
            "impact_summary": (
                f"Switch to {target['label']} and recompute the learning plan using "
                "the learner profile."
            ),
            "payload_version": 1,
        }

    async def commit(self, db, user, target_path_id: str, idempotency_key: str) -> dict[str, Any]:
        # Unit-test fallback only; production idempotency must be backed by agent_pending_actions.
        if idempotency_key in self._commit_cache:
            return self._commit_cache[idempotency_key]
        target = SUPPORTED_AGENT_PATHS[target_path_id]
        await self.goal_repo.upsert_for_user(
            user.id,
            selected_course_ids=target["selected_course_ids"],
            notes=f"agent_path_switch:{idempotency_key}",
        )
        generated = await self.planner(db, user, GeneratePathRequest())
        result = {
            "targetPathId": target_path_id,
            "targetCourseIds": target["selected_course_ids"],
            "totalUnits": generated.total_units,
            "totalHours": generated.total_hours,
            "warnings": generated.warnings,
        }
        self._commit_cache[idempotency_key] = result
        return result
