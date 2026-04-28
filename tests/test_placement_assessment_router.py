# tests/test_placement_assessment_router.py
import unittest


class PlacementAssessmentRouterRegistrationTests(unittest.TestCase):
    def test_router_importable(self):
        from src.routers.placement_assessment import placement_assessment_router
        self.assertIsNotNone(placement_assessment_router)

    def test_router_has_four_routes(self):
        from src.routers.placement_assessment import placement_assessment_router
        paths = {route.path for route in placement_assessment_router.routes}
        self.assertIn("/api/placement-assessment/start", paths)
        self.assertIn("/api/placement-assessment/submit", paths)
        self.assertIn("/api/placement-assessment/results", paths)
        self.assertIn("/api/placement-assessment/topic-decision", paths)

    def test_router_registered_in_app(self):
        from src.api.app import app
        all_routes = {route.path for route in app.routes}
        self.assertIn("/api/placement-assessment/start", all_routes)
        self.assertIn("/api/placement-assessment/submit", all_routes)
        self.assertIn("/api/placement-assessment/results", all_routes)
        self.assertIn("/api/placement-assessment/topic-decision", all_routes)


if __name__ == "__main__":
    unittest.main()
