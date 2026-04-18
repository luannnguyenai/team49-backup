import types
import unittest

from src.models.course import (
    Course,
    CourseAsset,
    CourseAssetAvailabilityStatus,
    CourseAssetType,
    CourseOverview,
    CourseRecommendation,
    CourseSection,
    CourseSectionKind,
    CourseStatus,
    CourseVisibility,
    LearnerAssessmentProfile,
    LearningProgressRecord,
    LearningProgressStatus,
    LearningUnit,
    LearningUnitEntryMode,
    LearningUnitStatus,
    LearningUnitType,
    LegacyLectureMapping,
    LegacyLectureMigrationState,
    TutorContextBinding,
)
from src.schemas.course import (
    CourseCatalogItem,
    CourseCatalogResponse,
    CourseOverviewContent,
    CourseOverviewResponse,
    LearningUnitContentPayload,
    LearningUnitResponse,
    StartLearningDecisionResponse,
    TutorContextPayload,
)


class CoursePlatformFoundationTests(unittest.TestCase):
    def test_models_define_expected_tables_and_relationships(self):
        self.assertEqual(Course.__tablename__, "courses")
        self.assertEqual(CourseOverview.__tablename__, "course_overviews")
        self.assertEqual(CourseSection.__tablename__, "course_sections")
        self.assertEqual(LearningUnit.__tablename__, "learning_units")
        self.assertEqual(CourseAsset.__tablename__, "course_assets")
        self.assertEqual(
            LearnerAssessmentProfile.__tablename__, "learner_assessment_profiles"
        )
        self.assertEqual(CourseRecommendation.__tablename__, "course_recommendations")
        self.assertEqual(LearningProgressRecord.__tablename__, "learning_progress_records")
        self.assertEqual(TutorContextBinding.__tablename__, "tutor_context_bindings")
        self.assertEqual(LegacyLectureMapping.__tablename__, "legacy_lecture_mappings")

        self.assertTrue(hasattr(Course, "overview"))
        self.assertTrue(hasattr(Course, "sections"))
        self.assertTrue(hasattr(Course, "assets"))
        self.assertTrue(hasattr(Course, "recommendations"))
        self.assertTrue(hasattr(LearningUnit, "course"))
        self.assertTrue(hasattr(LearningUnit, "section"))
        self.assertTrue(hasattr(LearningUnit, "assets"))
        self.assertTrue(hasattr(LearningUnit, "tutor_context_bindings"))

    def test_enums_cover_refactor_states(self):
        self.assertEqual(
            {item.value for item in CourseStatus},
            {"ready", "coming_soon", "metadata_partial"},
        )
        self.assertEqual({item.value for item in CourseVisibility}, {"public", "hidden"})
        self.assertEqual(
            {item.value for item in CourseSectionKind},
            {"module", "unit", "lesson_group", "lecture_group"},
        )
        self.assertEqual(
            {item.value for item in LearningUnitType},
            {"lesson", "lecture", "reading", "practice"},
        )
        self.assertEqual(
            {item.value for item in LearningUnitStatus},
            {"ready", "coming_soon", "metadata_partial"},
        )
        self.assertEqual(
            {item.value for item in LearningUnitEntryMode}, {"text", "video", "hybrid"}
        )
        self.assertEqual(
            {item.value for item in CourseAssetType},
            {"video", "transcript", "slides", "thumbnail", "supplement"},
        )
        self.assertEqual(
            {item.value for item in CourseAssetAvailabilityStatus},
            {"available", "processing", "missing"},
        )
        self.assertEqual(
            {item.value for item in LearningProgressStatus},
            {"not_started", "in_progress", "completed", "blocked"},
        )
        self.assertEqual(
            {item.value for item in LegacyLectureMigrationState},
            {"pending", "mapped", "deprecated"},
        )

    def test_response_schemas_match_contract_shape(self):
        catalog = CourseCatalogResponse(
            items=[
                CourseCatalogItem(
                    id="course_cs231n",
                    slug="cs231n",
                    title="CS231n",
                    short_description="Vision course",
                    status="ready",
                    cover_image_url="https://cdn.example/courses/cs231n/cover.jpg",
                    hero_badge="Available now",
                    is_recommended=True,
                )
            ]
        )
        self.assertEqual(catalog.items[0].status, "ready")

        overview = CourseOverviewResponse(
            course=CourseCatalogItem(
                id="course_cs224n",
                slug="cs224n",
                title="CS224n",
                short_description="NLP course",
                status="coming_soon",
                cover_image_url="https://cdn.example/courses/cs224n/cover.jpg",
                hero_badge="Coming soon",
                is_recommended=False,
            ),
            overview=CourseOverviewContent(
                headline="Learn NLP systems",
                subheadline="Overview placeholder",
                summary_markdown="Course summary...",
                learning_outcomes=["Understand transformers"],
                target_audience="Learners",
                prerequisites_summary="Basic Python",
                estimated_duration_text="Coming soon",
            ),
            entry=StartLearningDecisionResponse(
                decision="redirect",
                target="/courses/cs224n",
                reason="course_unavailable",
            ),
        )
        self.assertEqual(overview.entry.reason, "course_unavailable")

        learning_unit = LearningUnitResponse(
            course=types.SimpleNamespace(slug="cs231n", title="CS231n"),
            unit=types.SimpleNamespace(
                id="unit_lecture_01",
                slug="lecture-1-introduction",
                title="Lecture 1: Introduction",
                unit_type="lecture",
                status="ready",
                entry_mode="video",
            ),
            content=LearningUnitContentPayload(
                body_markdown="Optional lecture notes",
                video_url="https://cdn.example/cs231n/lecture-1.mp4",
                transcript_available=True,
                slides_available=True,
            ),
            tutor=TutorContextPayload(
                enabled=True,
                mode="in_context",
                context_binding_id="ctx_lecture_01",
                legacy_lecture_id="cs231n-lecture-1",
            ),
        )
        self.assertTrue(learning_unit.tutor.enabled)


if __name__ == "__main__":
    unittest.main()
