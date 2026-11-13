import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.shared_scenarios.functional.two_stage_scenarios_v5 import two_batches_two_routes
from tests.infra.cases.exact_model_case import ExactModelTestCase


class Case23RoutingAndScheduling(ExactModelTestCase):
    """The routes are exported and used by the scheduling, and the longer route goes to the faster picker."""

    def test_routes_are_exported_and_used_by_scheduling(self):
        """Case 23b."""
        scenario = two_batches_two_routes()
        values, route_times, status, _ = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        self.assert_routes_cover_requirements(values, scenario)
        self.assertAlmostEqual(route_times["B1"], 5.0, places=5)
        self.assertAlmostEqual(route_times["B2"], 14.0, places=5)

        assignments = self.assignments(values, scenario["P"], scenario["B"])
        self.assertEqual(set(assignments), scenario["B"])
        self.assert_no_overlap(values, scenario, route_times)

    def test_longer_route_is_assigned_to_the_faster_picker(self):
        """Case 23a."""
        scenario = two_batches_two_routes()
        _, route_times, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        assignments = self.assignments(values, scenario["P"], scenario["B"])
        self.assertEqual(assignments["B2"], "P_fast")
        self.assertEqual(assignments["B1"], "P_slow")
        self.assert_no_overlap(values, scenario, route_times)
