"""
models/__init__.py
------------------
Re-export every model so that Alembic env.py only needs to import this
package to discover all tables.
"""

from src.models.base import Base  # noqa: F401

# Original lecture models
from src.models.store import Lecture, Chapter, TranscriptLine, QAHistory  # noqa: F401

# New personalized learning models
from src.models.user import User  # noqa: F401
from src.models.content import Module, Topic, KnowledgeComponent, Question  # noqa: F401
from src.models.learning import (  # noqa: F401
    Session,
    Interaction,
    MasteryScore,
    LearningPath,
)

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
    # Learning
    "Session",
    "Interaction",
    "MasteryScore",
    "LearningPath",
]
