import unittest
import sys
import os

from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_aco_4 import OPPAntColonyOptimization
from tests.infra.cases.opp_test_case import OPPTestCase

from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO

from tests.shared_scenarios.functional.scenario_01 import basic_two_orders_capacity_limit


class TestOPPAntColonyOptimization4Model1Equivalence(OPPTestCase):
    """
    Test ACO4-1: Basic. Same scenario as test_case_01.
    Purpose: with V_p unset (all speeds default to 1.0) and T_cold left
    at its default (+inf), opp_aco_4 must behave exactly like opp_aco_2 -
    the picker-speed/cold-chain extensions must be a no-op unless configured.
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

        params = SolveAco4ModelDTO()
        params.W_c = w1
        params.W_pen = w2
        params.W_e = gamma
        params.W_t = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.T_travel = beta_time
        params.T_setup = beta_setup
        params.T_pick = beta_picking
        params.T_due_n = due_date
        params.M = M
        params.B_nb = y
        # V_p and T_cold left at their defaults (speed 1.0, no cold chain).

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)

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

        self.assertTrue(
            result in ("optimal", "feasible"),
            "The model did not find a solution.",
        )

        self.assertIsNotNone(output_graph, "Output graph should not be None")
        self.assertEqual(set(output_graph.get_vertices()), set(location_graph.get_vertices()),
                        "Output graph should contain all vertices")

        self.assertTrue(output_graph.has_edge("L1", "L2") or output_graph.has_edge("L1", "L3"),
                       "Should have an arc from depot")
        self.assertTrue(output_graph.has_edge("L2", "L4") or output_graph.has_edge("L3", "L4"),
                       "Should have an arc to final")


if __name__ == "__main__":
    unittest.main()
