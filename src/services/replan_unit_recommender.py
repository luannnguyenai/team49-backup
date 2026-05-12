"""
services/replan_unit_recommender.py
----------------------------------
LLM-based unit recommendation for Replan.

After keywords are extracted and units are found in the learning path,
this service uses LLM to analyze user intent and recommend which units
to test based on their claim.
"""

import logging

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field

from src.config import settings
from src.services.chat_model_factory import build_chat_model_kwargs

log = logging.getLogger(__name__)


class UnitRecommendation(BaseModel):
    """Single unit recommendation."""

    unit_id: str = Field(description="Canonical unit ID to recommend")
    reason: str = Field(description="Why this unit should be tested")


class UnitRecommendationResult(BaseModel):
    """LLM recommendation result."""

    recommendations: list[UnitRecommendation] = Field(
        description="List of recommended units to test"
    )
    should_skip_all: bool = Field(
        default=False, description="True if user's intent doesn't match any available units"
    )
    skip_reason: str = Field(
        default="", description="Reason for skipping if should_skip_all is True"
    )

    model_config = ConfigDict(populate_by_name=True)


_SYSTEM_PROMPT = """You are a learning advisor helping to select which units a learner should test.

**User's Learning Goal:**
The user wants to skip or test out of certain topics by demonstrating they already know them.

**Available Units in Their Path:**
A list of units with their titles and descriptions.

**Your Task:**
1. Analyze the user's intent from their claim
2. Look at available units in their learning path
3. Recommend ONLY units that genuinely match what they're describing
4. If NONE of the available units match their intent, set should_skip_all=true

**Important:**
- Don't force a match if there isn't one
- If user mentions "YOLO" but the course only has NLP topics, skip rather than recommending unrelated CNN topics
- If user mentions Computer Vision concepts but course is NLP, be honest about the mismatch
- Prioritize exact conceptual matches over partial keyword overlaps

**Response Format:**
JSON with recommendations list, should_skip_all boolean, and skip_reason string.
"""


class ReplanUnitRecommender:
    """LLM-based unit recommender."""

    def __init__(self):
        self._model = None

    @property
    def model(self):
        """Lazy-load the model."""
        if self._model is None:
            kwargs = build_chat_model_kwargs(
                model=settings.default_model,
                temperature=0.2,  # Low temperature for consistent recommendations
                max_tokens=1500,
            )
            self._model = init_chat_model(**kwargs)
            log.info(f"Initialized Replan Unit Recommender with model: {settings.default_model}")
        return self._model

    async def recommend(
        self,
        user_claim: str,
        available_units: list[
            dict
        ],  # [{"unit_id": str, "title": str, "summary": str, "key_points": list[str]}]
    ) -> UnitRecommendationResult:
        """Recommend which units to test based on user claim.

        Args:
            user_claim: User's original knowledge claim
            available_units: Units found in learning path that matched keywords

        Returns:
            UnitRecommendationResult with recommendations and skip decision
        """
        if not available_units:
            return UnitRecommendationResult(
                recommendations=[],
                should_skip_all=True,
                skip_reason="No matching units found in learning path",
            )

        # Build unit context for LLM
        units_context = "\n".join(
            [
                f"- {u['unit_id']}: {u['title']}\n  Summary: {(u.get('summary') or 'N/A')[:150]}\n  Key Points: {', '.join(u.get('key_points', [])[:3])}"
                for u in available_units[:20]  # Limit to 20 units
            ]
        )

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=f"""**User's Claim:**
"{user_claim}"

**Available Units in Learning Path:**
{units_context}

Analyze and recommend which units this user should test. Be strict - only recommend if there's a genuine conceptual match."""
            ),
        ]

        try:
            structured_model = self.model.with_structured_output(UnitRecommendationResult)
            response = await structured_model.ainvoke(messages)
            log.info(
                f"LLM recommend: {len(response.recommendations)} units, skip_all={response.should_skip_all}"
            )
            return response

        except Exception as e:
            log.error(f"LLM recommendation failed: {e}")
            # Fallback: return all units (conservative approach)
            return UnitRecommendationResult(
                recommendations=[
                    UnitRecommendation(unit_id=u["unit_id"], reason="Matched keywords (fallback)")
                    for u in available_units
                ],
                should_skip_all=False,
            )


# Singleton instance
_recommender: ReplanUnitRecommender | None = None


def get_unit_recommender() -> ReplanUnitRecommender:
    """Get or create the singleton recommender instance."""
    global _recommender
    if _recommender is None:
        _recommender = ReplanUnitRecommender()
    return _recommender
