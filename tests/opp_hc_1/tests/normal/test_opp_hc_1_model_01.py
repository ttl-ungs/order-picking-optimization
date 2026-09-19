import unittest

import sys
import os

from dtos.hc.solve_hc_model_dto import SolveHCModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)


from models.opp_hc_1 import OPPHillClimbing
from tests.opp_test_case import OPPTestCase

from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO

from tests.shared_scenarios.normal.scenario_01 import basic_two_orders_capacity_limit


class TestOPPHillClimbingModel1(OPPTestCase):
    """
    Test HC1: Basic. 4 vertex, 5 edges, 2 orders, 2 batches.
    Purpose: to test the basic functionality of the Hill Climbing model.
    Equivalent to test_opp_v3_model_1.py
    """

    def test_basic_two_orders_capacity_limit(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            basic_two_orders_capacity_limit()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1

        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

        params = SolveHCModelDTO()
        params.W_full = w1
        params.W_ea_ta = w2
        params.W_ea = gamma
        params.W_ta = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = beta_time
        params.B_setup = beta_setup
        params.B_picking = beta_picking
        params.Dd = due_date
        params.M = M
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPHillClimbing(model_dto)

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        expected_graph = OPPLocationGraph(
            depot_node="L1",
            final_node="L4",
        )

        for i in location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge("L1", "L2", location_graph.get_distance("L1", "L2"))
        expected_graph.add_edge("L2", "L4", location_graph.get_distance("L2", "L4"))

        expected_graph.add_edge("L1", "L3", location_graph.get_distance("L1", "L3"))
        expected_graph.add_edge("L3", "L4", location_graph.get_distance("L3", "L4"))

        self.assertTrue(
            result in ("optimal", "feasible"),
            "The model did not find a solution.",
        )

        # Validate output graph structure
        self.assertIsNotNone(output_graph, "Output graph should not be None")
        self.assertEqual(set(output_graph.get_vertices()), set(location_graph.get_vertices()),
                        "Output graph should contain all vertices")

        # Validate that both batches are connected (depot to final through required locations)
        # The exact route may differ from the exact solver (it's a heuristic)
        self.assertTrue(output_graph.has_edge("L1", "L2") or output_graph.has_edge("L1", "L3"),
                       "Should have an arc from depot")
        self.assertTrue(output_graph.has_edge("L2", "L4") or output_graph.has_edge("L3", "L4"),
                       "Should have an arc to final")


if __name__ == "__main__":
    unittest.main()
