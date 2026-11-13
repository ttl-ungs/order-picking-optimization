import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.shared_scenarios.functional.two_stage_scenarios_v5 import two_possible_routes
from tests.infra.zimpl.zpl_utils import extract_active_arcs
from tests.infra.cases.exact_model_case import ExactModelTestCase


SHORT_ROUTE = {("L1", "L4"), ("L4", "L5")}


class Case06ShortestRoute(ExactModelTestCase):
    """Choosing between routes, where the choice actually matters.

    A batch may report a completion later than it physically finishes
    (voluntary wait), so a longer route that still arrives in time costs the
    same as the shortest one: with due date 15 every route is optimal, and
    "the shortest route" is not a property of the model. With due date 10 the
    long route arrives late, and only the short route is optimal.
    """

    def test_shorter_route_is_chosen_when_the_longer_one_is_late(self):
        """Case 6b: Due date 10: the short route finishes at 8 and waits until 10; a
        long route finishes at 11.5, late. Both batches take the short route
        and complete at 10, objective 20."""
        scenario = two_possible_routes(due_date=10.0)
        routes, _, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        for batch, arcs in extract_active_arcs(routes, scenario["B"]).items():
            self.assertEqual(set(arcs), SHORT_ROUTE, f"{batch} did not take the short route")
        for batch in scenario["B"]:
            self.assertAlmostEqual(values[f"c_b${batch}"], 10.0, places=5)
        self.assertAlmostEqual(self.objective_value(), 20.0, places=5)

    def test_every_route_is_optimal_when_all_arrive_in_time(self):
        """Case 6a: Due date 15: every route arrives in time, so the route is
        not asserted, only that each batch has one and completes exactly at
        its due date, objective 30."""
        scenario = two_possible_routes(due_date=15.0)
        routes, _, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        self.assert_routes_cover_requirements(routes, scenario)
        for batch in scenario["B"]:
            self.assertAlmostEqual(values[f"c_b${batch}"], 15.0, places=5)
        self.assertAlmostEqual(self.objective_value(), 30.0, places=5)
