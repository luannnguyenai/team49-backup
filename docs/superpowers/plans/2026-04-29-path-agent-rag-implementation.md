# Path Agent RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a V1 Path Agent backend that accepts chat messages, resolves user/path context, retrieves canonical units through unit-centered search or graph-based path requirements, returns cited answers/actions, and exposes traceable tool contracts.

**Architecture:** Add a separate `/api/agent` router and focused backend services: schemas, context resolver, query normalizer, unit search, runtime navigation resolver, path requirement service, unit context service, and chat orchestrator. Keep the implementation deterministic and tool-mediated; do not update mastery/planner state from LLM text. Use non-streaming chat in V1 and return structured citations/actions/traces.

**Tech Stack:** FastAPI, SQLAlchemy AsyncSession, Pydantic v2, PostgreSQL full-text-compatible query construction, pytest/pytest-asyncio, httpx ASGI contract tests.

---

## Scope And Constraints

This plan implements backend contracts and deterministic orchestration only. It does not implement frontend chat UI, streaming, vector embeddings, or LLM answer generation. The chat orchestrator can return template-based grounded answers in V1 while preserving the final response shape for future LLM integration.

Important rules:

- `units.unit_id` is canonical and is the primary retrieval key.
- UI actions need runtime navigation fields such as `learning_unit_id`, `course_slug`, `unit_slug`, and `learn_href`.
- Public search requests must not allow `includeHidden`.
- Public requested `courseIds` must be intersected with the user's selected/enrolled/available courses.
- `traceMode="full"` is reviewer/dev/admin only.
- Replan requests must not trust client-provided phase/KP/mastery deltas.
- Self-report does not update mastery. Assessment evidence does.

## File Structure

Create:

- `src/schemas/agent.py` — Pydantic request/response contracts for chat, search, path requirements, unit context, actions, trace, citations, and actions.
- `src/routers/agent.py` — FastAPI `/api/agent` endpoints and auth/db wiring.
- `src/services/agent_query_normalizer.py` — deterministic alias/synonym expansion with trace output.
- `src/services/agent_context_service.py` — authenticated user/path/course context resolver.
- `src/services/agent_navigation_service.py` — canonical unit to runtime `learn_href` resolver.
- `src/services/agent_search_service.py` — unit-centered search and ranking.
- `src/services/agent_requirement_service.py` — graph-based path prerequisite/gap service.
- `src/services/agent_unit_context_service.py` — canonical unit context/KP/quiz/timestamp expansion.
- `src/services/agent_chat_service.py` — orchestration endpoint logic: intent, tool calls, citations, actions, fallback, trace.
- `tests/services/test_agent_query_normalizer.py`
- `tests/services/test_agent_context_service.py`
- `tests/services/test_agent_search_service.py`
- `tests/services/test_agent_requirement_service.py`
- `tests/services/test_agent_unit_context_service.py`
- `tests/services/test_agent_chat_service.py`
- `tests/contract/test_agent_routes.py`

Modify:

- `src/api/app.py` — include `agent_router`.
- `src/repositories/canonical_content_repo.py` — add focused data access helpers for agent search/navigation/requirements.
- `tests/repositories/test_canonical_content_repo.py` — add repository behavior tests for new helpers.

Do not modify:

- Existing Lecture AI Tutor routing/scope.
- Existing assessment scoring/mastery update logic.
- Existing planner generation logic except through future replan action stubs.

---

### Task 1: Agent Schemas

**Files:**
- Create: `src/schemas/agent.py`
- Test: `tests/test_agent_schema_contract.py`

- [ ] **Step 1: Write schema contract tests**

Create `tests/test_agent_schema_contract.py`:

```python
from pydantic import ValidationError

from src.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentAction,
    AgentCitation,
    UnitSearchRequest,
    UnitSearchResponse,
)


def test_chat_request_accepts_minimal_message():
    request = AgentChatRequest(message="Where is receptive field taught?")

    assert request.message == "Where is receptive field taught?"
    assert request.response_mode == "non_streaming"
    assert request.trace_mode == "summary"


def test_chat_response_supports_citations_and_disabled_assessment_action():
    response = AgentChatResponse(
        conversation_id="conv-1",
        message_id="msg-1",
        answer={"markdown": "Found it in CS231n Lecture 5.", "confidence": "grounded"},
        citations=[
            AgentCitation(
                canonical_unit_id="local::lecture_5::seg6",
                course_id="CS231n",
                lecture_id="lecture-05",
                lecture_title="Lecture 5: Image Classification with CNNs",
                unit_name="Receptive fields, stride, and convolution formulas",
                learn_href="/courses/cs231n/learn/lecture-05-seg6#t=3220",
                timestamp_s=3220,
                source="key_point",
            )
        ],
        actions=[
            AgentAction(
                type="start_assessment",
                label="Verify with a short quiz",
                canonical_unit_ids=["local::lecture_5::seg6"],
                default_phase="skip_verification",
                eligible=False,
                disabled_reason="no_eligible_questions",
            )
        ],
    )

    assert response.actions[0].eligible is False
    assert response.actions[0].disabled_reason == "no_eligible_questions"


def test_unit_search_request_does_not_accept_include_hidden():
    try:
        UnitSearchRequest.model_validate(
            {
                "query": "course logistics",
                "includeHidden": True,
            }
        )
    except ValidationError as exc:
        assert "includeHidden" in str(exc)
    else:
        raise AssertionError("includeHidden must not be accepted on public request")


def test_unit_search_response_trace_uses_per_result_navigation_resolution():
    response = UnitSearchResponse(
        results=[],
        trace={
            "trace_id": "trace-1",
            "resolved_scope": "current_path",
            "normalized_query": "receptive field",
            "query_expansions": [],
            "applied_filters": ["course_scope:CS231n"],
            "ranking_version": "unit_search_v1",
            "runtime_navigation_resolution": [
                {
                    "canonical_unit_id": "local::lecture_5::seg6",
                    "source": "product_learning_unit",
                    "learn_href": "/courses/cs231n/learn/lecture-05-seg6",
                }
            ],
        },
    )

    assert response.trace.runtime_navigation_resolution[0].source == "product_learning_unit"
```

- [ ] **Step 2: Run schema tests and verify failure**

Run:

```bash
pytest tests/test_agent_schema_contract.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.schemas.agent'`.

- [ ] **Step 3: Implement schemas**

Create `src/schemas/agent.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AgentScope = Literal[
    "current_unit",
    "current_lecture",
    "current_course",
    "current_path",
    "global_catalog",
]

AgentIntent = Literal[
    "explain_concept",
    "find_content",
    "navigate_to_unit",
    "ask_what_next",
    "assess_knowledge",
    "request_replan",
    "explain_planner_decision",
    "summarize_progress",
    "general_course_question",
]

AssessmentPhase = Literal[
    "placement",
    "mini_quiz",
    "skip_verification",
    "bridge_check",
    "final_quiz",
    "review",
]


class RouteContext(BaseModel):
    route: str
    course_slug: str | None = Field(default=None, alias="courseSlug")
    unit_slug: str | None = Field(default=None, alias="unitSlug")
    canonical_unit_id: str | None = Field(default=None, alias="canonicalUnitId")
    player_timestamp_sec: int | None = Field(default=None, alias="playerTimestampSec")

    model_config = ConfigDict(populate_by_name=True)


class QueryExpansion(BaseModel):
    from_term: str = Field(alias="from")
    to: list[str]
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class RuntimeNavigationTrace(BaseModel):
    canonical_unit_id: str
    source: Literal["path_item", "product_learning_unit", "missing"]
    learn_href: str | None = None


class RetrievalTrace(BaseModel):
    trace_id: str
    intent: AgentIntent | None = None
    raw_query: str | None = None
    normalized_query: str
    query_expansions: list[QueryExpansion] = Field(default_factory=list)
    resolved_scope: AgentScope
    selected_path: str | None = None
    candidate_courses: list[str] = Field(default_factory=list)
    applied_filters: list[str] = Field(default_factory=list)
    ranking_version: str
    runtime_navigation_resolution: list[RuntimeNavigationTrace] = Field(default_factory=list)
    selected_unit_ids: list[str] = Field(default_factory=list)


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = Field(default=None, alias="conversationId")
    route_context: RouteContext | None = Field(default=None, alias="routeContext")
    response_mode: Literal["non_streaming", "streaming"] = Field(
        default="non_streaming", alias="responseMode"
    )
    trace_mode: Literal["none", "summary", "full"] = Field(default="summary", alias="traceMode")

    model_config = ConfigDict(populate_by_name=True)


class AgentAnswer(BaseModel):
    markdown: str
    confidence: Literal["grounded", "partial", "no_source"]


class AgentCitation(BaseModel):
    canonical_unit_id: str
    course_id: str
    lecture_id: str | None = None
    lecture_title: str | None = None
    unit_name: str
    learn_href: str | None = None
    timestamp_s: int | None = None
    quote: str | None = None
    source: Literal["summary", "key_point", "transcript", "planner", "mastery"]


class AgentAction(BaseModel):
    type: Literal["open_unit", "start_assessment", "request_replan_dry_run"]
    label: str
    learn_href: str | None = None
    canonical_unit_id: str | None = None
    canonical_unit_ids: list[str] = Field(default_factory=list)
    default_phase: AssessmentPhase | None = None
    eligible: bool | None = None
    disabled_reason: Literal[
        "no_eligible_questions",
        "unsupported_phase",
        "out_of_scope",
        "requires_login",
    ] | None = Field(default=None, alias="disabledReason")
    current_plan_id: str | None = Field(default=None, alias="currentPlanId")
    planner_session_id: str | None = Field(default=None, alias="plannerSessionId")
    assessment_session_id: str | None = Field(default=None, alias="assessmentSessionId")
    source_canonical_unit_ids: list[str] = Field(
        default_factory=list, alias="sourceCanonicalUnitIds"
    )

    model_config = ConfigDict(populate_by_name=True)


class AgentFallback(BaseModel):
    reason: Literal["no_retrieval_result", "out_of_scope", "unsafe_action", "tool_error"]
    message: str


class StartAssessmentActionRequest(BaseModel):
    canonical_unit_ids: list[str] = Field(alias="canonicalUnitIds", min_length=1)
    phase: AssessmentPhase
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class RequestReplanActionRequest(BaseModel):
    assessment_session_id: str | None = Field(default=None, alias="assessmentSessionId")
    source_canonical_unit_ids: list[str] = Field(default_factory=list, alias="sourceCanonicalUnitIds")
    reason: str
    dry_run: bool = Field(default=True, alias="dryRun")

    model_config = ConfigDict(populate_by_name=True)


class AgentActionResponse(BaseModel):
    accepted: bool
    rejected_reason: str | None = Field(default=None, alias="rejectedReason")
    dry_run: bool = Field(default=True, alias="dryRun")
    impact: dict | None = None

    model_config = ConfigDict(populate_by_name=True)


class AgentChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: AgentAnswer
    citations: list[AgentCitation] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)
    fallback: AgentFallback | None = None
    trace: RetrievalTrace | None = None


class UnitSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    scope: AgentScope | None = None
    course_ids: list[str] | None = Field(default=None, alias="courseIds")
    limit: int = Field(default=5, ge=1, le=20)
    intent: AgentIntent | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class UnitSearchResult(BaseModel):
    canonical_unit_id: str
    learning_unit_id: str | None = None
    course_id: str
    course_slug: str | None = None
    lecture_id: str | None = None
    lecture_title: str | None = None
    unit_slug: str | None = None
    learn_href: str | None = None
    start_sec: int | None = None
    end_sec: int | None = None
    unit_name: str
    summary: str | None = None
    score: float
    reasons: list[str] = Field(default_factory=list)
    has_quiz_items: bool = False
    content_type: str | None = None
    salience_score: str | None = None
    actionable: bool
    navigation_resolution: Literal["path_item", "product_learning_unit", "missing"]


class UnitSearchResponse(BaseModel):
    results: list[UnitSearchResult]
    trace: RetrievalTrace


class TranscriptSnippet(BaseModel):
    start_sec: int
    end_sec: int
    text: str
    source: Literal["transcript", "summary", "key_point"]


class UnitContextResponse(BaseModel):
    canonical_unit_id: str
    course_id: str
    lecture_id: str | None = None
    lecture_title: str | None = None
    unit_name: str
    summary: str | None = None
    key_points: list[dict | str] = Field(default_factory=list)
    kp_ids: list[str] = Field(default_factory=list)
    learn_href: str | None = None
    start_sec: int | None = None
    end_sec: int | None = None
    snippets: list[TranscriptSnippet] = Field(default_factory=list)
    trace: RetrievalTrace


class PathRequirementsRequest(BaseModel):
    target_path_key: Literal["computer_vision", "nlp"] = Field(alias="targetPathKey")
    target_course_ids: list[str] | None = Field(default=None, alias="targetCourseIds")
    source_course_ids: list[str] | None = Field(default=None, alias="sourceCourseIds")
    include_mastery: bool = Field(default=True, alias="includeMastery")
    prerequisite_depth: Literal[1, 2] = Field(default=2, alias="prerequisiteDepth")

    model_config = ConfigDict(populate_by_name=True)


class PathRequirementUnit(BaseModel):
    canonical_unit_id: str
    learning_unit_id: str | None = None
    course_id: str
    course_slug: str | None = None
    unit_slug: str | None = None
    learn_href: str | None = None
    unit_name: str
    required_kp_ids: list[str]
    prerequisite_for: list[str]
    mastery_lcb: float | None = None
    status: Literal["required", "already_mastered", "needs_review", "unassessed"]
    reasons: list[str]


class PathRequirementTrace(BaseModel):
    trace_id: str
    target_path: str
    selected_path: str
    selected_course_ids: list[str]
    prerequisite_depth: int
    graph_edges_considered: int
    applied_filters: list[str]
    ranking_version: str
    runtime_navigation_resolution: list[RuntimeNavigationTrace] = Field(default_factory=list)


class PathRequirementsResponse(BaseModel):
    required_units: list[PathRequirementUnit] = Field(alias="requiredUnits")
    auth: dict[str, bool] = Field(default_factory=lambda: {"userScoped": True})
    trace: PathRequirementTrace

    model_config = ConfigDict(populate_by_name=True)
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
pytest tests/test_agent_schema_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/schemas/agent.py tests/test_agent_schema_contract.py
git commit -m "feat: add path agent schemas"
```

---

### Task 2: Query Normalizer

**Files:**
- Create: `src/services/agent_query_normalizer.py`
- Test: `tests/services/test_agent_query_normalizer.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_query_normalizer.py`:

```python
from src.services.agent_query_normalizer import normalize_agent_query


def test_expands_rf_in_cv_context():
    result = normalize_agent_query("Where is RF covered?", course_ids=["CS231n"])

    assert "receptive field" in result.normalized_query
    assert result.expansions[0].from_term == "RF"
    assert result.expansions[0].to == ["receptive field"]


def test_expands_cnn_aliases():
    result = normalize_agent_query("Test me on CNNs")

    assert "convolutional neural network" in result.normalized_query
    assert any(exp.from_term.lower() == "cnn" for exp in result.expansions)


def test_expands_word_vectors():
    result = normalize_agent_query("word vectors in NLP")

    assert "word embeddings" in result.normalized_query
    assert "dense vectors" in result.normalized_query
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_query_normalizer.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement normalizer**

Create `src/services/agent_query_normalizer.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.schemas.agent import QueryExpansion


@dataclass(slots=True)
class NormalizedQuery:
    raw_query: str
    normalized_query: str
    expansions: list[QueryExpansion] = field(default_factory=list)


ALIASES: tuple[tuple[str, list[str], str], ...] = (
    (r"\bViT\b", ["vision transformer", "image transformer"], "vision_domain_alias"),
    (r"\bCNNs?\b", ["convnet", "convolutional neural network", "convolution"], "cv_domain_alias"),
    (r"\bRF\b", ["receptive field"], "cv_domain_alias"),
    (r"\bword vectors?\b", ["embeddings", "word embeddings", "dense vectors"], "nlp_domain_alias"),
    (r"\bRAG\b", ["retrieval augmented generation", "retrieval", "augmentation"], "rag_alias"),
    (r"\bbackprop\b", ["backpropagation", "gradient", "chain rule"], "dl_domain_alias"),
)


def normalize_agent_query(query: str, course_ids: list[str] | None = None) -> NormalizedQuery:
    normalized = query.strip()
    expansions: list[QueryExpansion] = []
    for pattern, replacements, reason in ALIASES:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            matched = re.search(pattern, normalized, flags=re.IGNORECASE)
            from_term = matched.group(0) if matched else pattern
            for replacement in replacements:
                if replacement.lower() not in normalized.lower():
                    normalized = f"{normalized} {replacement}"
            expansions.append(
                QueryExpansion.model_validate(
                    {"from": from_term, "to": replacements, "reason": reason}
                )
            )

    normalized = re.sub(r"\s+", " ", normalized).strip()
    return NormalizedQuery(raw_query=query, normalized_query=normalized, expansions=expansions)
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_query_normalizer.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_query_normalizer.py tests/services/test_agent_query_normalizer.py
git commit -m "feat: add agent query normalizer"
```

---

### Task 3: Agent Context Resolver

**Files:**
- Create: `src/services/agent_context_service.py`
- Test: `tests/services/test_agent_context_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_context_service.py`:

```python
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services.agent_context_service import AgentContextService


@pytest.mark.asyncio
async def test_context_resolver_reads_goal_preference_courses():
    user_id = uuid4()
    goal_repo = SimpleNamespace()

    async def get_by_user_id(input_user_id):
        assert input_user_id == user_id
        return SimpleNamespace(selected_course_ids=["CS230", "CS231n"])

    goal_repo.get_by_user_id = get_by_user_id

    context = await AgentContextService(goal_repo).resolve(SimpleNamespace(id=user_id))

    assert context.allowed_course_ids == ["CS230", "CS231n"]
    assert context.scope == "current_path"


@pytest.mark.asyncio
async def test_context_resolver_does_not_fallback_to_all_courses():
    goal_repo = SimpleNamespace()

    async def get_by_user_id(user_id):
        return None

    goal_repo.get_by_user_id = get_by_user_id

    context = await AgentContextService(goal_repo).resolve(SimpleNamespace(id=uuid4()))

    assert context.allowed_course_ids == []


def test_context_checks_canonical_unit_course_scope():
    context = SimpleNamespace(allowed_course_ids=["CS230", "CS231n"])

    assert AgentContextService.unit_in_scope(SimpleNamespace(course_id="cs231n"), context) is True
    assert AgentContextService.unit_in_scope(SimpleNamespace(course_id="CS224n"), context) is False
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_context_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement context service**

Create `src/services/agent_context_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentContext:
    user_id: str
    allowed_course_ids: list[str]
    scope: str = "current_path"


class AgentContextService:
    def __init__(self, goal_preference_repo):
        self.goal_preference_repo = goal_preference_repo

    async def resolve(self, user) -> AgentContext:
        goal = await self.goal_preference_repo.get_by_user_id(user.id)
        selected = list(getattr(goal, "selected_course_ids", None) or [])
        return AgentContext(
            user_id=str(user.id),
            allowed_course_ids=[str(course_id) for course_id in selected],
        )

    @staticmethod
    def unit_in_scope(unit, context: AgentContext) -> bool:
        allowed = {course_id.lower() for course_id in context.allowed_course_ids}
        return str(getattr(unit, "course_id", "")).lower() in allowed
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_context_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_context_service.py tests/services/test_agent_context_service.py
git commit -m "feat: add path agent context resolver"
```

---

### Task 4: Repository Helpers For Agent Data

**Files:**
- Modify: `src/repositories/canonical_content_repo.py`
- Test: `tests/repositories/test_canonical_content_repo.py`

- [ ] **Step 1: Add repository tests**

Append to `tests/repositories/test_canonical_content_repo.py`:

```python
@pytest.mark.asyncio
async def test_search_units_skips_empty_query():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.search_agent_units("", ["CS231n"]) == []
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_runtime_navigation_for_canonical_units_skips_empty_ids():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_runtime_navigation_for_canonical_units([]) == {}
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_unit_kp_concepts_skips_empty_ids():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_unit_kp_concepts([]) == []
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_agent_unit_context_skips_empty_id():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_agent_unit_context("") is None
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_transcript_snippets_for_unit_skips_empty_id():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_transcript_snippets_for_unit("", max_snippets=3) == []
    assert session.execute.await_count == 0
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/repositories/test_canonical_content_repo.py -q
```

Expected: FAIL with missing methods.

- [ ] **Step 3: Implement repository helpers**

Modify `src/repositories/canonical_content_repo.py`.

Add imports:

```python
from dataclasses import dataclass
from sqlalchemy import String, and_, cast, not_
```

Add dataclasses after imports:

```python
@dataclass(slots=True)
class AgentUnitSearchRow:
    unit: CanonicalUnit
    quiz_count: int
    score: float


@dataclass(slots=True)
class RuntimeNavigationRow:
    canonical_unit_id: str
    learning_unit_id: UUID
    course_id: UUID
    course_slug: str | None
    unit_slug: str | None
    learn_href: str | None


@dataclass(slots=True)
class AgentUnitContextRow:
    unit: CanonicalUnit
    kp_rows: list[tuple[UnitKPMap, ConceptKP]]
    navigation: RuntimeNavigationRow | None


@dataclass(slots=True)
class AgentTranscriptSnippetRow:
    start_sec: int
    end_sec: int
    text: str
    source: str
```

Add methods inside `CanonicalContentRepository`:

```python
    async def search_agent_units(
        self,
        query: str,
        course_ids: list[str],
        limit: int = 5,
    ) -> list[AgentUnitSearchRow]:
        clean_query = query.strip()
        if not clean_query or not course_ids:
            return []

        selected_lower = [course_id.lower() for course_id in course_ids]
        hidden_filter = and_(
            or_(
                CanonicalUnit.section_flags.is_(None),
                and_(
                    not_(CanonicalUnit.section_flags.contains(["logistics"])),
                    not_(CanonicalUnit.section_flags.contains(["admin"])),
                    not_(CanonicalUnit.section_flags.contains(["administrative"])),
                    not_(CanonicalUnit.section_flags.contains(["reference"])),
                ),
            ),
            or_(
                CanonicalUnit.content_type.is_(None),
                CanonicalUnit.content_type.not_in(("logistics", "admin", "administrative", "reference")),
            ),
            CanonicalUnit.is_worth_learning.is_not(False),
        )
        like_terms = [term for term in clean_query.lower().split() if len(term) >= 2][:8]
        like_filter = None
        for term in like_terms:
            pattern = f"%{term}%"
            term_filter = or_(
                func.lower(CanonicalUnit.unit_name).like(pattern),
                func.lower(CanonicalUnit.lecture_title).like(pattern),
                func.lower(CanonicalUnit.summary).like(pattern),
                func.lower(cast(CanonicalUnit.key_points, String)).like(pattern),
            )
            like_filter = term_filter if like_filter is None else or_(like_filter, term_filter)

        if like_filter is None:
            return []

        quiz_count = (
            select(
                QuestionBankItem.unit_id.label("unit_id"),
                func.count(func.distinct(QuestionBankItem.item_id)).label("quiz_count"),
            )
            .join(ItemPhaseMap, ItemPhaseMap.item_id == QuestionBankItem.item_id)
            .where(
                ItemPhaseMap.phase.in_(
                    (
                        "placement",
                        "mini_quiz",
                        "skip_verification",
                        "bridge_check",
                        "final_quiz",
                        "review",
                    )
                ),
                QuestionBankItem.qa_gate_passed.is_not(False),
            )
            .group_by(QuestionBankItem.unit_id)
            .subquery()
        )

        result = await self.session.execute(
            select(
                CanonicalUnit,
                func.coalesce(quiz_count.c.quiz_count, 0).label("quiz_count"),
            )
            .outerjoin(quiz_count, quiz_count.c.unit_id == CanonicalUnit.unit_id)
            .where(
                func.lower(CanonicalUnit.course_id).in_(selected_lower),
                CanonicalUnit.active.is_(True),
                hidden_filter,
                like_filter,
            )
            .order_by(CanonicalUnit.course_id, CanonicalUnit.lecture_order, CanonicalUnit.ordering_index)
            .limit(limit)
        )

        rows: list[AgentUnitSearchRow] = []
        for unit, count in result.all():
            score = 1.0
            if clean_query.lower() in (unit.unit_name or "").lower():
                score += 2.0
            if getattr(unit, "content_type", None) in {"core_theory", "prerequisite", "foundation"}:
                score += 0.5
            if getattr(unit, "salience_score", None) in {"critical", "high"}:
                score += 0.5
            if int(count or 0) > 0:
                score += 0.25
            rows.append(AgentUnitSearchRow(unit=unit, quiz_count=int(count or 0), score=score))
        return rows

    async def get_runtime_navigation_for_canonical_units(
        self,
        canonical_unit_ids: list[str],
    ) -> dict[str, RuntimeNavigationRow]:
        if not canonical_unit_ids:
            return {}

        result = await self.session.execute(
            select(LearningUnit, Course)
            .join(Course, LearningUnit.course_id == Course.id)
            .where(LearningUnit.canonical_unit_id.in_(canonical_unit_ids))
        )
        rows: dict[str, RuntimeNavigationRow] = {}
        for learning_unit, course in result.all():
            canonical_id = str(learning_unit.canonical_unit_id)
            course_slug = getattr(course, "slug", None)
            unit_slug = getattr(learning_unit, "slug", None)
            rows[canonical_id] = RuntimeNavigationRow(
                canonical_unit_id=canonical_id,
                learning_unit_id=learning_unit.id,
                course_id=course.id,
                course_slug=course_slug,
                unit_slug=unit_slug,
                learn_href=f"/courses/{course_slug}/learn/{unit_slug}"
                if course_slug and unit_slug
                else None,
            )
        return rows

    async def get_unit_kp_concepts(self, canonical_unit_ids: list[str]) -> list[tuple[UnitKPMap, ConceptKP]]:
        if not canonical_unit_ids:
            return []
        result = await self.session.execute(
            select(UnitKPMap, ConceptKP)
            .join(ConceptKP, ConceptKP.kp_id == UnitKPMap.kp_id)
            .where(UnitKPMap.unit_id.in_(canonical_unit_ids))
        )
        return list(result.all())

    async def get_agent_unit_context(self, canonical_unit_id: str) -> AgentUnitContextRow | None:
        if not canonical_unit_id:
            return None
        unit = await self.session.get(CanonicalUnit, canonical_unit_id)
        if unit is None:
            return None
        kp_rows = await self.get_unit_kp_concepts([canonical_unit_id])
        navigation = (await self.get_runtime_navigation_for_canonical_units([canonical_unit_id])).get(
            canonical_unit_id
        )
        return AgentUnitContextRow(unit=unit, kp_rows=kp_rows, navigation=navigation)

    async def get_transcript_snippets_for_unit(
        self,
        canonical_unit_id: str,
        max_snippets: int = 3,
    ) -> list[AgentTranscriptSnippetRow]:
        if not canonical_unit_id:
            return []
        unit = await self.session.get(CanonicalUnit, canonical_unit_id)
        if unit is None:
            return []
        clip = unit.video_clip_ref or {}
        content_ref = unit.content_ref or {}
        start_sec = int(clip.get("start_sec") or content_ref.get("start_sec") or 0)
        end_sec = int(clip.get("end_sec") or content_ref.get("end_sec") or start_sec)
        text_value = unit.summary or unit.description or unit.unit_name
        return [
            AgentTranscriptSnippetRow(
                start_sec=start_sec,
                end_sec=end_sec,
                text=text_value,
                source="summary",
            )
        ][:max_snippets]
```

- [ ] **Step 4: Run repository tests**

Run:

```bash
pytest tests/repositories/test_canonical_content_repo.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/repositories/canonical_content_repo.py tests/repositories/test_canonical_content_repo.py
git commit -m "feat: add agent content repository helpers"
```

---

### Task 5: Runtime Navigation Resolver

**Files:**
- Create: `src/services/agent_navigation_service.py`
- Test: `tests/services/test_agent_navigation_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_navigation_service.py`:

```python
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services.agent_navigation_service import RuntimeNavigationResolver


@pytest.mark.asyncio
async def test_resolves_navigation_from_repository():
    repo = SimpleNamespace()
    learning_unit_id = uuid4()
    course_id = uuid4()

    async def get_runtime_navigation_for_canonical_units(ids):
        return {
            "unit-a": SimpleNamespace(
                canonical_unit_id="unit-a",
                learning_unit_id=learning_unit_id,
                course_id=course_id,
                course_slug="cs231n",
                unit_slug="lecture-05-seg6",
                learn_href="/courses/cs231n/learn/lecture-05-seg6",
            )
        }

    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    resolver = RuntimeNavigationResolver(repo)
    result = await resolver.resolve(["unit-a"])

    assert result["unit-a"].learn_href == "/courses/cs231n/learn/lecture-05-seg6"
    assert result["unit-a"].source == "product_learning_unit"


@pytest.mark.asyncio
async def test_missing_navigation_is_non_actionable():
    repo = SimpleNamespace()

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    resolver = RuntimeNavigationResolver(repo)
    result = await resolver.resolve(["unit-a"])

    assert result["unit-a"].learn_href is None
    assert result["unit-a"].source == "missing"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_navigation_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement service**

Create `src/services/agent_navigation_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class RuntimeNavigationTarget:
    canonical_unit_id: str
    learning_unit_id: str | None
    course_id: str | None
    course_slug: str | None
    unit_slug: str | None
    learn_href: str | None
    source: str


class RuntimeNavigationResolver:
    def __init__(self, content_repo):
        self.content_repo = content_repo

    async def resolve(self, canonical_unit_ids: list[str]) -> dict[str, RuntimeNavigationTarget]:
        if not canonical_unit_ids:
            return {}

        rows = await self.content_repo.get_runtime_navigation_for_canonical_units(canonical_unit_ids)
        resolved: dict[str, RuntimeNavigationTarget] = {}
        for unit_id in canonical_unit_ids:
            row = rows.get(unit_id)
            if row is None:
                resolved[unit_id] = RuntimeNavigationTarget(
                    canonical_unit_id=unit_id,
                    learning_unit_id=None,
                    course_id=None,
                    course_slug=None,
                    unit_slug=None,
                    learn_href=None,
                    source="missing",
                )
                continue
            resolved[unit_id] = RuntimeNavigationTarget(
                canonical_unit_id=unit_id,
                learning_unit_id=str(row.learning_unit_id),
                course_id=str(row.course_id),
                course_slug=row.course_slug,
                unit_slug=row.unit_slug,
                learn_href=row.learn_href,
                source="product_learning_unit",
            )
        return resolved
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_navigation_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_navigation_service.py tests/services/test_agent_navigation_service.py
git commit -m "feat: add agent runtime navigation resolver"
```

---

### Task 6: Unit Search Service

**Files:**
- Create: `src/services/agent_search_service.py`
- Test: `tests/services/test_agent_search_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_search_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.schemas.agent import UnitSearchRequest
from src.services.agent_search_service import UnitSearchService


@pytest.mark.asyncio
async def test_search_intersects_requested_courses_with_allowed_courses():
    repo = SimpleNamespace()
    captured = {}

    async def search_agent_units(query, course_ids, limit):
        captured["course_ids"] = course_ids
        return []

    repo.search_agent_units = search_agent_units

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    service = UnitSearchService(repo)
    response = await service.search(
        UnitSearchRequest(query="CNN", courseIds=["CS231n", "CS999"]),
        allowed_course_ids=["CS231n"],
    )

    assert captured["course_ids"] == ["CS231n"]
    assert response.trace.applied_filters == [
        "course_scope:CS231n",
        "content_policy:exclude_hidden_reference_logistics",
    ]


@pytest.mark.asyncio
async def test_search_returns_navigation_and_quiz_metadata():
    unit = SimpleNamespace(
        unit_id="unit-a",
        course_id="CS231n",
        lecture_id="lecture-05",
        lecture_title="Lecture 5",
        unit_name="Receptive fields",
        summary="Effective receptive field.",
        content_type="core_theory",
        salience_score="medium",
    )
    repo = SimpleNamespace()

    async def search_agent_units(query, course_ids, limit):
        return [SimpleNamespace(unit=unit, quiz_count=3, score=4.2)]

    async def get_runtime_navigation_for_canonical_units(ids):
        return {
            "unit-a": SimpleNamespace(
                learning_unit_id="lu-a",
                course_id="course-a",
                course_slug="cs231n",
                unit_slug="lecture-05-seg6",
                learn_href="/courses/cs231n/learn/lecture-05-seg6",
            )
        }

    repo.search_agent_units = search_agent_units
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    service = UnitSearchService(repo)
    response = await service.search(UnitSearchRequest(query="RF in CNNs"), ["CS231n"])

    assert response.results[0].canonical_unit_id == "unit-a"
    assert response.results[0].has_quiz_items is True
    assert response.results[0].learn_href == "/courses/cs231n/learn/lecture-05-seg6"
    assert response.results[0].navigation_resolution == "product_learning_unit"


@pytest.mark.asyncio
async def test_search_trace_records_content_policy_filter():
    repo = SimpleNamespace()

    async def search_agent_units(query, course_ids, limit):
        return []

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    repo.search_agent_units = search_agent_units
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units

    response = await UnitSearchService(repo).search(UnitSearchRequest(query="course intro"), ["CS230"])

    assert "content_policy:exclude_hidden_reference_logistics" in response.trace.applied_filters
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_search_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement service**

Create `src/services/agent_search_service.py`:

```python
from __future__ import annotations

from uuid import uuid4

from src.schemas.agent import (
    QueryExpansion,
    RetrievalTrace,
    RuntimeNavigationTrace,
    UnitSearchRequest,
    UnitSearchResponse,
    UnitSearchResult,
)
from src.services.agent_navigation_service import RuntimeNavigationResolver
from src.services.agent_query_normalizer import normalize_agent_query


class UnitSearchService:
    def __init__(self, content_repo):
        self.content_repo = content_repo

    async def search(
        self,
        request: UnitSearchRequest,
        allowed_course_ids: list[str],
    ) -> UnitSearchResponse:
        requested = request.course_ids or allowed_course_ids
        allowed_lower = {course_id.lower(): course_id for course_id in allowed_course_ids}
        scoped_course_ids = [
            allowed_lower[course_id.lower()]
            for course_id in requested
            if course_id.lower() in allowed_lower
        ]
        if not scoped_course_ids and request.scope == "global_catalog":
            scoped_course_ids = allowed_course_ids

        normalized = normalize_agent_query(request.query, course_ids=scoped_course_ids)
        rows = await self.content_repo.search_agent_units(
            normalized.normalized_query,
            scoped_course_ids,
            request.limit,
        )
        canonical_ids = [row.unit.unit_id for row in rows]
        navigation = await RuntimeNavigationResolver(self.content_repo).resolve(canonical_ids)

        results: list[UnitSearchResult] = []
        nav_trace: list[RuntimeNavigationTrace] = []
        for row in rows:
            unit = row.unit
            nav = navigation[unit.unit_id]
            nav_trace.append(
                RuntimeNavigationTrace(
                    canonical_unit_id=unit.unit_id,
                    source=nav.source,  # type: ignore[arg-type]
                    learn_href=nav.learn_href,
                )
            )
            reasons = ["text_match"]
            if row.quiz_count > 0:
                reasons.append("quiz_available")
            if nav.learn_href:
                reasons.append("runtime_navigation_available")
            results.append(
                UnitSearchResult(
                    canonical_unit_id=unit.unit_id,
                    learning_unit_id=nav.learning_unit_id,
                    course_id=unit.course_id,
                    course_slug=nav.course_slug,
                    lecture_id=unit.lecture_id,
                    lecture_title=unit.lecture_title,
                    unit_slug=nav.unit_slug,
                    learn_href=nav.learn_href,
                    unit_name=unit.unit_name,
                    summary=unit.summary,
                    score=float(row.score),
                    reasons=reasons,
                    has_quiz_items=row.quiz_count > 0,
                    content_type=unit.content_type,
                    salience_score=unit.salience_score,
                    actionable=bool(nav.learn_href),
                    navigation_resolution=nav.source,  # type: ignore[arg-type]
                )
            )

        return UnitSearchResponse(
            results=results,
            trace=RetrievalTrace(
                trace_id=str(uuid4()),
                intent=request.intent,
                raw_query=request.query,
                normalized_query=normalized.normalized_query,
                query_expansions=normalized.expansions,
                resolved_scope=request.scope or "current_path",
                candidate_courses=scoped_course_ids,
                applied_filters=(
                    [f"course_scope:{','.join(scoped_course_ids)}"] if scoped_course_ids else []
                )
                + ["content_policy:exclude_hidden_reference_logistics"],
                ranking_version="unit_search_v1",
                runtime_navigation_resolution=nav_trace,
                selected_unit_ids=canonical_ids,
            ),
        )
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_search_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_search_service.py tests/services/test_agent_search_service.py
git commit -m "feat: add path agent unit search service"
```

---

### Task 7: Path Requirement Service

**Files:**
- Create: `src/services/agent_requirement_service.py`
- Test: `tests/services/test_agent_requirement_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_requirement_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.schemas.agent import PathRequirementsRequest
from src.services.agent_requirement_service import PathRequirementService


@pytest.mark.asyncio
async def test_requirement_service_filters_target_courses_to_allowed_scope():
    repo = SimpleNamespace()

    async def get_linked_learning_units(course_ids):
        return []

    async def get_unit_kp_rows(ids):
        return []

    async def get_prerequisite_edges_for_kps(ids):
        return []

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    async def get_concepts_by_ids(ids):
        return []

    repo.get_linked_learning_units = get_linked_learning_units
    repo.get_unit_kp_rows = get_unit_kp_rows
    repo.get_prerequisite_edges_for_kps = get_prerequisite_edges_for_kps
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units
    repo.get_concepts_by_ids = get_concepts_by_ids

    service = PathRequirementService(repo)
    response = await service.get_requirements(
        PathRequirementsRequest(
            targetPathKey="nlp",
            targetCourseIds=["CS224n", "CS999"],
            sourceCourseIds=["CS230", "CS999"],
        ),
        allowed_course_ids=["CS224n", "CS230"],
    )

    assert response.trace.selected_course_ids == ["CS224n"]
    assert "target_course_scope:CS224n" in response.trace.applied_filters


@pytest.mark.asyncio
async def test_requirement_service_maps_prerequisite_kp_back_to_source_unit():
    target_unit = SimpleNamespace(canonical_unit_id="target-unit")
    source_unit = SimpleNamespace(
        canonical_unit_id="source-unit",
        title="Backpropagation",
    )
    target_kp = SimpleNamespace(unit_id="target-unit", kp_id="kp-target", planner_role="main")
    source_kp = SimpleNamespace(
        unit_id="source-unit",
        kp_id="kp-source",
        planner_role="main",
        coverage_weight=1.0,
    )
    edge = SimpleNamespace(source_kp_id="kp-source", target_kp_id="kp-target")

    repo = SimpleNamespace()

    async def get_linked_learning_units(course_ids):
        return [target_unit] if course_ids == ["CS224n"] else [source_unit]

    async def get_unit_kp_rows(ids):
        return [target_kp] if ids == ["target-unit"] else [source_kp]

    async def get_prerequisite_edges_for_kps(ids):
        return [edge]

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    async def get_concepts_by_ids(ids):
        return [SimpleNamespace(kp_id="kp-target", importance_level="high", structural_role="gateway")]

    repo.get_linked_learning_units = get_linked_learning_units
    repo.get_unit_kp_rows = get_unit_kp_rows
    repo.get_prerequisite_edges_for_kps = get_prerequisite_edges_for_kps
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units
    repo.get_concepts_by_ids = get_concepts_by_ids

    service = PathRequirementService(repo)
    response = await service.get_requirements(
        PathRequirementsRequest(targetPathKey="nlp", targetCourseIds=["CS224n"], sourceCourseIds=["CS230"]),
        allowed_course_ids=["CS224n", "CS230"],
    )

    assert response.required_units[0].canonical_unit_id == "source-unit"
    assert response.required_units[0].required_kp_ids == ["kp-source"]


@pytest.mark.asyncio
async def test_requirement_service_ignores_reference_and_mention_only_targets():
    target_unit = SimpleNamespace(canonical_unit_id="target-unit", content_type="reference")
    target_kp = SimpleNamespace(
        unit_id="target-unit",
        kp_id="kp-target",
        planner_role="support",
        coverage_level="mention",
    )
    repo = SimpleNamespace()

    async def get_linked_learning_units(course_ids):
        return [target_unit]

    async def get_unit_kp_rows(ids):
        return [target_kp]

    async def get_prerequisite_edges_for_kps(ids):
        raise AssertionError("mention-only reference targets must not query prerequisite edges")

    async def get_runtime_navigation_for_canonical_units(ids):
        return {}

    async def get_concepts_by_ids(ids):
        return [SimpleNamespace(kp_id="kp-target", importance_level="low", structural_role="support")]

    repo.get_linked_learning_units = get_linked_learning_units
    repo.get_unit_kp_rows = get_unit_kp_rows
    repo.get_prerequisite_edges_for_kps = get_prerequisite_edges_for_kps
    repo.get_runtime_navigation_for_canonical_units = get_runtime_navigation_for_canonical_units
    repo.get_concepts_by_ids = get_concepts_by_ids

    response = await PathRequirementService(repo).get_requirements(
        PathRequirementsRequest(targetPathKey="nlp", targetCourseIds=["CS224n"], sourceCourseIds=["CS230"]),
        allowed_course_ids=["CS224n", "CS230"],
    )

    assert response.required_units == []
    assert "target_content_policy:core_only" in response.trace.applied_filters
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_requirement_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement service**

Create `src/services/agent_requirement_service.py`:

```python
from __future__ import annotations

from uuid import uuid4

from src.config.goal_course_map import GOAL_COURSE_MAP
from src.schemas.agent import (
    PathRequirementTrace,
    PathRequirementUnit,
    PathRequirementsRequest,
    PathRequirementsResponse,
    RuntimeNavigationTrace,
)
from src.services.agent_navigation_service import RuntimeNavigationResolver


class PathRequirementService:
    def __init__(self, content_repo):
        self.content_repo = content_repo

    def _eligible_unit(self, unit) -> bool:
        flags = set(getattr(unit, "section_flags", None) or [])
        content_type = str(getattr(unit, "content_type", "") or "").lower()
        if flags.intersection({"logistics", "admin", "administrative", "reference"}):
            return False
        if content_type in {"logistics", "admin", "administrative", "reference"}:
            return False
        return getattr(unit, "is_worth_learning", True) is not False

    def _target_kp_row(self, row) -> bool:
        planner_role = str(getattr(row, "planner_role", "") or "").lower()
        coverage_level = str(getattr(row, "coverage_level", "") or "").lower()
        if coverage_level == "mention":
            return False
        return planner_role in {"main", "prereq", ""}

    def _target_concept(self, concept) -> bool:
        if concept is None:
            return True
        importance = str(getattr(concept, "importance_level", "") or "").lower()
        structural_role = str(getattr(concept, "structural_role", "") or "").lower()
        if structural_role == "gateway":
            return True
        return importance in {"critical", "high", "medium", ""}

    async def get_requirements(
        self,
        request: PathRequirementsRequest,
        allowed_course_ids: list[str],
    ) -> PathRequirementsResponse:
        allowed_lower = {course_id.lower(): course_id for course_id in allowed_course_ids}
        default_targets = GOAL_COURSE_MAP.get(request.target_path_key, [])
        requested_targets = request.target_course_ids or default_targets
        requested_sources = request.source_course_ids or allowed_course_ids
        target_courses = [
            allowed_lower[c.lower()] for c in requested_targets if c.lower() in allowed_lower
        ]
        source_courses = [
            allowed_lower[c.lower()] for c in requested_sources if c.lower() in allowed_lower
        ]

        target_units = [
            unit
            for unit in await self.content_repo.get_linked_learning_units(target_courses)
            if self._eligible_unit(unit)
        ]
        target_canonical_ids = [
            str(unit.canonical_unit_id)
            for unit in target_units
            if getattr(unit, "canonical_unit_id", None)
        ]
        target_kp_rows = await self.content_repo.get_unit_kp_rows(target_canonical_ids)
        target_concepts = await self.content_repo.get_concepts_by_ids(
            sorted({row.kp_id for row in target_kp_rows})
        )
        target_concept_by_id = {concept.kp_id: concept for concept in target_concepts}
        target_kp_ids = sorted(
            {
                row.kp_id
                for row in target_kp_rows
                if self._target_kp_row(row)
                and self._target_concept(target_concept_by_id.get(row.kp_id))
            }
        )

        all_edges = []
        prereq_kp_ids: set[str] = set()
        frontier = target_kp_ids
        for _ in range(request.prerequisite_depth):
            if not frontier:
                break
            edges = await self.content_repo.get_prerequisite_edges_for_kps(frontier)
            all_edges.extend(edges)
            next_frontier = {
                edge.source_kp_id
                for edge in edges
                if edge.target_kp_id in frontier and edge.source_kp_id not in prereq_kp_ids
            }
            prereq_kp_ids.update(next_frontier)
            frontier = sorted(next_frontier)

        source_units = [
            unit
            for unit in await self.content_repo.get_linked_learning_units(source_courses)
            if self._eligible_unit(unit)
        ]
        source_canonical_ids = [
            str(unit.canonical_unit_id)
            for unit in source_units
            if getattr(unit, "canonical_unit_id", None)
        ]
        source_kp_rows = await self.content_repo.get_unit_kp_rows(source_canonical_ids)
        unit_to_kps: dict[str, set[str]] = {}
        for row in source_kp_rows:
            if row.kp_id in prereq_kp_ids and self._target_kp_row(row):
                unit_to_kps.setdefault(row.unit_id, set()).add(row.kp_id)

        mastery_by_kp = {}
        if request.include_mastery and hasattr(self.content_repo, "get_mastery_lcb_by_kp_ids"):
            mastery_by_kp = await self.content_repo.get_mastery_lcb_by_kp_ids(sorted(prereq_kp_ids))

        navigation = await RuntimeNavigationResolver(self.content_repo).resolve(list(unit_to_kps))
        units_by_canonical = {str(unit.canonical_unit_id): unit for unit in source_units}
        required_units: list[PathRequirementUnit] = []
        nav_trace: list[RuntimeNavigationTrace] = []
        for canonical_id in sorted(unit_to_kps):
            nav = navigation[canonical_id]
            nav_trace.append(
                RuntimeNavigationTrace(
                    canonical_unit_id=canonical_id,
                    source=nav.source,  # type: ignore[arg-type]
                    learn_href=nav.learn_href,
                )
            )
            unit = units_by_canonical.get(canonical_id)
            mastery_values = [
                mastery_by_kp[kp_id]
                for kp_id in unit_to_kps[canonical_id]
                if kp_id in mastery_by_kp
            ]
            min_mastery = min(mastery_values) if mastery_values else None
            status = (
                "already_mastered"
                if min_mastery is not None and min_mastery >= 0.8
                else "needs_review"
                if min_mastery is not None and min_mastery >= 0.5
                else "unassessed"
            )
            required_units.append(
                PathRequirementUnit(
                    canonical_unit_id=canonical_id,
                    learning_unit_id=nav.learning_unit_id,
                    course_id=nav.course_id or "",
                    course_slug=nav.course_slug,
                    unit_slug=nav.unit_slug,
                    learn_href=nav.learn_href,
                    unit_name=getattr(unit, "title", canonical_id),
                    required_kp_ids=sorted(unit_to_kps[canonical_id]),
                    prerequisite_for=target_kp_ids,
                    mastery_lcb=min_mastery,
                    status=status,
                    reasons=["required_prerequisite", "prerequisite_kp_match"],
                )
            )

        return PathRequirementsResponse(
            requiredUnits=required_units,
            trace=PathRequirementTrace(
                trace_id=str(uuid4()),
                target_path=request.target_path_key,
                selected_path=request.target_path_key,
                selected_course_ids=target_courses,
                prerequisite_depth=request.prerequisite_depth,
                graph_edges_considered=len(all_edges),
                applied_filters=[
                    f"target_course_scope:{','.join(target_courses)}",
                    "target_content_policy:core_only",
                    "kp_policy:main_prereq_not_mention",
                ],
                ranking_version="path_requirements_v1",
                runtime_navigation_resolution=nav_trace,
            ),
        )
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_requirement_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_requirement_service.py tests/services/test_agent_requirement_service.py
git commit -m "feat: add path requirement service"
```

---

### Task 8: Unit Context Service

**Files:**
- Create: `src/services/agent_unit_context_service.py`
- Test: `tests/services/test_agent_unit_context_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_unit_context_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.services.agent_unit_context_service import AgentUnitContextService


@pytest.mark.asyncio
async def test_unit_context_returns_kps_navigation_and_snippets():
    unit = SimpleNamespace(
        unit_id="unit-a",
        course_id="CS231n",
        lecture_id="lecture-05",
        lecture_title="Lecture 5",
        unit_name="Receptive fields",
        summary="How convolution kernels see local image regions.",
        key_points=["local receptive field"],
        video_clip_ref={"start_sec": 3200, "end_sec": 3340},
    )
    kp = SimpleNamespace(kp_id="kp-rf", name="Receptive field")
    context_row = SimpleNamespace(
        unit=unit,
        kp_rows=[(SimpleNamespace(kp_id="kp-rf"), kp)],
        navigation=SimpleNamespace(learn_href="/courses/cs231n/learn/lecture-05-seg6"),
    )
    repo = SimpleNamespace()

    async def get_agent_unit_context(canonical_unit_id):
        return context_row

    async def get_transcript_snippets_for_unit(canonical_unit_id, max_snippets=3):
        return [
            SimpleNamespace(
                start_sec=3200,
                end_sec=3340,
                text="Convolutional layers use local receptive fields.",
                source="summary",
            )
        ]

    repo.get_agent_unit_context = get_agent_unit_context
    repo.get_transcript_snippets_for_unit = get_transcript_snippets_for_unit

    response = await AgentUnitContextService(repo).get_context(
        "unit-a",
        allowed_course_ids=["CS231n"],
    )

    assert response.canonical_unit_id == "unit-a"
    assert response.kp_ids == ["kp-rf"]
    assert response.learn_href == "/courses/cs231n/learn/lecture-05-seg6"
    assert response.snippets[0].start_sec == 3200


@pytest.mark.asyncio
async def test_unit_context_rejects_out_of_scope_unit():
    repo = SimpleNamespace()

    async def get_agent_unit_context(canonical_unit_id):
        return SimpleNamespace(unit=SimpleNamespace(course_id="CS224n"))

    repo.get_agent_unit_context = get_agent_unit_context
    repo.get_transcript_snippets_for_unit = get_agent_unit_context

    with pytest.raises(PermissionError, match="canonical_unit_out_of_scope"):
        await AgentUnitContextService(repo).get_context("unit-a", allowed_course_ids=["CS231n"])


@pytest.mark.asyncio
async def test_unit_context_raises_for_missing_unit():
    repo = SimpleNamespace()

    async def get_agent_unit_context(canonical_unit_id):
        return None

    repo.get_agent_unit_context = get_agent_unit_context
    repo.get_transcript_snippets_for_unit = get_agent_unit_context

    with pytest.raises(ValueError, match="canonical_unit_not_found"):
        await AgentUnitContextService(repo).get_context("missing-unit", allowed_course_ids=["CS231n"])
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_unit_context_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement service**

Create `src/services/agent_unit_context_service.py`:

```python
from __future__ import annotations

from uuid import uuid4

from src.schemas.agent import RetrievalTrace, TranscriptSnippet, UnitContextResponse


class AgentUnitContextService:
    def __init__(self, content_repo):
        self.content_repo = content_repo

    async def get_context(
        self,
        canonical_unit_id: str,
        allowed_course_ids: list[str],
        max_snippets: int = 3,
    ) -> UnitContextResponse:
        context = await self.content_repo.get_agent_unit_context(canonical_unit_id)
        if context is None:
            raise ValueError("canonical_unit_not_found")

        unit = context.unit
        allowed = {course_id.lower() for course_id in allowed_course_ids}
        if str(unit.course_id).lower() not in allowed:
            raise PermissionError("canonical_unit_out_of_scope")
        snippets = await self.content_repo.get_transcript_snippets_for_unit(
            canonical_unit_id,
            max_snippets=max_snippets,
        )
        kp_ids = [kp.kp_id for _, kp in context.kp_rows]
        key_points = list(unit.key_points or [])
        navigation = context.navigation

        return UnitContextResponse(
            canonical_unit_id=unit.unit_id,
            course_id=unit.course_id,
            lecture_id=unit.lecture_id,
            lecture_title=unit.lecture_title,
            unit_name=unit.unit_name,
            summary=unit.summary,
            key_points=key_points,
            kp_ids=kp_ids,
            learn_href=getattr(navigation, "learn_href", None),
            start_sec=(unit.video_clip_ref or {}).get("start_sec"),
            end_sec=(unit.video_clip_ref or {}).get("end_sec"),
            snippets=[
                TranscriptSnippet(
                    start_sec=snippet.start_sec,
                    end_sec=snippet.end_sec,
                    text=snippet.text,
                    source=snippet.source,
                )
                for snippet in snippets
            ],
            trace=RetrievalTrace(
                trace_id=str(uuid4()),
                normalized_query=canonical_unit_id,
                resolved_scope="current_path",
                ranking_version="unit_context_v1",
                selected_unit_ids=[canonical_unit_id],
            ),
        )

    async def get_transcript_snippets(
        self,
        canonical_unit_id: str,
        allowed_course_ids: list[str],
        max_snippets: int = 5,
    ) -> list[TranscriptSnippet]:
        context = await self.content_repo.get_agent_unit_context(canonical_unit_id)
        if context is None:
            raise ValueError("canonical_unit_not_found")
        allowed = {course_id.lower() for course_id in allowed_course_ids}
        if str(context.unit.course_id).lower() not in allowed:
            raise PermissionError("canonical_unit_out_of_scope")
        snippets = await self.content_repo.get_transcript_snippets_for_unit(
            canonical_unit_id,
            max_snippets=max_snippets,
        )
        return [
            TranscriptSnippet(
                start_sec=snippet.start_sec,
                end_sec=snippet.end_sec,
                text=snippet.text,
                source=snippet.source,
            )
            for snippet in snippets
        ]
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_unit_context_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_unit_context_service.py tests/services/test_agent_unit_context_service.py
git commit -m "feat: add agent unit context service"
```

---

### Task 9: Agent Chat Orchestrator

**Files:**
- Create: `src/services/agent_chat_service.py`
- Test: `tests/services/test_agent_chat_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_chat_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.schemas.agent import AgentChatRequest, RetrievalTrace, UnitSearchResponse
from src.services.agent_chat_service import AgentChatService


@pytest.mark.asyncio
async def test_chat_uses_path_requirements_for_required_parts_question():
    search_service = SimpleNamespace()
    requirement_service = SimpleNamespace()

    async def get_requirements(request, allowed_course_ids):
        return SimpleNamespace(
            required_units=[
                SimpleNamespace(
                    canonical_unit_id="unit-a",
                    course_id="CS230",
                    unit_name="Backpropagation",
                    learn_href="/courses/cs230/learn/lecture-02-seg4",
                    required_kp_ids=["kp-backprop"],
                )
            ],
            trace=SimpleNamespace(
                trace_id="trace-req",
                selected_course_ids=["CS224n"],
                runtime_navigation_resolution=[],
            ),
        )

    requirement_service.get_requirements = get_requirements
    service = AgentChatService(search_service, requirement_service)

    response = await service.chat(
        AgentChatRequest(message="Which DL parts are required for NLP?"),
        allowed_course_ids=["CS230", "CS224n"],
        is_reviewer=False,
    )

    assert response.answer.confidence == "grounded"
    assert response.citations[0].canonical_unit_id == "unit-a"
    assert response.actions[0].type == "open_unit"
    assert response.trace is not None


@pytest.mark.asyncio
async def test_chat_hides_requirement_trace_when_requested():
    search_service = SimpleNamespace()
    requirement_service = SimpleNamespace()

    async def get_requirements(request, allowed_course_ids):
        return SimpleNamespace(required_units=[], trace=SimpleNamespace(trace_id="trace-req"))

    requirement_service.get_requirements = get_requirements
    service = AgentChatService(search_service, requirement_service)

    response = await service.chat(
        AgentChatRequest(message="Which DL parts are required for NLP?", traceMode="none"),
        allowed_course_ids=["CS230", "CS224n"],
        is_reviewer=False,
    )

    assert response.trace is None


@pytest.mark.asyncio
async def test_chat_downgrades_full_trace_for_normal_user():
    trace = RetrievalTrace(
        trace_id="trace-1",
        normalized_query="receptive field",
        resolved_scope="current_path",
        candidate_courses=["CS231n"],
        ranking_version="unit_search_v1",
    )
    search_service = SimpleNamespace()

    async def search(request, allowed_course_ids):
        return UnitSearchResponse(results=[], trace=trace)

    search_service.search = search
    requirement_service = SimpleNamespace()
    service = AgentChatService(search_service, requirement_service)

    response = await service.chat(
        AgentChatRequest(message="Where is receptive field taught?", traceMode="full"),
        allowed_course_ids=["CS231n"],
        is_reviewer=False,
    )

    assert response.trace is not None
    assert response.trace.candidate_courses == []
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_chat_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement orchestrator**

Create `src/services/agent_chat_service.py`:

```python
from __future__ import annotations

from uuid import uuid4

from src.schemas.agent import (
    AgentAnswer,
    AgentChatRequest,
    AgentChatResponse,
    AgentFallback,
    PathRequirementsRequest,
    RetrievalTrace,
    UnitSearchRequest,
)


class AgentChatService:
    def __init__(self, search_service, requirement_service):
        self.search_service = search_service
        self.requirement_service = requirement_service

    def _filter_trace(
        self,
        trace: RetrievalTrace,
        request: AgentChatRequest,
        is_reviewer: bool,
    ) -> RetrievalTrace | None:
        if request.trace_mode == "none":
            return None
        if request.trace_mode == "full" and not is_reviewer:
            return RetrievalTrace(
                trace_id=trace.trace_id,
                intent=trace.intent,
                raw_query=trace.raw_query,
                normalized_query=trace.normalized_query,
                resolved_scope=trace.resolved_scope,
                applied_filters=trace.applied_filters,
                ranking_version=trace.ranking_version,
                selected_unit_ids=trace.selected_unit_ids,
            )
        return trace

    async def chat(
        self,
        request: AgentChatRequest,
        allowed_course_ids: list[str],
        is_reviewer: bool = False,
    ) -> AgentChatResponse:
        message_lower = request.message.lower()
        if "required for nlp" in message_lower or "dl parts" in message_lower:
            requirements = await self.requirement_service.get_requirements(
                PathRequirementsRequest(targetPathKey="nlp"),
                allowed_course_ids=allowed_course_ids,
            )
            answer = "I checked the path requirement graph for NLP prerequisites."
            if not requirements.required_units:
                answer = "I could not find required prerequisite units in the current scoped path."
            citations = [
                {
                    "canonical_unit_id": unit.canonical_unit_id,
                    "course_id": unit.course_id,
                    "unit_name": unit.unit_name,
                    "learn_href": unit.learn_href,
                    "source": "planner",
                }
                for unit in requirements.required_units[:5]
            ]
            actions = [
                {
                    "type": "open_unit",
                    "label": f"Open {unit.unit_name}",
                    "learn_href": unit.learn_href,
                    "canonical_unit_id": unit.canonical_unit_id,
                }
                for unit in requirements.required_units[:3]
                if unit.learn_href
            ]
            trace = RetrievalTrace(
                trace_id=requirements.trace.trace_id,
                intent="ask_what_next",
                raw_query=request.message,
                normalized_query=request.message,
                resolved_scope="current_path",
                selected_path="nlp",
                candidate_courses=getattr(requirements.trace, "selected_course_ids", []),
                applied_filters=getattr(requirements.trace, "applied_filters", []),
                ranking_version="path_requirements_v1",
                runtime_navigation_resolution=getattr(
                    requirements.trace,
                    "runtime_navigation_resolution",
                    [],
                ),
                selected_unit_ids=[
                    unit.canonical_unit_id for unit in requirements.required_units[:5]
                ],
            )
            return AgentChatResponse(
                conversation_id=request.conversation_id or str(uuid4()),
                message_id=str(uuid4()),
                answer=AgentAnswer(
                    markdown=answer,
                    confidence="grounded" if requirements.required_units else "no_source",
                ),
                citations=citations,
                actions=actions,
                trace=self._filter_trace(trace, request, is_reviewer),
            )

        search = await self.search_service.search(
            UnitSearchRequest(query=request.message, scope="current_path"),
            allowed_course_ids=allowed_course_ids,
        )
        citations = []
        actions = []
        for result in search.results[:3]:
            citations.append(
                {
                    "canonical_unit_id": result.canonical_unit_id,
                    "course_id": result.course_id,
                    "lecture_id": result.lecture_id,
                    "lecture_title": result.lecture_title,
                    "unit_name": result.unit_name,
                    "learn_href": result.learn_href,
                    "source": "summary",
                }
            )
            if result.learn_href:
                actions.append(
                    {
                        "type": "open_unit",
                        "label": f"Open {result.unit_name}",
                        "learn_href": result.learn_href,
                        "canonical_unit_id": result.canonical_unit_id,
                    }
                )

        return AgentChatResponse(
            conversation_id=request.conversation_id or str(uuid4()),
            message_id=str(uuid4()),
            answer=AgentAnswer(
                markdown="I found relevant learning units." if citations else "I could not find a grounded source.",
                confidence="grounded" if citations else "no_source",
            ),
            citations=citations,
            actions=actions,
            fallback=None if citations else AgentFallback(
                reason="no_retrieval_result",
                message="No grounded unit matched the query in your current scope.",
            ),
            trace=self._filter_trace(search.trace, request, is_reviewer),
        )
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/services/test_agent_chat_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/agent_chat_service.py tests/services/test_agent_chat_service.py
git commit -m "feat: add path agent chat orchestrator"
```

---

### Task 10: Agent Router And App Wiring

**Files:**
- Create: `src/routers/agent.py`
- Modify: `src/api/app.py`
- Test: `tests/contract/test_agent_routes.py`

- [ ] **Step 1: Write route contract tests**

Create `tests/contract/test_agent_routes.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.database import get_async_db
from src.dependencies.auth import get_current_user


pytestmark = pytest.mark.anyio


async def override_db():
    yield object()


@pytest.fixture(autouse=True)
def agent_route_overrides():
    user = SimpleNamespace(id=uuid4(), is_onboarded=True)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_async_db] = override_db
    try:
        yield user
    finally:
        app.dependency_overrides.clear()


async def test_agent_chat_endpoint_returns_structured_response():
    expected = {
        "conversation_id": "conv-1",
        "message_id": "msg-1",
        "answer": {"markdown": "Found it.", "confidence": "grounded"},
        "citations": [],
        "actions": [],
        "fallback": None,
        "trace": None,
    }

    with (
        patch("src.routers.agent.AgentChatService.chat", new=AsyncMock(return_value=expected)),
        patch(
            "src.routers.agent._agent_context_for_user",
            new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS230", "CS231n"])),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post("/api/agent/chat", json={"message": "Where is CNN taught?"})

    assert response.status_code == 200
    assert response.json()["answer"]["confidence"] == "grounded"


async def test_agent_search_rejects_include_hidden_contract():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/agent/search-units",
            json={"query": "logistics", "includeHidden": True},
        )

    assert response.status_code == 422


async def test_agent_unit_context_endpoint_returns_context():
    expected = {
        "canonical_unit_id": "unit-a",
        "course_id": "CS231n",
        "lecture_id": "lecture-05",
        "lecture_title": "Lecture 5",
        "unit_name": "Receptive fields",
        "summary": "Convolution receptive fields.",
        "key_points": ["local receptive field"],
        "kp_ids": ["kp-rf"],
        "learn_href": "/courses/cs231n/learn/lecture-05-seg6",
        "start_sec": 3200,
        "end_sec": 3340,
        "snippets": [],
        "trace": {
            "trace_id": "trace-context",
            "normalized_query": "unit-a",
            "resolved_scope": "current_path",
            "ranking_version": "unit_context_v1",
        },
    }
    with patch(
        "src.routers.agent.AgentUnitContextService.get_context",
        new=AsyncMock(return_value=expected),
    ), patch(
        "src.routers.agent._agent_context_for_user",
        new=AsyncMock(return_value=SimpleNamespace(allowed_course_ids=["CS231n"])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get("/api/agent/unit-context/unit-a")

    assert response.status_code == 200
    assert response.json()["canonical_unit_id"] == "unit-a"


```

- [ ] **Step 2: Run route tests and verify failure**

Run:

```bash
pytest tests/contract/test_agent_routes.py -q
```

Expected: FAIL with 404 for `/api/agent/*`.

- [ ] **Step 3: Implement router**

Create `src/routers/agent.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.repositories.goal_preference_repo import GoalPreferenceRepository
from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    PathRequirementsRequest,
    PathRequirementsResponse,
    UnitContextResponse,
    UnitSearchRequest,
    UnitSearchResponse,
)
from src.services.agent_context_service import AgentContext, AgentContextService
from src.services.agent_chat_service import AgentChatService
from src.services.agent_requirement_service import PathRequirementService
from src.services.agent_search_service import UnitSearchService
from src.services.agent_unit_context_service import AgentUnitContextService


agent_router = APIRouter(prefix="/api/agent", tags=["Path Agent"])


async def _agent_context_for_user(user: User, db: AsyncSession) -> AgentContext:
    return await AgentContextService(GoalPreferenceRepository(db)).resolve(user)


@agent_router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    body: AgentChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentChatResponse:
    repo = CanonicalContentRepository(db)
    context = await _agent_context_for_user(user, db)
    search = UnitSearchService(repo)
    requirements = PathRequirementService(repo)
    service = AgentChatService(search, requirements)
    return await service.chat(
        body,
        allowed_course_ids=context.allowed_course_ids,
        is_reviewer=False,
    )


@agent_router.post("/search-units", response_model=UnitSearchResponse)
async def agent_search_units(
    body: UnitSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UnitSearchResponse:
    context = await _agent_context_for_user(user, db)
    return await UnitSearchService(CanonicalContentRepository(db)).search(
        body,
        allowed_course_ids=context.allowed_course_ids,
    )


@agent_router.post("/path-requirements", response_model=PathRequirementsResponse)
async def agent_path_requirements(
    body: PathRequirementsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> PathRequirementsResponse:
    context = await _agent_context_for_user(user, db)
    return await PathRequirementService(CanonicalContentRepository(db)).get_requirements(
        body,
        allowed_course_ids=context.allowed_course_ids,
    )


@agent_router.get("/unit-context/{canonical_unit_id}", response_model=UnitContextResponse)
async def agent_unit_context(
    canonical_unit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UnitContextResponse:
    context = await _agent_context_for_user(user, db)
    return await AgentUnitContextService(CanonicalContentRepository(db)).get_context(
        canonical_unit_id,
        allowed_course_ids=context.allowed_course_ids,
    )


@agent_router.get(
    "/transcript-snippets/{canonical_unit_id}",
    response_model=list[dict],
)
async def agent_transcript_snippets(
    canonical_unit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[dict]:
    context = await _agent_context_for_user(user, db)
    snippets = await AgentUnitContextService(CanonicalContentRepository(db)).get_transcript_snippets(
        canonical_unit_id,
        allowed_course_ids=context.allowed_course_ids,
        max_snippets=5,
    )
    return [
        {
            "start_sec": snippet.start_sec,
            "end_sec": snippet.end_sec,
            "text": snippet.text,
            "source": snippet.source,
        }
        for snippet in snippets
    ]


```

Modify `src/api/app.py` imports:

```python
from src.routers.agent import agent_router
```

Add router include near other routers:

```python
app.include_router(agent_router)
```

- [ ] **Step 4: Run route tests**

Run:

```bash
pytest tests/contract/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 5: Run focused suite**

Run:

```bash
pytest tests/test_agent_schema_contract.py tests/services/test_agent_query_normalizer.py tests/services/test_agent_context_service.py tests/services/test_agent_navigation_service.py tests/services/test_agent_search_service.py tests/services/test_agent_requirement_service.py tests/services/test_agent_unit_context_service.py tests/services/test_agent_chat_service.py tests/contract/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/routers/agent.py src/api/app.py tests/contract/test_agent_routes.py
git commit -m "feat: expose path agent api routes"
```

---

### Task 11: Replan And Assessment Action Endpoints

**Files:**
- Modify: `src/schemas/agent.py`
- Create: `src/services/agent_action_service.py`
- Modify: `src/routers/agent.py`
- Test: `tests/services/test_agent_action_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/services/test_agent_action_service.py`:

```python
from types import SimpleNamespace

import pytest

from src.services.agent_action_service import (
    default_phase_for_intent,
    start_assessment_not_implemented,
    validate_replan_request,
)


def test_default_phase_for_self_report_skip():
    assert default_phase_for_intent("assess_knowledge", "self_report_skip") == "skip_verification"


def test_default_phase_for_review():
    assert default_phase_for_intent("summarize_progress", "stale_mastery") == "review"


@pytest.mark.asyncio
async def test_replan_validation_rejects_missing_evidence():
    result = await validate_replan_request(
        SimpleNamespace(assessment_session_id=None, source_canonical_unit_ids=[]),
        user_id="user-1",
    )

    assert result.accepted is False
    assert result.rejected_reason == "missing_evidence"


def test_start_assessment_stub_is_not_accepted_until_wired():
    result = start_assessment_not_implemented()

    assert result.accepted is False
    assert result.rejected_reason == "not_implemented"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/services/test_agent_action_service.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement action service**

Create `src/services/agent_action_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


def default_phase_for_intent(intent: str, reason: str | None = None) -> str:
    if reason == "self_report_skip":
        return "skip_verification"
    if reason == "stale_mastery":
        return "review"
    if reason == "bridge_gap":
        return "bridge_check"
    if reason == "end_of_unit":
        return "final_quiz"
    if intent == "assess_knowledge":
        return "placement"
    return "review"


@dataclass(slots=True)
class ReplanValidationResult:
    accepted: bool
    rejected_reason: str | None = None


def start_assessment_not_implemented() -> ReplanValidationResult:
    return ReplanValidationResult(accepted=False, rejected_reason="not_implemented")


async def validate_replan_request(request, user_id: str) -> ReplanValidationResult:
    assessment_session_id = getattr(request, "assessment_session_id", None)
    source_unit_ids = getattr(request, "source_canonical_unit_ids", [])
    if not assessment_session_id and not source_unit_ids:
        return ReplanValidationResult(accepted=False, rejected_reason="missing_evidence")
    return ReplanValidationResult(accepted=True)
```

- [ ] **Step 4: Wire action endpoints**

Modify `src/routers/agent.py` imports:

```python
from src.schemas.agent import (
    AgentActionResponse,
    RequestReplanActionRequest,
    StartAssessmentActionRequest,
)
from src.services.agent_action_service import start_assessment_not_implemented, validate_replan_request
```

Add endpoints:

```python
@agent_router.post("/actions/start-assessment", response_model=AgentActionResponse)
async def agent_start_assessment(
    body: StartAssessmentActionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentActionResponse:
    result = start_assessment_not_implemented()
    return AgentActionResponse(
        accepted=result.accepted,
        rejectedReason=result.rejected_reason,
        dryRun=True,
        impact=None,
    )


@agent_router.post("/actions/request-replan", response_model=AgentActionResponse)
async def agent_request_replan(
    body: RequestReplanActionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AgentActionResponse:
    validation = await validate_replan_request(body, user_id=str(user.id))
    return AgentActionResponse(
        accepted=validation.accepted,
        rejectedReason=validation.rejected_reason,
        dryRun=body.dry_run,
        impact={"mode": "dry_run_only"} if validation.accepted and body.dry_run else None,
    )
```

Append to `tests/contract/test_agent_routes.py`:

```python
async def test_agent_action_endpoints_exist():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/agent/actions/request-replan",
            json={
                "assessmentSessionId": "session-a",
                "sourceCanonicalUnitIds": ["unit-a"],
                "reason": "assessment_completed",
                "dryRun": True,
            },
        )

    assert response.status_code == 200
    assert response.json()["accepted"] is True


async def test_start_assessment_action_is_disabled_until_wired():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/agent/actions/start-assessment",
            json={
                "canonicalUnitIds": ["unit-a"],
                "phase": "skip_verification",
                "reason": "self_report_skip",
            },
        )

    assert response.status_code == 200
    assert response.json()["accepted"] is False
    assert response.json()["rejectedReason"] == "not_implemented"
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/services/test_agent_action_service.py tests/contract/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/schemas/agent.py src/services/agent_action_service.py src/routers/agent.py tests/services/test_agent_action_service.py tests/contract/test_agent_routes.py
git commit -m "feat: add agent action validation stubs"
```

---

### Task 12: Documentation And Final Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-04-29-path-agent-rag-plan.md`
- Modify: `docs/superpowers/plans/2026-04-29-path-agent-rag-implementation.md`

- [ ] **Step 1: Add implementation status note to design plan**

Append this section to `docs/superpowers/plans/2026-04-29-path-agent-rag-plan.md`:

```markdown
## 17. Implementation Plan Link

Implementation tasks are tracked in `docs/superpowers/plans/2026-04-29-path-agent-rag-implementation.md`.
```

- [ ] **Step 2: Run backend focused tests**

Run:

```bash
pytest tests/test_agent_schema_contract.py tests/repositories/test_canonical_content_repo.py tests/services/test_agent_query_normalizer.py tests/services/test_agent_context_service.py tests/services/test_agent_navigation_service.py tests/services/test_agent_search_service.py tests/services/test_agent_requirement_service.py tests/services/test_agent_unit_context_service.py tests/services/test_agent_chat_service.py tests/services/test_agent_action_service.py tests/contract/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 3: Run existing adjacent tests**

Run:

```bash
pytest tests/repositories/test_canonical_content_repo.py tests/services/test_recommendation_engine_canonical_cutover.py tests/contract/test_canonical_content_routes.py -q
```

Expected: PASS.

- [ ] **Step 4: Optional frontend type-check**

Run:

```bash
npm run type-check
```

Expected: PASS or only documented unrelated existing failures. If unrelated failures occur, record exact file/error in the final response and do not modify unrelated files.

- [ ] **Step 5: Commit final docs**

```bash
git add docs/superpowers/plans/2026-04-29-path-agent-rag-plan.md docs/superpowers/plans/2026-04-29-path-agent-rag-implementation.md
git commit -m "docs: link path agent implementation plan"
```

---

## Self-Review

Spec coverage:

- Chat/orchestration endpoint: Task 9 and Task 10.
- Trace exposure and full-trace restriction: Task 1 and Task 9.
- User/path scope context: Task 3 and Task 10.
- Unit-centered search with query normalization: Task 2, Task 4, Task 6.
- Runtime navigation data: Task 4, Task 5, Task 6.
- Unit context and transcript snippets: Task 1, Task 4, Task 8, Task 10.
- Path requirements/prerequisite graph with content/KP policy and mastery overlay: Task 7.
- Assessment/replan action guardrails: Task 1, Task 9, Task 11.
- Public API contracts: Task 10.
- Verification and docs handoff: Task 12.

Known V1 limits:

- Search implementation starts with deterministic LIKE-style matching plus content-policy filters and can be upgraded to PostgreSQL `tsvector`/BM25 ranking without changing API shape.
- Chat response is template-based in V1; LLM wording can be added behind `AgentChatService` once tool traces are stable.
- Replan mutation is intentionally not implemented; Task 11 exposes backend-mediated validation and dry-run action contracts only.
