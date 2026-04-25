import unittest


class TestPlacementAssessmentRepository(unittest.TestCase):
    def test_importable(self):
        from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
        self.assertTrue(callable(PlacementAssessmentRepository))

    def test_has_required_methods(self):
        from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
        self.assertTrue(hasattr(PlacementAssessmentRepository, 'get_by_user_id'))
        self.assertTrue(hasattr(PlacementAssessmentRepository, 'get_by_user_and_unit'))
        self.assertTrue(hasattr(PlacementAssessmentRepository, 'upsert'))


class TestCanonicalQuestionRepoExtension(unittest.TestCase):
    def test_get_items_for_placement_bucketed_exists(self):
        from src.repositories.canonical_question_repo import CanonicalQuestionRepository
        self.assertTrue(hasattr(CanonicalQuestionRepository, 'get_items_for_placement_bucketed'))

    def test_method_is_coroutine(self):
        import inspect
        from src.repositories.canonical_question_repo import CanonicalQuestionRepository
        method = CanonicalQuestionRepository.get_items_for_placement_bucketed
        self.assertTrue(inspect.iscoroutinefunction(method))


if __name__ == "__main__":
    unittest.main()
