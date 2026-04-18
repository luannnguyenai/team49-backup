"""
services/learning_unit_service.py
---------------------------------
Learning-unit payloads for the canonical lecture experience.
The route exists now so later tasks can fill in real CS231n mappings.
"""

from src.schemas.course import LearningUnitResponse


async def get_learning_unit_payload(
    course_slug: str,
    unit_slug: str,
) -> LearningUnitResponse | None:
    del course_slug, unit_slug
    return None
