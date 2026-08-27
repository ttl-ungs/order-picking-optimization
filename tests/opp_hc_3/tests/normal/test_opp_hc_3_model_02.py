import unittest
import sys
import os

from dtos.hc.solve_hc_3_model_dto import SolveHC3ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from models.opp_hc_3 import OPPHillClimbing
from tests.opp.tests.opp_test_case import OPPTestCase
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO

from tests.opp_v3.scenarios.normal.scenario_02 import two_orders_two_aisles


class TestOPPHillClimbing2Model2(OPPTestCase):
    """
    Test HC2: Medium. 8 vertex, 8 edges, 2 orders, 2 batches.
    Purpose: To test the functionality of the model when it has to follow a route.
    Equivalent to test_opp_v3_model_2.py
    """

    def test_two_orders_two_aisles(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        # Order 1 must visit locations 2, 3, 4
        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1
        a[("O1", "L4")] = 1

        # Order 2 must visit locations 5, 6, 7
        a[("O2", "L5")] = 1
        a[("O2", "L6")] = 1
        a[("O2", "L7")] = 1

        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

        params = SolveHC3ModelDTO()
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
            final_node="L8",
        )

        for i in location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge("L1", "L2", location_graph.get_distance("L1", "L2"))
        expected_graph.add_edge("L2", "L3", location_graph.get_distance("L2", "L3"))
        expected_graph.add_edge("L3", "L4", location_graph.get_distance("L3", "L4"))
        expected_graph.add_edge("L4", "L8", location_graph.get_distance("L4", "L8"))

        expected_graph.add_edge("L1", "L5", location_graph.get_distance("L1", "L5"))
        expected_graph.add_edge("L5", "L6", location_graph.get_distance("L5", "L6"))
        expected_graph.add_edge("L6", "L7", location_graph.get_distance("L6", "L7"))
        expected_graph.add_edge("L7", "L8", location_graph.get_distance("L7", "L8"))

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "The model did not find a solution.",
        )

        self.assertEqual(output_graph, expected_graph)


if __name__ == "__main__":
    unittest.main()
