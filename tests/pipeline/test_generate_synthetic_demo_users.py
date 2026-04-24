from src.services.auth_service import verify_password
from src.scripts.pipeline.generate_synthetic_demo_users import (
    COHORT_DATASET,
    DEMO_DATASET,
    DEMO_PASSWORD,
    DEMO_PASSWORD_HASH,
    CourseRef,
    ItemRef,
    SyntheticCatalog,
    UnitRef,
    build_synthetic_rows,
    build_user_specs,
    write_jsonl_snapshots,
)
import json
import uuid


def test_build_user_specs_separates_demo_accounts_from_cohort_users():
    specs = build_user_specs()

    demo_specs = [spec for spec in specs if spec.dataset == DEMO_DATASET]
    cohort_specs = [spec for spec in specs if spec.dataset == COHORT_DATASET]

    assert len(demo_specs) == 9
    assert len(cohort_specs) == 30
    assert {spec.email for spec in demo_specs}.isdisjoint({spec.email for spec in cohort_specs})


def test_build_user_specs_uses_vinuni_domain_and_expected_demo_accounts():
    specs = build_user_specs()

    assert all(spec.email.endswith("@vinuni.edu.vn") for spec in specs)
    assert [spec.email for spec in specs if spec.dataset == DEMO_DATASET] == [
        "demo.firstlogin@vinuni.edu.vn",
        "demo.full@vinuni.edu.vn",
        "demo.cs231@vinuni.edu.vn",
        "demo.cs224n@vinuni.edu.vn",
        "demo.skipper@vinuni.edu.vn",
        "demo.reviewer@vinuni.edu.vn",
        "demo.beginner@vinuni.edu.vn",
        "demo.abandon.video@vinuni.edu.vn",
        "demo.returner@vinuni.edu.vn",
    ]


def test_demo_password_hash_is_static_and_verifies_shared_password():
    assert DEMO_PASSWORD == "DemoPass123!"
    assert verify_password(DEMO_PASSWORD, DEMO_PASSWORD_HASH)


def test_cohort_has_diverse_proficiency_bands():
    cohort_specs = [spec for spec in build_user_specs() if spec.dataset == COHORT_DATASET]

    counts = {}
    for spec in cohort_specs:
        counts[spec.proficiency_band] = counts.get(spec.proficiency_band, 0) + 1

    assert counts == {
        "beginner": 6,
        "developing": 7,
        "proficient": 10,
        "advanced": 7,
    }


def test_build_user_specs_is_deterministic():
    first = [spec.to_metadata() for spec in build_user_specs()]
    second = [spec.to_metadata() for spec in build_user_specs()]

    assert first == second


def test_build_synthetic_rows_preserves_case_and_proficiency_metadata():
    rows = build_synthetic_rows(_fake_catalog())

    assert len(rows["users"]) == 39
    assert len(rows["goal_preferences"]) == 38
    assert len(rows["planner_session_state"]) == 38
    assert any("synthetic_fixture:demo_accounts_v1:advanced" in row["updated_by"] for row in rows["learner_mastery_kp"])
    assert any(row["state_json"]["synthetic_case"] == "abandon_mid_video" for row in rows["planner_session_state"])
    assert any(row["state_json"]["proficiency_band"] == "beginner" for row in rows["planner_session_state"])


def test_write_jsonl_snapshots_keeps_demo_and_cohort_directories_separate(tmp_path):
    rows = build_synthetic_rows(_fake_catalog())

    counts = write_jsonl_snapshots(rows, tmp_path)

    assert counts[DEMO_DATASET]["users"] == 9
    assert counts[COHORT_DATASET]["users"] == 30
    assert counts[DEMO_DATASET]["rationale_log"] > 0
    assert counts[COHORT_DATASET]["rationale_log"] > 0
    demo_manifest = json.loads((tmp_path / DEMO_DATASET / "manifest.json").read_text())
    cohort_manifest = json.loads((tmp_path / COHORT_DATASET / "manifest.json").read_text())
    assert demo_manifest["dataset"] == DEMO_DATASET
    assert cohort_manifest["dataset"] == COHORT_DATASET
    assert (tmp_path / DEMO_DATASET / "users.jsonl").exists()
    assert (tmp_path / COHORT_DATASET / "users.jsonl").exists()


def _fake_catalog() -> SyntheticCatalog:
    cs224n_course_id = uuid.uuid5(uuid.NAMESPACE_URL, "test-course-cs224n")
    cs231n_course_id = uuid.uuid5(uuid.NAMESPACE_URL, "test-course-cs231n")
    courses = (
        CourseRef(id=cs224n_course_id, slug="cs224n", canonical_course_id="CS224N"),
        CourseRef(id=cs231n_course_id, slug="cs231n", canonical_course_id="CS231N"),
    )
    units = []
    items = []
    unit_kp_ids = {}
    for course_index, course in enumerate(courses, start=1):
        for unit_index in range(1, 9):
            canonical_unit_id = f"{course.slug}_unit_{unit_index:02d}"
            unit_id = uuid.uuid5(uuid.NAMESPACE_URL, f"test-unit-{canonical_unit_id}")
            units.append(
                UnitRef(
                    id=unit_id,
                    course_id=course.id,
                    section_id=uuid.uuid5(uuid.NAMESPACE_URL, f"test-section-{course.slug}"),
                    canonical_unit_id=canonical_unit_id,
                    title=f"{course.slug.upper()} Unit {unit_index:02d}",
                    sort_order=unit_index,
                )
            )
            unit_kp_ids[canonical_unit_id] = (
                f"kp_{course.slug}_{unit_index:02d}_a",
                f"kp_{course.slug}_{unit_index:02d}_b",
            )
            for item_index in range(1, 5):
                items.append(
                    ItemRef(
                        item_id=f"item_{course_index}_{unit_index:02d}_{item_index:02d}",
                        unit_id=canonical_unit_id,
                        answer_index=item_index % 4,
                        choice_count=4,
                        phases=("mini_quiz", "review", "placement"),
                        kp_ids=unit_kp_ids[canonical_unit_id],
                    )
                )
    return SyntheticCatalog(
        courses=courses,
        units=tuple(units),
        items=tuple(items),
        unit_kp_ids=unit_kp_ids,
    )
