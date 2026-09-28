import unittest
import sys
import os

from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_hc_4 import OPPHillClimbing
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO

from tests.opp_hc_4.opp_hc_4_test_case import OPPTestCaseHC4
from tests.shared_scenarios.functional.scenario_03 import two_possible_routes_batches


class TestOPPHillClimbing4TwoPossibleRoutes(OPPTestCaseHC4):
    """
    Ported from opp_aco_2's test_case_03 (test_two_possible_routes): never
    ported to the HC lineage at all (opp_hc_2 has no equivalent, at any
    number -- checked by method name, not file number, the same way
    test_case_25-33's origins were traced). 5 vertices, 6 edges, 2 orders
    sharing a batch that must choose between two possible routes to L4.
    """

    def test_two_possible_routes(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            two_possible_routes_batches()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        # Orders must visit location 4
        a[("O1", "L4")] = 1
        a[("O2", "L4")] = 1

        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        params = SolveHC4ModelDTO()
        params.W_full = w1
        params.W_ea_ta = w2
        params.W_ea = gamma
        params.W_ta = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = 0.5
        params.B_setup = 1.0
        params.B_picking = 1.0
        params.Dd = {"O1": 15.0, "O2": 15.0}
        params.M = 1000.0
        params.Bn = y
        params.Seed = 1
        params.Max_it = 100
        params.Max_imp = 30
        params.Max_time = 10.0

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

        expected_graph = OPPLocationGraph(depot_node="L1", final_node="L5")
        for i in location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")
        expected_graph.add_edge("L1", "L4", location_graph.get_distance("L1", "L4"))
        expected_graph.add_edge("L4", "L5", location_graph.get_distance("L4", "L5"))

        self.assertIn(result, ("optimal", "feasible"), "The model did not find a solution.")
        self.assertEqual(output_graph, expected_graph)


if __name__ == "__main__":
    unittest.main()
