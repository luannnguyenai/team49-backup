from src.models.course import Course, LearningUnit
from src.models.learning import Interaction, Session


def test_product_tables_have_canonical_bridge_columns():
    assert hasattr(Course, "canonical_course_id")
    assert hasattr(LearningUnit, "canonical_unit_id")


def test_runtime_learning_tables_have_canonical_bridge_columns():
    assert hasattr(Session, "canonical_phase")
    assert hasattr(Interaction, "canonical_item_id")
