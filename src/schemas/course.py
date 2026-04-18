"""
schemas/course.py
-----------------
Pydantic schemas for the canonical course-platform API.
"""

from pydantic import BaseModel, Field


class CourseCatalogItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    slug: str
    title: str
    short_description: str
    status: str
    cover_image_url: str | None = None
    hero_badge: str | None = None
    is_recommended: bool = False


class CourseCatalogResponse(BaseModel):
    items: list[CourseCatalogItem] = Field(default_factory=list)


class CourseOverviewContent(BaseModel):
    model_config = {"from_attributes": True}

    headline: str
    subheadline: str | None = None
    summary_markdown: str
    learning_outcomes: list[str] = Field(default_factory=list)
    target_audience: str | None = None
    prerequisites_summary: str | None = None
    estimated_duration_text: str | None = None
    structure_snapshot: dict | None = None
    cta_label: str | None = None


class StartLearningDecisionResponse(BaseModel):
    decision: str
    target: str
    reason: str


class CourseOverviewResponse(BaseModel):
    course: CourseCatalogItem
    overview: CourseOverviewContent
    entry: StartLearningDecisionResponse


class LearningUnitCourseSummary(BaseModel):
    model_config = {"from_attributes": True}

    slug: str
    title: str


class LearningUnitSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    slug: str
    title: str
    unit_type: str
    status: str
    entry_mode: str


class LearningUnitContentPayload(BaseModel):
    body_markdown: str | None = None
    video_url: str | None = None
    transcript_available: bool = False
    slides_available: bool = False


class TutorContextPayload(BaseModel):
    enabled: bool
    mode: str
    context_binding_id: str | None = None


class LearningUnitResponse(BaseModel):
    course: LearningUnitCourseSummary
    unit: LearningUnitSummary
    content: LearningUnitContentPayload
    tutor: TutorContextPayload
