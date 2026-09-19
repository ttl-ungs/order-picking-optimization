import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.shared_scenarios.functional.two_stage_scenarios_v5 import two_batches_two_routes
from tests.opp_v5.opp_test_case_v5 import OPPTestCaseV5


class TestOPPV5RoutingAndScheduling(OPPTestCaseV5):
    """Regression of the normal v4 route tests through the v5 two-stage flow."""

    def test_routes_are_exported_and_used_by_scheduling(self):
        scenario = two_batches_two_routes()
        stage1_values, route_times, status, stage2_values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        self.assert_routes_cover_requirements(stage1_values, scenario)
        self.assertAlmostEqual(route_times["B1"], 5.0, places=5)
        self.assertAlmostEqual(route_times["B2"], 14.0, places=5)

        assignments = self.assignments(stage2_values, scenario["P"], scenario["B"])
        self.assertEqual(set(assignments), scenario["B"])
        self.assert_no_overlap(stage2_values, scenario, route_times)

    def test_longer_route_is_assigned_to_the_faster_picker(self):
        scenario = two_batches_two_routes()
        _, route_times, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        assignments = self.assignments(values, scenario["P"], scenario["B"])
        self.assertEqual(assignments["B2"], "P_fast")
        self.assertEqual(assignments["B1"], "P_slow")
        self.assert_no_overlap(values, scenario, route_times)
