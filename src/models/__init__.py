"""
models/__init__.py
------------------
Re-export every model so that Alembic env.py only needs to import this
package to discover all tables.
"""

from src.models.base import Base  # noqa: F401
from src.models.canonical import (  # noqa: F401
    CanonicalUnit,
    ConceptKP,
    ItemCalibration,
    ItemKPMap,
    ItemPhaseMap,
    PrerequisiteEdge,
    PrunedEdge,
    QuestionBankItem,
    UnitKPMap,
)
from src.models.content import KnowledgeComponent, Module, Question, Topic  # noqa: F401
from src.models.course import (  # noqa: F401
    Course,
    CourseAsset,
    CourseOverview,
    CourseRecommendation,
    CourseSection,
    LearnerAssessmentProfile,
    LearningProgressRecord,
    LearningUnit,
    LegacyLectureMapping,
    TutorContextBinding,
)
from src.models.learning import (  # noqa: F401
    GoalPreference,
    Interaction,
    LearnerMasteryKP,
    LearningPath,
    MasteryScore,
    PlanHistory,
    PlannerSessionState,
    RationaleLog,
    Session,
    WaivedUnit,
)

# Original lecture models
from src.models.store import Chapter, Lecture, QAHistory, TranscriptLine  # noqa: F401

# New personalized learning models
from src.models.user import User  # noqa: F401

__all__ = [
    "Base",
    # Lecture models
    "Lecture",
    "Chapter",
    "TranscriptLine",
    "QAHistory",
    # User
    "User",
    # Content
    "Module",
    "Topic",
    "KnowledgeComponent",
    "Question",
    # Canonical content artifact tables
    "ConceptKP",
    "CanonicalUnit",
    "UnitKPMap",
    "QuestionBankItem",
    "ItemCalibration",
    "ItemPhaseMap",
    "ItemKPMap",
    "PrerequisiteEdge",
    "PrunedEdge",
    # Course platform
    "Course",
    "CourseOverview",
    "CourseSection",
    "LearningUnit",
    "CourseAsset",
    "LearnerAssessmentProfile",
    "CourseRecommendation",
    "LearningProgressRecord",
    "TutorContextBinding",
    "LegacyLectureMapping",
    # Learning
    "Session",
    "Interaction",
    "MasteryScore",
    "LearningPath",
    "LearnerMasteryKP",
    "GoalPreference",
    "WaivedUnit",
    "PlanHistory",
    "RationaleLog",
    "PlannerSessionState",
]
