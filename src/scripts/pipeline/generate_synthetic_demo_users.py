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
from typing import Any, Literal

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
DATASET_ALIASES = {
    "demo": DEMO_DATASET,
    "cohort": COHORT_DATASET,
    "all": "all",
}
DEMO_PASSWORD = "DemoPass123!"
DEMO_PASSWORD_HASH = "$2b$12$2VA.mexLhoY.6Xtrv1520OhlOkcefL/cFeWWTkL7gga4pkFALNtBi"
DEMO_NOW = datetime(2026, 4, 24, 9, 0, tzinfo=UTC)
DEFAULT_OUTPUT_DIR = Path("data/synthetic")
SCENARIO_FILES = {
    DEMO_DATASET: DEFAULT_OUTPUT_DIR / DEMO_DATASET / "scenarios.json",
    COHORT_DATASET: DEFAULT_OUTPUT_DIR / COHORT_DATASET / "scenarios.json",
}
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "a20-app-049/synthetic-demo-users/v1")

ProficiencyBand = Literal["beginner", "developing", "proficient", "advanced"]
ALLOWED_PROFICIENCY_BANDS = {"beginner", "developing", "proficient", "advanced"}


@dataclass(frozen=True)
class SyntheticSessionSpec:
    phase: str
    answer_pattern: tuple[str, ...]
    item_count: int
    completed: bool = True
    response_time_ms: int | None = None


@dataclass(frozen=True)
class SyntheticUserSpec:
    dataset: str
    synthetic_case: str
    email: str
    full_name: str
    proficiency_band: ProficiencyBand
    course_scope: tuple[str, ...]
    is_demo_account: bool
    is_onboarded: bool
    mastery_profile: dict[str, Any]
    learning_state: dict[str, Any]
    sessions: tuple[SyntheticSessionSpec, ...]

    def to_metadata(self) -> dict[str, Any]:
        return {
            "is_synthetic": True,
            "synthetic_dataset": self.dataset,
            "synthetic_case": self.synthetic_case,
            "proficiency_band": self.proficiency_band,
            "course_scope": list(self.course_scope),
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


def build_user_specs(dataset: str = "all") -> list[SyntheticUserSpec]:
    normalized_dataset = DATASET_ALIASES.get(dataset, dataset)
    if normalized_dataset == DEMO_DATASET:
        return load_user_specs(SCENARIO_FILES[DEMO_DATASET])
    if normalized_dataset == COHORT_DATASET:
        return load_user_specs(SCENARIO_FILES[COHORT_DATASET])
    if normalized_dataset == "all":
        return load_user_specs(SCENARIO_FILES[DEMO_DATASET]) + load_user_specs(
            SCENARIO_FILES[COHORT_DATASET]
        )
    raise ValueError(f"Unsupported synthetic dataset: {dataset}")


def load_user_specs(path: Path) -> list[SyntheticUserSpec]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    dataset = raw["dataset"]
    specs: list[SyntheticUserSpec] = []
    for row in raw["users"]:
        spec = SyntheticUserSpec(
            dataset=dataset,
            synthetic_case=row["synthetic_case"],
            email=row["email"],
            full_name=row["full_name"],
            proficiency_band=row["proficiency_band"],
            course_scope=tuple(row.get("course_scope", [])),
            is_demo_account=bool(row["is_demo_account"]),
            is_onboarded=bool(row["is_onboarded"]),
            mastery_profile=dict(row.get("mastery_profile", {})),
            learning_state=dict(row.get("learning_state", {})),
            sessions=tuple(
                SyntheticSessionSpec(
                    phase=session_row["phase"],
                    answer_pattern=tuple(session_row.get("answer_pattern", [])),
                    item_count=int(session_row.get("item_count", 0)),
                    completed=bool(session_row.get("completed", True)),
                    response_time_ms=session_row.get("response_time_ms"),
                )
                for session_row in row.get("sessions", [])
            ),
        )
        _validate_spec(spec)
        specs.append(spec)
    return specs


def _validate_spec(spec: SyntheticUserSpec) -> None:
    if not spec.email.endswith("@vinuni.edu.vn"):
        raise ValueError(f"Synthetic user must use @vinuni.edu.vn email: {spec.email}")
    if spec.proficiency_band not in ALLOWED_PROFICIENCY_BANDS:
        raise ValueError(f"Unsupported proficiency band for {spec.email}: {spec.proficiency_band}")
    if not spec.is_onboarded:
        return
    for key in ("theta_mu", "theta_sigma", "mastery_mean_cached"):
        if key not in spec.mastery_profile:
            raise ValueError(f"{spec.email} missing mastery_profile.{key}")
    for session in spec.sessions:
        if session.item_count != len(session.answer_pattern):
            raise ValueError(
                f"{spec.email} session {session.phase} item_count does not match answer_pattern"
            )
        if session.response_time_ms is None:
            raise ValueError(f"{spec.email} session {session.phase} missing response_time_ms")
        unsupported = set(session.answer_pattern) - {"correct", "wrong"}
        if unsupported:
            raise ValueError(
                f"{spec.email} session {session.phase} has unsupported answers: {sorted(unsupported)}"
            )


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


def _select_courses(catalog: SyntheticCatalog, course_scope: tuple[str, ...]) -> list[CourseRef]:
    if not course_scope:
        return []
    scope_values = {value.lower() for value in course_scope}
    if "all" in scope_values:
        return list(catalog.courses)
    matched = [
        course
        for course in catalog.courses
        if any(scope_value in course.slug.lower() for scope_value in scope_values)
    ]
    return matched or list(catalog.courses[:1])


def _select_units(
    catalog: SyntheticCatalog,
    selected_courses: list[CourseRef],
    spec: SyntheticUserSpec,
) -> list[UnitRef]:
    selected_course_ids = {course.id for course in selected_courses}
    units = [unit for unit in catalog.units if unit.course_id in selected_course_ids]
    return units[: int(spec.learning_state.get("unit_count", 5))]


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

        progress_strategy = spec.learning_state.get("progress_strategy", "completed")
        if progress_strategy == "first_only" and index > 0:
            status = LearningProgressStatus.not_started.value
            completed_at = None
        elif progress_strategy == "abandon_video" and index == 0:
            status = LearningProgressStatus.in_progress.value
            completed_at = None
            last_position_seconds = float(spec.learning_state.get("video_progress_s", 522.0))
            last_opened_at = _parse_scenario_time(spec.learning_state["last_activity"])
        elif progress_strategy == "abandon_quiz" and index == 0:
            status = LearningProgressStatus.in_progress.value
            completed_at = None
            last_position_seconds = float(spec.learning_state.get("video_progress_s", 980.0))
            last_opened_at = _parse_scenario_time(spec.learning_state["last_activity"])
        elif spec.learning_state.get("last_activity"):
            last_opened_at = _parse_scenario_time(spec.learning_state["last_activity"])

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
    theta_mu = float(spec.mastery_profile["theta_mu"])
    theta_sigma = float(spec.mastery_profile["theta_sigma"])
    mastery = float(spec.mastery_profile["mastery_mean_cached"])
    n_items_base = int(spec.mastery_profile.get("n_items_observed_base", 3))
    updated_at = _parse_scenario_time(spec.learning_state.get("last_activity"))
    for index, kp_id in enumerate(kp_ids):
        rows["learner_mastery_kp"].append(
            {
                "id": _stable_uuid("mastery", f"{spec.email}:{kp_id}"),
                "user_id": user_id,
                "kp_id": kp_id,
                "theta_mu": theta_mu - (0.03 * (index % 3)),
                "theta_sigma": theta_sigma,
                "mastery_mean_cached": mastery,
                "n_items_observed": n_items_base + (index % 4),
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
    sequence_global = 1
    for phase_index, session_spec in enumerate(spec.sessions):
        phase = session_spec.phase
        items = _select_items(catalog, units, phase)
        if not items:
            continue
        items = items[: session_spec.item_count]
        completed_at = (
            created_at + timedelta(days=phase_index, hours=2)
            if session_spec.completed
            else None
        )

        session_id = _stable_uuid("session", f"{spec.email}:{phase}")
        session_ids[phase] = session_id
        correct_flags = [answer == "correct" for answer in session_spec.answer_pattern[: len(items)]]
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
                    "response_time_ms": int(session_spec.response_time_ms or 0) + (item_index * 1000),
                    "changed_answer": spec.proficiency_band == "beginner" and not is_correct,
                    "hint_used": spec.proficiency_band in {"beginner", "developing"} and not is_correct,
                    "explanation_viewed": not is_correct,
                    "timestamp": created_at + timedelta(days=phase_index, hours=1, minutes=item_index),
                }
            )
            sequence_global += 1

    return session_ids


def _select_items(catalog: SyntheticCatalog, units: list[UnitRef], phase: str) -> list[ItemRef]:
    unit_ids = {unit.canonical_unit_id for unit in units}
    return [
        item
        for item in catalog.items
        if item.unit_id in unit_ids and phase in item.phases
    ]


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
            "action": _action_for_spec(spec, index),
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
                "reason_code": _action_for_spec(spec, index),
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


def _action_for_spec(spec: SyntheticUserSpec, rank: int) -> str:
    planner_action = spec.learning_state.get("planner_action")
    if planner_action == "skip" and rank <= 2:
        return "skip"
    if planner_action == "quick_review":
        return "quick_review"
    if planner_action == "deep_practice":
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
    last_activity = _parse_scenario_time(spec.learning_state.get("last_activity"))
    current_stage = spec.learning_state.get("current_stage", "between_units")
    current_progress: dict[str, Any] = {
        "synthetic_case": spec.synthetic_case,
        "proficiency_band": spec.proficiency_band,
    }

    if spec.learning_state.get("progress_strategy") == "abandon_video":
        current_progress.update(
            {
                "video_progress_s": spec.learning_state.get("video_progress_s", 522),
                "video_finished": False,
            }
        )
    elif spec.learning_state.get("progress_strategy") == "abandon_quiz":
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
                "items_remaining": [
                    f"remaining-{index}"
                    for index in range(
                        1, int(spec.learning_state.get("items_remaining_count", 3)) + 1
                    )
                ],
            }
        )
    elif spec.learning_state.get("resume_expected"):
        current_progress.update({"resume_expected": spec.learning_state["resume_expected"]})

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


def _parse_scenario_time(value: str | None) -> datetime:
    if not value:
        return DEMO_NOW - timedelta(minutes=30)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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
    *,
    specs: list[SyntheticUserSpec] | None = None,
) -> dict[str, dict[str, int]]:
    split = split_rows_by_dataset(rows, specs=specs)
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
    dataset: str = "all",
) -> dict[str, Any]:
    async with async_session() as session:
        specs = build_user_specs(dataset)
        catalog = await load_catalog(session)
        rows = build_synthetic_rows(catalog, specs=specs)
        jsonl_counts = write_jsonl_snapshots(rows, output_dir, specs=specs) if write_jsonl else None
        import_counts = None
        if import_db:
            import_counts = await reset_and_import_synthetic_rows(session, rows, specs=specs)
            await session.commit()
        return {
            "demo_now": _iso(DEMO_NOW),
            "dataset": DATASET_ALIASES.get(dataset, dataset),
            "users": len(specs),
            "jsonl_counts": jsonl_counts,
            "import_counts": import_counts,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        choices=("demo", "cohort", "all", DEMO_DATASET, COHORT_DATASET),
        default="all",
        help="Dataset to generate/reset. Use 'demo' for only the 9 login accounts.",
    )
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
            dataset=args.dataset,
        )
    )
    print(json.dumps(_json_safe(result), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
