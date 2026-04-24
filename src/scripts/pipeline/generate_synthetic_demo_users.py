"""Generate deterministic synthetic demo learners.

The dataset is deliberately scripted, not random. Re-running the importer
resets the known synthetic accounts to the same baseline, which keeps live
demos reproducible while still allowing demo users to be clicked through.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Literal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session
from src.models.canonical import ItemKPMap, ItemPhaseMap, QuestionBankItem, UnitKPMap
from src.models.course import Course, LearningProgressRecord, LearningProgressStatus, LearningUnit
from src.models.learning import (
    GoalPreference,
    Interaction,
    LearnerMasteryKP,
    PlanHistory,
    PlannerSessionState,
    RationaleLog,
    SelectedAnswer,
    Session,
    SessionType,
    WaivedUnit,
)
from src.models.user import PreferredMethod, User

DEMO_DATASET = "demo_accounts_v1"
COHORT_DATASET = "cohort_30_v1"
DEMO_PASSWORD = "DemoPass123!"
DEMO_PASSWORD_HASH = "$2b$12$2VA.mexLhoY.6Xtrv1520OhlOkcefL/cFeWWTkL7gga4pkFALNtBi"
DEMO_NOW = datetime(2026, 4, 24, 9, 0, tzinfo=UTC)
DEFAULT_OUTPUT_DIR = Path("data/synthetic")
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "a20-app-049/synthetic-demo-users/v1")

ProficiencyBand = Literal["beginner", "developing", "proficient", "advanced"]

PROFICIENCY_MASTERY: dict[ProficiencyBand, tuple[float, float, float]] = {
    "beginner": (-0.85, 1.05, 0.30),
    "developing": (-0.20, 0.85, 0.45),
    "proficient": (0.75, 0.55, 0.72),
    "advanced": (1.35, 0.40, 0.86),
}
CORRECTNESS_PATTERNS: dict[ProficiencyBand, tuple[bool, ...]] = {
    "beginner": (False, False, True, False, False, True),
    "developing": (True, False, True, False, True, False),
    "proficient": (True, True, False, True, True, False),
    "advanced": (True, True, True, True, False, True),
}
RESPONSE_TIME_MS: dict[ProficiencyBand, int] = {
    "beginner": 62000,
    "developing": 47000,
    "proficient": 32000,
    "advanced": 21000,
}


@dataclass(frozen=True)
class SyntheticUserSpec:
    dataset: str
    synthetic_case: str
    email: str
    full_name: str
    proficiency_band: ProficiencyBand
    course_scope: str
    is_demo_account: bool
    is_onboarded: bool = True

    def to_metadata(self) -> dict[str, Any]:
        return {
            "is_synthetic": True,
            "synthetic_dataset": self.dataset,
            "synthetic_case": self.synthetic_case,
            "proficiency_band": self.proficiency_band,
            "course_scope": self.course_scope,
            "is_demo_account": self.is_demo_account,
            "resettable": True,
        }


@dataclass(frozen=True)
class CourseRef:
    id: uuid.UUID
    slug: str
    canonical_course_id: str | None


@dataclass(frozen=True)
class UnitRef:
    id: uuid.UUID
    course_id: uuid.UUID
    section_id: uuid.UUID | None
    canonical_unit_id: str
    title: str
    sort_order: int


@dataclass(frozen=True)
class ItemRef:
    item_id: str
    unit_id: str
    answer_index: int
    choice_count: int
    phases: tuple[str, ...]
    kp_ids: tuple[str, ...]


@dataclass(frozen=True)
class SyntheticCatalog:
    courses: tuple[CourseRef, ...]
    units: tuple[UnitRef, ...]
    items: tuple[ItemRef, ...]
    unit_kp_ids: dict[str, tuple[str, ...]]


def _stable_uuid(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}")


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _metadata_json(spec: SyntheticUserSpec) -> str:
    return json.dumps(spec.to_metadata(), ensure_ascii=True, sort_keys=True)


def build_user_specs() -> list[SyntheticUserSpec]:
    return _build_demo_specs() + _build_cohort_specs()


def _build_demo_specs() -> list[SyntheticUserSpec]:
    return [
        SyntheticUserSpec(
            dataset=DEMO_DATASET,
            synthetic_case="first_login",
            email="demo.firstlogin@vinuni.edu.vn",
            full_name="Demo First Login",
            proficiency_band="beginner",
            course_scope="none",
            is_demo_account=True,
            is_onboarded=False,
        ),
        SyntheticUserSpec(
            dataset=DEMO_DATASET,
            synthetic_case="full_2_courses",
            email="demo.full@vinuni.edu.vn",
            full_name="Demo Full Two Courses",
            proficiency_band="proficient",
            course_scope="all",
            is_demo_account=True,
        ),
        SyntheticUserSpec(
            dataset=DEMO_DATASET,
            synthetic_case="cs231_only",
            email="demo.cs231@vinuni.edu.vn",
            full_name="Demo CS231 Only",
            proficiency_band="proficient",
            course_scope="cs231n",
            is_demo_account=True,
        ),
        SyntheticUserSpec(
            dataset=DEMO_DATASET,
            synthetic_case="cs224n_only",
            email="demo.cs224n@vinuni.edu.vn",
            full_name="Demo CS224N Only",
            proficiency_band="developing",
            course_scope="cs224n",
            is_demo_account=True,
        ),
        SyntheticUserSpec(
            dataset=DEMO_DATASET,
            synthetic_case="strong_skipper",
            email="demo.skipper@vinuni.edu.vn",
            full_name="Demo Strong Skipper",
            proficiency_band="advanced",
            course_scope="all",
            is_demo_account=True,
        ),
        SyntheticUserSpec(
            dataset=DEMO_DATASET,
            synthetic_case="review_heavy",
            email="demo.reviewer@vinuni.edu.vn",
            full_name="Demo Review Heavy",
            proficiency_band="proficient",
            course_scope="all",
            is_demo_account=True,
        ),
        SyntheticUserSpec(
            dataset=DEMO_DATASET,
            synthetic_case="weak_beginner",
            email="demo.beginner@vinuni.edu.vn",
            full_name="Demo Weak Beginner",
            proficiency_band="beginner",
            course_scope="all",
            is_demo_account=True,
        ),
        SyntheticUserSpec(
            dataset=DEMO_DATASET,
            synthetic_case="abandon_mid_video",
            email="demo.abandon.video@vinuni.edu.vn",
            full_name="Demo Abandon Video",
            proficiency_band="developing",
            course_scope="all",
            is_demo_account=True,
        ),
        SyntheticUserSpec(
            dataset=DEMO_DATASET,
            synthetic_case="abandon_mid_quiz_long_return",
            email="demo.returner@vinuni.edu.vn",
            full_name="Demo Long Returner",
            proficiency_band="proficient",
            course_scope="all",
            is_demo_account=True,
        ),
    ]


def _build_cohort_specs() -> list[SyntheticUserSpec]:
    specs: list[SyntheticUserSpec] = []

    def add_group(
        case: str,
        prefix: str,
        course_scope: str,
        bands: Iterable[ProficiencyBand],
    ) -> None:
        for index, band in enumerate(bands, start=1):
            specs.append(
                SyntheticUserSpec(
                    dataset=COHORT_DATASET,
                    synthetic_case=case,
                    email=f"synthetic.{prefix}.{index:02d}@vinuni.edu.vn",
                    full_name=f"Synthetic {case.replace('_', ' ').title()} {index:02d}",
                    proficiency_band=band,
                    course_scope=course_scope,
                    is_demo_account=False,
                )
            )

    add_group(
        "full_2_courses",
        "full",
        "all",
        ("developing", "proficient", "proficient", "proficient", "advanced", "advanced"),
    )
    add_group(
        "cs231_only",
        "cs231",
        "cs231n",
        ("developing", "developing", "proficient", "proficient", "advanced"),
    )
    add_group("cs224n_only", "cs224n", "cs224n", ("developing", "proficient", "proficient"))
    add_group("strong_skipper", "skipper", "all", ("advanced", "advanced", "advanced", "advanced"))
    add_group("review_heavy", "reviewer", "all", ("developing", "proficient", "proficient"))
    add_group("weak_beginner", "beginner", "all", ("beginner", "beginner", "beginner"))
    add_group("abandon_mid_video", "abandon-video", "all", ("beginner", "developing"))
    add_group("abandon_mid_quiz", "abandon-quiz", "all", ("beginner", "developing"))
    add_group("long_returner_review", "long-returner", "all", ("proficient",))
    add_group("very_long_returner_placement_lite", "very-long-returner", "all", ("beginner",))
    return specs


async def load_catalog(session: AsyncSession) -> SyntheticCatalog:
    course_rows = (
        await session.execute(select(Course).order_by(Course.slug))
    ).scalars().all()
    unit_rows = (
        await session.execute(
            select(LearningUnit).order_by(
                LearningUnit.course_id,
                LearningUnit.sort_order,
                LearningUnit.slug,
            )
        )
    ).scalars().all()
    question_rows = (
        await session.execute(
            select(QuestionBankItem).order_by(
                QuestionBankItem.unit_id,
                QuestionBankItem.item_id,
            )
        )
    ).scalars().all()
    phase_rows = (
        await session.execute(
            select(ItemPhaseMap).order_by(ItemPhaseMap.item_id, ItemPhaseMap.phase)
        )
    ).scalars().all()
    item_kp_rows = (
        await session.execute(select(ItemKPMap).order_by(ItemKPMap.item_id, ItemKPMap.kp_id))
    ).scalars().all()
    unit_kp_rows = (
        await session.execute(select(UnitKPMap).order_by(UnitKPMap.unit_id, UnitKPMap.kp_id))
    ).scalars().all()

    phases_by_item: dict[str, list[str]] = defaultdict(list)
    for row in phase_rows:
        phases_by_item[row.item_id].append(row.phase)

    kp_by_item: dict[str, list[str]] = defaultdict(list)
    for row in item_kp_rows:
        kp_by_item[row.item_id].append(row.kp_id)

    kp_by_unit: dict[str, list[str]] = defaultdict(list)
    for row in unit_kp_rows:
        kp_by_unit[row.unit_id].append(row.kp_id)

    return SyntheticCatalog(
        courses=tuple(
            CourseRef(
                id=row.id,
                slug=row.slug,
                canonical_course_id=row.canonical_course_id,
            )
            for row in course_rows
        ),
        units=tuple(
            UnitRef(
                id=row.id,
                course_id=row.course_id,
                section_id=row.section_id,
                canonical_unit_id=row.canonical_unit_id or str(row.id),
                title=row.title,
                sort_order=row.sort_order,
            )
            for row in unit_rows
            if row.canonical_unit_id
        ),
        items=tuple(
            ItemRef(
                item_id=row.item_id,
                unit_id=row.unit_id,
                answer_index=row.answer_index,
                choice_count=len(row.choices or []),
                phases=tuple(phases_by_item.get(row.item_id, [])),
                kp_ids=tuple(kp_by_item.get(row.item_id, []) or [row.primary_kp_id]),
            )
            for row in question_rows
        ),
        unit_kp_ids={
            unit_id: tuple(kp_ids)
            for unit_id, kp_ids in sorted(kp_by_unit.items())
        },
    )


def build_synthetic_rows(
    catalog: SyntheticCatalog,
    *,
    specs: list[SyntheticUserSpec] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    specs = specs or build_user_specs()
    _validate_catalog(catalog)

    rows: dict[str, list[dict[str, Any]]] = {
        "users": [],
        "goal_preferences": [],
        "sessions": [],
        "interactions": [],
        "learner_mastery_kp": [],
        "learning_progress_records": [],
        "waived_units": [],
        "plan_history": [],
        "rationale_log": [],
        "planner_session_state": [],
    }

    for spec_index, spec in enumerate(specs, start=1):
        _append_user_rows(rows, catalog, spec, spec_index)

    return rows


def _validate_catalog(catalog: SyntheticCatalog) -> None:
    if not catalog.courses:
        raise ValueError("Synthetic demo users require imported product courses.")
    if not catalog.units:
        raise ValueError("Synthetic demo users require imported learning units.")
    if not catalog.items:
        raise ValueError("Synthetic demo users require imported question_bank items.")


def _append_user_rows(
    rows: dict[str, list[dict[str, Any]]],
    catalog: SyntheticCatalog,
    spec: SyntheticUserSpec,
    spec_index: int,
) -> None:
    user_id = _stable_uuid("user", spec.email)
    created_at = DEMO_NOW - timedelta(days=45 - min(spec_index, 30))
    selected_courses = _select_courses(catalog, spec.course_scope)
    selected_units = _select_units(catalog, selected_courses, spec)
    active_unit = selected_units[0] if selected_units else None

    rows["users"].append(
        {
            "id": user_id,
            "email": spec.email,
            "full_name": spec.full_name,
            "hashed_password": DEMO_PASSWORD_HASH,
            "available_hours_per_week": 8.0 if spec.is_onboarded else None,
            "target_deadline": None,
            "preferred_method": PreferredMethod.video.value if spec.is_onboarded else None,
            "is_onboarded": spec.is_onboarded,
            "created_at": created_at,
        }
    )

    if not spec.is_onboarded:
        return

    rows["goal_preferences"].append(
        {
            "id": _stable_uuid("goal", spec.email),
            "user_id": user_id,
            "goal_weights_json": {
                "available_hours_per_week": 8.0,
                "preferred_method": "video",
                "synthetic_proficiency_band": spec.proficiency_band,
            },
            "selected_course_ids": [str(course.id) for course in selected_courses],
            "goal_embedding": None,
            "goal_embedding_version": None,
            "derived_from_course_set_hash": f"synthetic:{spec.dataset}:{spec.course_scope}",
            "notes": _metadata_json(spec),
            "created_at": created_at,
            "updated_at": created_at,
        }
    )

    if not active_unit:
        return

    _append_progress_rows(rows, spec, user_id, selected_units, created_at)
    _append_mastery_rows(rows, catalog, spec, user_id, selected_units, created_at)
    session_ids = _append_session_and_interaction_rows(
        rows,
        catalog,
        spec,
        user_id,
        selected_units,
        created_at,
    )
    plan_id = _append_planner_rows(rows, spec, user_id, selected_units, selected_courses, created_at)
    _append_session_state(rows, spec, user_id, selected_units, session_ids, plan_id)


def _select_courses(catalog: SyntheticCatalog, course_scope: str) -> list[CourseRef]:
    if course_scope == "none":
        return []
    if course_scope == "all":
        return list(catalog.courses)
    matched = [course for course in catalog.courses if course_scope.lower() in course.slug.lower()]
    return matched or list(catalog.courses[:1])


def _select_units(
    catalog: SyntheticCatalog,
    selected_courses: list[CourseRef],
    spec: SyntheticUserSpec,
) -> list[UnitRef]:
    selected_course_ids = {course.id for course in selected_courses}
    units = [unit for unit in catalog.units if unit.course_id in selected_course_ids]
    limit_by_case = {
        "full_2_courses": 10,
        "cs231_only": 8,
        "cs224n_only": 6,
        "strong_skipper": 8,
        "review_heavy": 7,
        "weak_beginner": 4,
        "abandon_mid_video": 3,
        "abandon_mid_quiz": 3,
        "abandon_mid_quiz_long_return": 4,
        "long_returner_review": 5,
        "very_long_returner_placement_lite": 5,
    }
    return units[: limit_by_case.get(spec.synthetic_case, 5)]


def _append_progress_rows(
    rows: dict[str, list[dict[str, Any]]],
    spec: SyntheticUserSpec,
    user_id: uuid.UUID,
    units: list[UnitRef],
    created_at: datetime,
) -> None:
    for index, unit in enumerate(units):
        status = LearningProgressStatus.completed.value
        completed_at = created_at + timedelta(days=index, hours=1)
        last_position_seconds: float | None = None
        last_opened_at = completed_at

        if spec.synthetic_case == "weak_beginner" and index > 0:
            status = LearningProgressStatus.not_started.value
            completed_at = None
        elif spec.synthetic_case == "abandon_mid_video" and index == 0:
            status = LearningProgressStatus.in_progress.value
            completed_at = None
            last_position_seconds = 522.0
            last_opened_at = DEMO_NOW - timedelta(minutes=50)
        elif spec.synthetic_case in {"abandon_mid_quiz", "abandon_mid_quiz_long_return"} and index == 0:
            status = LearningProgressStatus.in_progress.value
            completed_at = None
            last_position_seconds = 980.0
            last_opened_at = DEMO_NOW - timedelta(days=1, hours=23)
        elif "returner" in spec.synthetic_case:
            last_opened_at = _last_activity_for_case(spec.synthetic_case)

        rows["learning_progress_records"].append(
            {
                "id": _stable_uuid("progress", f"{spec.email}:{unit.id}"),
                "user_id": user_id,
                "course_id": unit.course_id,
                "learning_unit_id": unit.id,
                "status": status,
                "last_position_seconds": last_position_seconds,
                "last_opened_at": last_opened_at,
                "completed_at": completed_at,
            }
        )


def _append_mastery_rows(
    rows: dict[str, list[dict[str, Any]]],
    catalog: SyntheticCatalog,
    spec: SyntheticUserSpec,
    user_id: uuid.UUID,
    units: list[UnitRef],
    created_at: datetime,
) -> None:
    kp_ids: list[str] = []
    for unit in units:
        kp_ids.extend(catalog.unit_kp_ids.get(unit.canonical_unit_id, ()))
    kp_ids = sorted(set(kp_ids))[:12]
    theta_mu, theta_sigma, mastery = PROFICIENCY_MASTERY[spec.proficiency_band]
    if spec.synthetic_case == "strong_skipper":
        theta_mu, theta_sigma, mastery = (1.6, 0.35, 0.91)
    if spec.synthetic_case == "weak_beginner":
        theta_mu, theta_sigma, mastery = (-1.05, 1.15, 0.24)

    updated_at = _last_activity_for_case(spec.synthetic_case)
    for index, kp_id in enumerate(kp_ids):
        rows["learner_mastery_kp"].append(
            {
                "id": _stable_uuid("mastery", f"{spec.email}:{kp_id}"),
                "user_id": user_id,
                "kp_id": kp_id,
                "theta_mu": theta_mu - (0.03 * (index % 3)),
                "theta_sigma": theta_sigma,
                "mastery_mean_cached": mastery,
                "n_items_observed": 3 + (index % 4),
                "updated_by": f"synthetic_fixture:{spec.dataset}:{spec.proficiency_band}",
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )


def _append_session_and_interaction_rows(
    rows: dict[str, list[dict[str, Any]]],
    catalog: SyntheticCatalog,
    spec: SyntheticUserSpec,
    user_id: uuid.UUID,
    units: list[UnitRef],
    created_at: datetime,
) -> dict[str, uuid.UUID]:
    session_ids: dict[str, uuid.UUID] = {}
    phases = _phases_for_case(spec.synthetic_case)
    sequence_global = 1
    for phase_index, phase in enumerate(phases):
        items = _select_items(catalog, units, phase)
        if not items:
            continue
        if spec.synthetic_case in {"abandon_mid_quiz", "abandon_mid_quiz_long_return"} and phase == "mini_quiz":
            items = items[:2]
            completed_at = None
        else:
            items = items[:4]
            completed_at = created_at + timedelta(days=phase_index, hours=2)

        session_id = _stable_uuid("session", f"{spec.email}:{phase}")
        session_ids[phase] = session_id
        correct_flags = _correctness_flags(spec.proficiency_band, len(items))
        rows["sessions"].append(
            {
                "id": session_id,
                "user_id": user_id,
                "session_type": SessionType.assessment.value,
                "topic_id": None,
                "module_id": None,
                "started_at": created_at + timedelta(days=phase_index, hours=1),
                "completed_at": completed_at,
                "total_questions": len(items),
                "correct_count": sum(1 for value in correct_flags if value),
                "score_percent": round(100 * sum(1 for value in correct_flags if value) / len(items), 2),
                "canonical_phase": phase,
                "canonical_unit_id": units[0].id,
                "canonical_section_id": units[0].section_id,
            }
        )

        for item_index, item in enumerate(items, start=1):
            is_correct = correct_flags[item_index - 1]
            selected_answer = _selected_answer(item, is_correct)
            rows["interactions"].append(
                {
                    "id": _stable_uuid("interaction", f"{spec.email}:{phase}:{item.item_id}"),
                    "user_id": user_id,
                    "session_id": session_id,
                    "question_id": None,
                    "canonical_item_id": item.item_id,
                    "sequence_position": item_index,
                    "global_sequence_position": sequence_global,
                    "selected_answer": selected_answer,
                    "is_correct": is_correct,
                    "response_time_ms": RESPONSE_TIME_MS[spec.proficiency_band] + (item_index * 1000),
                    "changed_answer": spec.proficiency_band == "beginner" and not is_correct,
                    "hint_used": spec.proficiency_band in {"beginner", "developing"} and not is_correct,
                    "explanation_viewed": not is_correct,
                    "timestamp": created_at + timedelta(days=phase_index, hours=1, minutes=item_index),
                }
            )
            sequence_global += 1

    return session_ids


def _phases_for_case(case: str) -> tuple[str, ...]:
    if case == "review_heavy" or case == "long_returner_review":
        return ("mini_quiz", "review")
    if case in {"abandon_mid_quiz", "abandon_mid_quiz_long_return"}:
        return ("mini_quiz",)
    if case == "very_long_returner_placement_lite":
        return ("placement",)
    return ("mini_quiz",)


def _select_items(catalog: SyntheticCatalog, units: list[UnitRef], phase: str) -> list[ItemRef]:
    unit_ids = {unit.canonical_unit_id for unit in units}
    return [
        item
        for item in catalog.items
        if item.unit_id in unit_ids and phase in item.phases
    ]


def _correctness_flags(band: ProficiencyBand, count: int) -> list[bool]:
    pattern = CORRECTNESS_PATTERNS[band]
    return [pattern[index % len(pattern)] for index in range(count)]


def _selected_answer(item: ItemRef, is_correct: bool) -> str:
    answer_index = item.answer_index if is_correct else (item.answer_index + 1) % max(item.choice_count, 4)
    answer_index = min(answer_index, 3)
    return (SelectedAnswer.A, SelectedAnswer.B, SelectedAnswer.C, SelectedAnswer.D)[answer_index].value


def _append_planner_rows(
    rows: dict[str, list[dict[str, Any]]],
    spec: SyntheticUserSpec,
    user_id: uuid.UUID,
    units: list[UnitRef],
    courses: list[CourseRef],
    created_at: datetime,
) -> uuid.UUID:
    plan_id = _stable_uuid("plan", spec.email)
    recommended_path = [
        {
            "learning_unit_id": str(unit.id),
            "title": unit.title,
            "rank": index,
            "action": _action_for_case(spec.synthetic_case, index),
            "synthetic_case": spec.synthetic_case,
        }
        for index, unit in enumerate(units[:6], start=1)
    ]
    rows["plan_history"].append(
        {
            "id": plan_id,
            "user_id": user_id,
            "parent_plan_id": None,
            "trigger": f"synthetic_{spec.synthetic_case}",
            "recommended_path_json": recommended_path,
            "goal_snapshot_json": {
                **spec.to_metadata(),
                "selected_course_ids": [str(course.id) for course in courses],
            },
            "weights_used_json": {
                "need": 0.45,
                "interest": 0.25,
                "unlock_gain": 0.20,
                "review": 0.10,
                "proficiency_band": spec.proficiency_band,
            },
            "created_at": created_at,
            "updated_at": created_at,
        }
    )
    for index, unit in enumerate(units[:4], start=1):
        rows["rationale_log"].append(
            {
                "id": _stable_uuid("rationale", f"{spec.email}:{unit.id}"),
                "plan_history_id": plan_id,
                "learning_unit_id": unit.id,
                "rank": index,
                "reason_code": _action_for_case(spec.synthetic_case, index),
                "term_breakdown_json": {
                    "need": round(0.9 - index * 0.06, 2),
                    "interest": 0.7,
                    "unlock_gain": 0.5 if spec.proficiency_band in {"proficient", "advanced"} else 0.25,
                    "difficulty_fit": spec.proficiency_band,
                },
                "rationale_text": f"Synthetic {spec.synthetic_case} plan row for {spec.proficiency_band} learner.",
                "created_at": created_at,
                "updated_at": created_at,
            }
        )
    return plan_id


def _action_for_case(case: str, rank: int) -> str:
    if case == "strong_skipper" and rank <= 2:
        return "skip"
    if case in {"review_heavy", "long_returner_review"}:
        return "quick_review"
    if case == "weak_beginner":
        return "deep_practice"
    return "learn"


def _append_session_state(
    rows: dict[str, list[dict[str, Any]]],
    spec: SyntheticUserSpec,
    user_id: uuid.UUID,
    units: list[UnitRef],
    session_ids: dict[str, uuid.UUID],
    plan_id: uuid.UUID,
) -> None:
    current_unit = units[0]
    last_activity = _last_activity_for_case(spec.synthetic_case)
    current_stage = "between_units"
    current_progress: dict[str, Any] = {
        "synthetic_case": spec.synthetic_case,
        "proficiency_band": spec.proficiency_band,
    }

    if spec.synthetic_case == "abandon_mid_video":
        current_stage = "watching"
        current_progress.update(
            {
                "video_progress_s": 522,
                "video_finished": False,
            }
        )
    elif spec.synthetic_case in {"abandon_mid_quiz", "abandon_mid_quiz_long_return"}:
        current_stage = "quiz_in_progress"
        quiz_id = session_ids.get("mini_quiz")
        answered_items = [
            row["canonical_item_id"]
            for row in rows["interactions"]
            if row["user_id"] == user_id and row["session_id"] == quiz_id
        ]
        current_progress.update(
            {
                "quiz_id": str(quiz_id) if quiz_id else None,
                "quiz_phase": "mini_quiz",
                "items_answered": answered_items,
                "items_remaining": [f"remaining-{index}" for index in range(1, 4)],
            }
        )
    elif "returner" in spec.synthetic_case:
        current_stage = "between_units"
        current_progress.update({"resume_expected": "review_or_placement_lite"})

    rows["planner_session_state"].append(
        {
            "id": _stable_uuid("planner-state", spec.email),
            "user_id": user_id,
            "session_id": "canonical-learning-path",
            "last_plan_history_id": plan_id,
            "bridge_chain_depth": 0,
            "consecutive_bridge_count": 0,
            "current_unit_id": current_unit.id,
            "current_stage": current_stage,
            "current_progress": current_progress,
            "last_activity": last_activity,
            "state_json": spec.to_metadata(),
            "created_at": last_activity,
            "updated_at": last_activity,
        }
    )

    if spec.synthetic_case == "strong_skipper":
        for unit in units[:2]:
            rows["waived_units"].append(
                {
                    "id": _stable_uuid("waive", f"{spec.email}:{unit.id}"),
                    "user_id": user_id,
                    "learning_unit_id": unit.id,
                    "evidence_items": [
                        {
                            "source": "synthetic_fixture",
                            "synthetic_case": spec.synthetic_case,
                            "proficiency_band": spec.proficiency_band,
                        }
                    ],
                    "mastery_lcb_at_waive": 0.84,
                    "skip_quiz_score": 90.0,
                    "created_at": last_activity,
                    "updated_at": last_activity,
                }
            )


def _last_activity_for_case(case: str) -> datetime:
    if case == "abandon_mid_video":
        return DEMO_NOW - timedelta(minutes=50)
    if case in {"abandon_mid_quiz", "abandon_mid_quiz_long_return"}:
        return DEMO_NOW - timedelta(days=1, hours=23)
    if case == "long_returner_review":
        return datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
    if case == "very_long_returner_placement_lite":
        return datetime(2026, 3, 10, 9, 0, tzinfo=UTC)
    return DEMO_NOW - timedelta(minutes=30)


def split_rows_by_dataset(
    rows: dict[str, list[dict[str, Any]]],
    specs: list[SyntheticUserSpec] | None = None,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    specs = specs or build_user_specs()
    dataset_by_user_id = {
        _stable_uuid("user", spec.email): spec.dataset
        for spec in specs
    }
    dataset_by_plan_id = {
        row["id"]: dataset_by_user_id[row["user_id"]]
        for row in rows.get("plan_history", [])
        if row.get("user_id") in dataset_by_user_id
    }
    result = {
        DEMO_DATASET: {table: [] for table in rows},
        COHORT_DATASET: {table: [] for table in rows},
    }
    for table, table_rows in rows.items():
        for row in table_rows:
            user_id = row.get("user_id") or row.get("id")
            dataset = dataset_by_user_id.get(user_id)
            if dataset is None and table == "rationale_log":
                dataset = dataset_by_plan_id.get(row.get("plan_history_id"))
            if dataset:
                result[dataset][table].append(row)
    return result


def write_jsonl_snapshots(
    rows: dict[str, list[dict[str, Any]]],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, dict[str, int]]:
    split = split_rows_by_dataset(rows)
    counts: dict[str, dict[str, int]] = {}
    for dataset, dataset_rows in split.items():
        dataset_dir = output_dir / dataset
        dataset_dir.mkdir(parents=True, exist_ok=True)
        counts[dataset] = {}
        for table, table_rows in dataset_rows.items():
            path = dataset_dir / f"{table}.jsonl"
            with path.open("w", encoding="utf-8") as handle:
                for row in table_rows:
                    handle.write(json.dumps(_json_safe(row), ensure_ascii=True, sort_keys=True))
                    handle.write("\n")
            counts[dataset][table] = len(table_rows)
        manifest = {
            "dataset": dataset,
            "generated_at": _iso(DEMO_NOW),
            "demo_now": _iso(DEMO_NOW),
            "counts": counts[dataset],
            "password_note": "Demo accounts use the shared password documented in WORKLOG, not stored in JSONL.",
        }
        (dataset_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return counts


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return _iso(value)
    return value


async def reset_and_import_synthetic_rows(
    session: AsyncSession,
    rows: dict[str, list[dict[str, Any]]],
    *,
    specs: list[SyntheticUserSpec] | None = None,
) -> dict[str, int]:
    specs = specs or build_user_specs()
    emails = [spec.email for spec in specs]
    await session.execute(delete(User).where(User.email.in_(emails)))
    await session.flush()

    model_order = [
        ("users", User),
        ("goal_preferences", GoalPreference),
        ("sessions", Session),
        ("interactions", Interaction),
        ("learner_mastery_kp", LearnerMasteryKP),
        ("learning_progress_records", LearningProgressRecord),
        ("waived_units", WaivedUnit),
        ("plan_history", PlanHistory),
        ("rationale_log", RationaleLog),
        ("planner_session_state", PlannerSessionState),
    ]
    counts: dict[str, int] = {}
    for table, model in model_order:
        objects = [model(**_db_row(table, row)) for row in rows[table]]
        session.add_all(objects)
        counts[table] = len(objects)
        await session.flush()
    return counts


def _db_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    next_row = dict(row)
    if table == "users" and next_row.get("preferred_method"):
        next_row["preferred_method"] = PreferredMethod(next_row["preferred_method"])
    if table == "sessions":
        next_row["session_type"] = SessionType(next_row["session_type"])
    if table == "interactions" and next_row.get("selected_answer"):
        next_row["selected_answer"] = SelectedAnswer(next_row["selected_answer"])
    if table == "learning_progress_records":
        next_row["status"] = LearningProgressStatus(next_row["status"])
    return next_row


async def generate_from_db(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    write_jsonl: bool = True,
    import_db: bool = False,
) -> dict[str, Any]:
    async with async_session() as session:
        catalog = await load_catalog(session)
        rows = build_synthetic_rows(catalog)
        jsonl_counts = write_jsonl_snapshots(rows, output_dir) if write_jsonl else None
        import_counts = None
        if import_db:
            import_counts = await reset_and_import_synthetic_rows(session, rows)
            await session.commit()
        return {
            "demo_now": _iso(DEMO_NOW),
            "users": len(build_user_specs()),
            "jsonl_counts": jsonl_counts,
            "import_counts": import_counts,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where deterministic JSONL snapshots are written.",
    )
    parser.add_argument(
        "--no-jsonl",
        action="store_true",
        help="Do not write JSONL snapshots.",
    )
    parser.add_argument(
        "--import-db",
        action="store_true",
        help="Reset and import the synthetic users into the active database.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(
        generate_from_db(
            output_dir=args.output_dir,
            write_jsonl=not args.no_jsonl,
            import_db=args.import_db,
        )
    )
    print(json.dumps(_json_safe(result), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
