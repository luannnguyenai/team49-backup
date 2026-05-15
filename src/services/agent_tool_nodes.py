from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.schemas.agent import (
    AgentAction,
    AgentCitation,
    AgentFallback,
    AgentWarning,
    PathRequirementsRequest,
    UnitSearchRequest,
)
from src.services.agent_evidence_quality import AgentEvidenceQualityService, EvidenceQualityVerdict
from src.services.agent_graph_contracts import AgentSlots, ToolResult
from src.services.agent_search_scope_service import AgentSearchScopeService


class AgentToolNodes:
    TOO_MANY_RESULTS_THRESHOLD = 20

    def __init__(
        self,
        search_service,
        requirement_service,
        prerequisite_path_service=None,
        user_id=None,
        user_learning_context_service=None,
    ):
        self.search_service = search_service
        self.requirement_service = requirement_service
        self.prerequisite_path_service = prerequisite_path_service
        self.user_id = user_id
        self.user_learning_context_service = user_learning_context_service
        self.scope_service = AgentSearchScopeService()
        self.evidence_quality = AgentEvidenceQualityService()

    async def clarify(self, message: str, reason: str = "ambiguous_target") -> ToolResult:
        clarification = "Could you clarify the course, unit, or learning goal you want help with?"
        answer_markdown = clarification if reason == "ambiguous_target" else reason
        return ToolResult(
            kind="clarification",
            answer_markdown=answer_markdown,
            requires_evidence=False,
        )

    async def assistant_help(self, answer_markdown: str) -> ToolResult:
        return ToolResult(
            kind="clarification",
            answer_markdown=answer_markdown,
            requires_evidence=False,
        )

    async def user_learning_context(
        self,
        *,
        message: str,
        slots: AgentSlots,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
        route_context=None,
        context_kind: str | None = None,
    ) -> ToolResult:
        if self.user_id is None or self.user_learning_context_service is None:
            return ToolResult(
                kind="progress_summary",
                answer_markdown=(
                    "I cannot read learner progress in this environment, but I can still answer "
                    "from course content."
                ),
                fallback=AgentFallback(
                    reason="tool_unavailable",
                    message="Authenticated learner context service is unavailable.",
                ),
                requires_evidence=False,
                metadata={"learner_context_available": False},
            )

        snapshot = await self.user_learning_context_service.snapshot(
            user_id=self.user_id,
            allowed_course_ids=allowed_course_ids,
            current_path_course_ids=current_path_course_ids,
            route_context=route_context,
            context_kind=context_kind,
        )
        return ToolResult(
            kind="progress_summary",
            answer_markdown=None,
            requires_evidence=False,
            metadata={
                "learner_context_available": True,
                "learner_context": snapshot,
                "raw_topic": slots.raw_topic,
                "search_queries": slots.search_queries,
            },
        )

    async def lecture_context(
        self,
        *,
        message: str,
        slots: AgentSlots,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
        canonical_unit_id: str | None = None,
        query: str | None = None,
    ) -> ToolResult:
        repo = getattr(self.search_service, "repo", None)
        get_lecture_context = getattr(repo, "get_lecture_context_for_unit", None)
        if get_lecture_context is None:
            return await self.find_content(
                message,
                "find_content",
                slots,
                allowed_course_ids,
                current_path_course_ids=current_path_course_ids,
            )

        candidate_ids: list[str] = []
        if canonical_unit_id and str(canonical_unit_id).strip():
            candidate_ids.append(str(canonical_unit_id).strip())
        for slot_unit_id in slots.canonical_unit_ids:
            normalized = str(slot_unit_id).strip()
            if normalized and normalized not in candidate_ids:
                candidate_ids.append(normalized)

        lecture = None
        selected_id = None
        for candidate_id in candidate_ids:
            lecture = await get_lecture_context(
                candidate_id,
                allowed_course_ids=current_path_course_ids or allowed_course_ids,
            )
            if lecture:
                selected_id = candidate_id
                break

        if lecture is None and query:
            search_slots = slots.model_copy(update={"search_queries": [str(query)], "raw_topic": str(query)})
            search_result = await self.find_content(
                message,
                "find_content",
                search_slots,
                allowed_course_ids,
                current_path_course_ids=current_path_course_ids,
            )
            if search_result.citations:
                selected_id = search_result.citations[0].canonical_unit_id
                lecture = await get_lecture_context(
                    selected_id,
                    allowed_course_ids=current_path_course_ids or allowed_course_ids,
                )
        if not selected_id:
            return ToolResult(
                kind="clarification",
                answer_markdown="I need a selected unit or searchable lecture topic to summarize that lecture.",
                requires_evidence=False,
            )

        if not lecture:
            return ToolResult(
                kind="find_content",
                answer_markdown="I could not find lecture context for the selected unit.",
                requires_evidence=True,
                metadata={"lecture_context_found": False, "canonical_unit_id": selected_id},
            )

        citations = [
            AgentCitation(
                canonical_unit_id=unit["canonical_unit_id"],
                course_id=unit["course_id"],
                lecture_id=unit.get("lecture_id"),
                lecture_title=unit.get("lecture_title"),
                unit_name=unit["unit_name"],
                learn_href=unit.get("learn_href"),
                quote=unit.get("summary"),
                source="summary",
            )
            for unit in lecture["units"][:8]
            if unit.get("canonical_unit_id")
        ]
        return ToolResult(
            kind="find_content",
            answer_markdown=None,
            citations=citations,
            requires_evidence=False,
            metadata={
                "lecture_context_found": True,
                "lecture_context": lecture,
                "raw_topic": lecture.get("lecture_title") or selected_id,
                "search_queries": [lecture.get("lecture_title") or selected_id],
            },
        )

    async def find_content(
        self,
        message: str,
        intent: str,
        slots: AgentSlots,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
    ) -> ToolResult:
        scoped_course_ids = self.scope_service.course_ids_for_paths(
            slots.resolved_search_path_ids,
            allowed_course_ids,
        )
        current_path_ids = (
            slots.excluded_search_path_ids
            if slots.search_scope == "expanded_paths" and slots.excluded_search_path_ids
            else slots.resolved_search_path_ids
        )
        current_course_ids = current_path_course_ids or self.scope_service.course_ids_for_paths(
            current_path_ids,
            allowed_course_ids,
        )
        preferred_course_ids = (
            scoped_course_ids if slots.search_scope == "explicit_path" else current_course_ids
        )
        search_queries = self._search_queries(message, slots)
        searches = [
            await self.search_service.search(
                UnitSearchRequest(
                    query=query,
                    scope="global_catalog"
                    if slots.search_scope == "expanded_paths"
                    else "current_path",
                    courseIds=allowed_course_ids,
                    currentPathCourseIds=current_course_ids,
                    preferredCourseIds=preferred_course_ids,
                    preferredScope=slots.search_scope,
                    intent=intent,
                    limit=20,
                ),
                allowed_course_ids=allowed_course_ids,
            )
            for query in search_queries
        ]
        search = searches[0]
        merged_results = {}
        for response in searches:
            for result in response.results:
                if result.score <= 0:
                    continue
                existing = merged_results.get(result.canonical_unit_id)
                if existing is None or result.score > existing.score:
                    merged_results[result.canonical_unit_id] = result
        all_results = sorted(
            merged_results.values(),
            key=lambda result: result.score,
            reverse=True,
        )
        verdict = self.evidence_quality.score(slots.raw_topic or search_queries[0], all_results)
        if slots.canonical_unit_ids:
            selected_exact_ids = [
                result.canonical_unit_id
                for result in all_results
                if result.canonical_unit_id in set(slots.canonical_unit_ids)
            ]
            if selected_exact_ids:
                verdict = EvidenceQualityVerdict(
                    label="direct_match",
                    selected_unit_ids=selected_exact_ids[:3],
                    reason_codes=["explicit_topic_choice"],
                    match_reasons={
                        unit_id: "The learner selected this topic from the ambiguity card."
                        for unit_id in selected_exact_ids[:3]
                    },
                )
                all_results = [
                    result
                    for result in all_results
                    if result.canonical_unit_id in set(selected_exact_ids)
                ]
        if not slots.topic_choice_approved:
            topic_choice_actions = self._build_topic_choice_actions(
                message=message,
                raw_topic=slots.raw_topic or search_queries[0],
                all_results=all_results,
                selected_unit_ids=verdict.selected_unit_ids,
            )
        else:
            topic_choice_actions = []
        if topic_choice_actions:
            trace = search.trace.model_copy(
                update={
                    "intent": intent,
                    "selected_path": slots.search_scope,
                    "candidate_courses": allowed_course_ids,
                    "selected_unit_ids": [],
                }
            )
            return ToolResult(
                kind="clarification",
                answer_markdown=self._topic_choice_message(
                    message, slots.raw_topic or search_queries[0]
                ),
                actions=topic_choice_actions,
                warning=AgentWarning(
                    type="ambiguous_target",
                    message="Multiple matching units were found; choose one to narrow the explanation.",
                ),
                requires_evidence=False,
                metadata={
                    "topic_selection_offered": True,
                    "evidence_verdict": verdict.label,
                    "search_queries": search_queries,
                },
                trace=trace,
            )
        if (
            len(all_results) >= self.TOO_MANY_RESULTS_THRESHOLD
            and not slots.show_top_results_approved
            and not (verdict.label == "direct_match" and len(verdict.selected_unit_ids) < 3)
        ):
            raw_topic = slots.raw_topic or message
            top_results = all_results[:5]
            citations = [
                AgentCitation(
                    canonical_unit_id=result.canonical_unit_id,
                    course_id=result.course_id,
                    lecture_id=result.lecture_id,
                    lecture_title=result.lecture_title,
                    unit_name=result.unit_name,
                    learn_href=result.learn_href,
                    quote=result.summary,
                    source="summary",
                )
                for result in top_results
            ]
            actions = [
                AgentAction(
                    type="open_unit",
                    label=f"Open {result.unit_name}",
                    learn_href=result.learn_href,
                    canonical_unit_id=result.canonical_unit_id,
                )
                for result in top_results
                if result.learn_href
            ]
            trace = search.trace.model_copy(
                update={
                    "intent": intent,
                    "selected_path": slots.search_scope,
                    "candidate_courses": allowed_course_ids,
                    "selected_unit_ids": [result.canonical_unit_id for result in top_results],
                }
            )
            return ToolResult(
                kind="clarification",
                answer_markdown=None,
                citations=citations,
                actions=actions,
                warning=self._outside_current_path_warning(top_results),
                requires_evidence=False,
                metadata={
                    "too_many_results_offered": True,
                    "result_count": len(all_results),
                    "raw_topic": raw_topic,
                    "search_queries": search_queries,
                    "top_results_allowed": True,
                    "answer_confidence": "partial",
                },
                trace=trace,
            )
        if (
            verdict.label == "weak_match"
            and slots.search_scope == "current_path"
            and len(allowed_course_ids) > len(scoped_course_ids)
        ):
            trace = search.trace.model_copy(
                update={
                    "intent": intent,
                    "selected_path": slots.search_scope,
                    "candidate_courses": allowed_course_ids,
                    "selected_unit_ids": [],
                }
            )
            return ToolResult(
                kind="clarification",
                answer_markdown=(
                    "I only found weakly related results in your current path. "
                    "Do you want me to expand the search to other allowed paths?"
                ),
                warning=AgentWarning(
                    type="ambiguous_target",
                    message="Current-path evidence was weak; expansion requires confirmation.",
                ),
                requires_evidence=False,
                metadata={
                    "scope_expansion_offered": True,
                    "evidence_verdict": verdict.label,
                    "evidence_reason_codes": verdict.reason_codes,
                    "search_queries": search_queries,
                },
                trace=trace,
            )
        selected_ids = set(verdict.selected_unit_ids)
        results = [result for result in all_results if result.canonical_unit_id in selected_ids][
            :3
        ] or all_results[:3]
        citations = [
            AgentCitation(
                canonical_unit_id=result.canonical_unit_id,
                course_id=result.course_id,
                lecture_id=result.lecture_id,
                lecture_title=result.lecture_title,
                unit_name=result.unit_name,
                learn_href=result.learn_href,
                quote=result.summary,
                source="summary",
            )
            for result in results
        ]
        actions = [
            AgentAction(
                type="open_unit",
                label=f"Open {result.unit_name}",
                learn_href=result.learn_href,
                canonical_unit_id=result.canonical_unit_id,
            )
            for result in results
            if result.learn_href
        ]
        prereq_action = await self._build_prerequisite_path_action(
            verdict_label=verdict.label,
            all_results=all_results,
            selected_unit_ids=verdict.selected_unit_ids,
            allowed_course_ids=allowed_course_ids,
        )
        if prereq_action is not None:
            actions.append(prereq_action)
        trace = search.trace.model_copy(
            update={
                    "intent": intent,
                    "selected_path": slots.search_scope,
                    "candidate_courses": allowed_course_ids,
                    "selected_unit_ids": [citation.canonical_unit_id for citation in citations],
                }
            )
        if verdict.label == "weak_match" and not actions:
            return ToolResult(
                kind="find_content",
                answer_markdown="I could not find a direct grounded source for that request.",
                citations=[],
                actions=[],
                requires_evidence=True,
                metadata={
                    "evidence_verdict": verdict.label,
                    "evidence_reason_codes": verdict.reason_codes,
                    "search_queries": search_queries,
                },
                trace=trace,
            )
        if not citations and slots.search_scope == "current_path":
            return ToolResult(
                kind="clarification",
                answer_markdown=(
                    "I could not find this in your current path. "
                    "Do you want me to expand the search to other allowed paths?"
                ),
                warning=AgentWarning(
                    type="ambiguous_target",
                    message="No result was found in the current path; expansion requires confirmation.",
                ),
                fallback=AgentFallback(
                    reason="no_retrieval_result",
                    message="Current-path search returned no grounded result.",
                ),
                requires_evidence=False,
                metadata={"scope_expansion_offered": True},
                trace=trace,
            )
        if not citations:
            return ToolResult(
                kind="find_content",
                answer_markdown="I could not find a grounded source for that request.",
                citations=[],
                actions=[],
                fallback=AgentFallback(
                    reason="no_retrieval_result",
                    message="No matching learning unit was found in the selected search scope.",
                ),
                requires_evidence=True,
                metadata={
                    "evidence_verdict": verdict.label,
                    "evidence_reason_codes": verdict.reason_codes,
                    "search_queries": search_queries,
                },
                trace=trace,
            )
        if slots.search_scope == "expanded_paths" and citations:
            allowed_path_ids = slots.resolved_search_path_ids
            path_hits: dict[str, list[AgentCitation]] = {}
            for citation in citations:
                for path_id in self.scope_service.path_ids_for_course(
                    citation.course_id,
                    allowed_path_ids,
                ):
                    path_hits.setdefault(path_id, []).append(citation)
            if len(path_hits) > 1:
                non_current_path_hits = {
                    path_id: hits
                    for path_id, hits in path_hits.items()
                    if path_id not in set(slots.excluded_search_path_ids)
                }
                if non_current_path_hits:
                    path_hits = non_current_path_hits
                if len(path_hits) < 3:
                    allowed_course_ids_for_path = {
                        citation.course_id for hits in path_hits.values() for citation in hits
                    }
                    citations = [
                        citation
                        for citation in citations
                        if citation.course_id in allowed_course_ids_for_path
                    ]
                    actions = [
                        action
                        for action in actions
                        if action.canonical_unit_id
                        in {citation.canonical_unit_id for citation in citations}
                    ]
                else:
                    raw_topic = slots.raw_topic or message
                    actions = [
                        AgentAction(
                            type="choose_target_path",
                            label=f"{raw_topic} in {self.scope_service.path_label(path_id)}",
                            workflowId=path_id,
                        )
                        for path_id in path_hits
                    ]
                    return ToolResult(
                        kind="clarification",
                        answer_markdown=(
                            f"I found information related to {raw_topic} in multiple paths. "
                            "Which path do you want me to search more deeply?"
                        ),
                        actions=actions,
                        warning=AgentWarning(
                            type="ambiguous_target",
                            message="Expanded search found multiple matching paths.",
                        ),
                        requires_evidence=False,
                        metadata={
                            "path_selection_offered": True,
                            "path_options": list(path_hits.keys()),
                        },
                        trace=trace,
                    )
        disclosure = ""
        if slots.search_scope == "expanded_paths" and citations:
            disclosure = "\n\nI found this outside the original current-path search scope."
        answer_markdown = disclosure.strip() or None
        metadata = {
            "evidence_verdict": verdict.label,
            "evidence_reason_codes": verdict.reason_codes,
            "match_reasons": verdict.match_reasons,
            "result_count": len(all_results),
            "search_queries": search_queries,
        }
        if verdict.label in {"related_match", "weak_match"}:
            answer_markdown = answer_markdown or (
                f"I found related results for {slots.raw_topic or message}, but they may not be an exact match. "
                "If these are not what you need, describe the target more specifically."
            )
            metadata["answer_confidence"] = "partial"
        return ToolResult(
            kind="find_content",
            answer_markdown=answer_markdown,
            citations=citations,
            actions=actions,
            warning=self._outside_current_path_warning(results),
            requires_evidence=verdict.requires_grounded_answer,
            metadata=metadata,
            trace=trace,
        )

    def _search_queries(self, message: str, slots: AgentSlots) -> list[str]:
        candidates = [query.strip() for query in slots.search_queries if query and query.strip()]
        if not candidates and slots.raw_topic and slots.raw_topic.strip():
            candidates.insert(0, slots.raw_topic.strip())
        if not candidates:
            candidates.append(message.strip())

        deduped: list[str] = []
        seen = set()
        for candidate in candidates:
            key = candidate.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
        return deduped[:5]

    @staticmethod
    def _outside_current_path_warning(results) -> AgentWarning | None:
        if not any(getattr(result, "outside_current_path", False) for result in results):
            return None
        return AgentWarning(
            type="outside_current_path",
            message=(
                "Some sources are outside your current learning path. "
                "You can open them directly if you want to self-study that material."
            ),
        )

    async def _build_prerequisite_path_action(
        self,
        *,
        verdict_label: str,
        all_results,
        selected_unit_ids: list[str],
        allowed_course_ids: list[str],
    ) -> AgentAction | None:
        if verdict_label != "direct_match" or self.prerequisite_path_service is None:
            return None
        target_result = self._specific_target_result(all_results, selected_unit_ids)
        if target_result is None:
            return None
        prerequisite_path = await self.prerequisite_path_service.build(
            target_canonical_unit_id=target_result.canonical_unit_id,
            allowed_course_ids=allowed_course_ids,
            user_id=self.user_id,
        )
        if prerequisite_path is None or len(prerequisite_path.nodes) < 2:
            return None
        canonical_unit_ids = [node.canonical_unit_id for node in prerequisite_path.nodes]
        return AgentAction(
            type="review_prerequisite_path",
            label="Review prerequisite order",
            canonical_unit_ids=canonical_unit_ids,
            canonical_unit_id=target_result.canonical_unit_id,
            prerequisitePath=prerequisite_path,
        )

    @staticmethod
    def _specific_target_result(all_results, selected_unit_ids: list[str]):
        selected = [
            result for result in all_results if result.canonical_unit_id in set(selected_unit_ids)
        ]
        if not selected:
            return None
        if len(selected) == 1:
            return selected[0]
        return selected[0] if selected[0].score > selected[1].score else None

    def _build_topic_choice_actions(
        self,
        *,
        message: str,
        raw_topic: str,
        all_results,
        selected_unit_ids: list[str],
    ) -> list[AgentAction]:
        return []

    def _topic_choice_message(self, message: str, raw_topic: str) -> str:
        if self._looks_vietnamese(message):
            return (
                f"Mình tìm thấy vài chủ đề khớp với {raw_topic}. "
                "Chọn một chủ đề bên dưới để mình giải thích đúng phạm vi và kiểm tra prerequisite liên quan."
            )
        return (
            f"I found several matching topics for {raw_topic}. "
            "Choose one below so I can explain the right scope and check the related prerequisites."
        )

    @staticmethod
    def _looks_vietnamese(message: str) -> bool:
        lowered = f" {message.lower()} "
        vietnamese_markers = (
            " tôi ",
            " bạn ",
            " muốn ",
            " học ",
            " giải thích ",
            " tìm ",
            " lộ trình ",
            " kiến thức ",
        )
        return bool(
            any(marker in lowered for marker in vietnamese_markers)
            or any(
                char in lowered
                for char in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
            )
        )

    async def planner_decision(
        self,
        message: str,
        slots: AgentSlots,
        allowed_course_ids: list[str],
        user_id: str | None,
    ) -> ToolResult:
        requirements = await self.requirement_service.get_requirements(
            PathRequirementsRequest(targetPathKey=slots.target_path),
            allowed_course_ids=allowed_course_ids,
            user_id=user_id,
        )
        citations = [
            AgentCitation(
                canonical_unit_id=unit.canonical_unit_id,
                course_id=unit.course_id,
                unit_name=unit.unit_name,
                learn_href=unit.learn_href,
                source="planner",
            )
            for unit in requirements.required_units[:5]
        ]
        return ToolResult(
            kind="planner_decision",
            answer_markdown="I checked the prerequisite graph for that path.",
            citations=citations,
            requires_evidence=True,
        )

    async def assessment_proposal(self, slots: AgentSlots) -> ToolResult:
        expires_at = datetime.now(UTC) + timedelta(minutes=30)
        return ToolResult(
            kind="assessment_proposal",
            answer_markdown="I can prepare an assessment after you confirm.",
            actions=[
                AgentAction(
                    type="start_assessment_workflow",
                    label="Prepare assessment proposal",
                    actionId=f"act_{uuid4()}",
                    status="awaiting_confirmation",
                    expiresAt=expires_at,
                    canonical_unit_ids=slots.canonical_unit_ids,
                    eligible=True,
                )
            ],
        )

    async def replan_proposal(self, message: str = "") -> ToolResult:
        expires_at = datetime.now(UTC) + timedelta(minutes=30)
        if self._looks_vietnamese(message):
            answer_markdown = (
                "Được. Mở bộ chọn phạm vi bên dưới, mô tả phần bạn đã biết, "
                "rồi mình sẽ dùng đánh giá đó để tối ưu lại lộ trình học."
            )
            label = "Mở bộ chọn phạm vi"
        else:
            answer_markdown = (
                "Sure. Open the scope builder below, describe what you already know, "
                "and I will use that assessment to optimize your learning path."
            )
            label = "Open scope builder"
        return ToolResult(
            kind="replan_proposal",
            answer_markdown=answer_markdown,
            actions=[
                AgentAction(
                    type="request_replan",
                    label=label,
                    actionId=f"act_{uuid4()}",
                    status="awaiting_confirmation",
                    expiresAt=expires_at,
                    eligible=True,
                )
            ],
        )

    async def path_switch_proposal(self, slots: AgentSlots) -> ToolResult:
        expires_at = datetime.now(UTC) + timedelta(minutes=30)
        return ToolResult(
            kind="path_switch_proposal",
            answer_markdown="Sure. Choose the learning path below, then confirm the change when you are ready.",
            actions=[
                AgentAction(
                    type="request_path_switch",
                    label="Choose learning path",
                    actionId=f"act_{uuid4()}",
                    status="awaiting_confirmation",
                    expiresAt=expires_at,
                    eligible=True,
                )
            ],
        )
