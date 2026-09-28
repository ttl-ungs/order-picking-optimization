import unittest
import sys
import os

from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_hc_4 import OPPHillClimbing
from dtos.opp.model_dto import ModelDTO

from tests.opp_hc_4.opp_hc_4_test_case import OPPTestCaseHC4
from tests.shared_scenarios.functional.scenario_04 import bidirectional_edges


class TestOPPHillClimbing4RepeatedPickingLocations(OPPTestCaseHC4):
    """
    Ported from opp_aco_2's test_case_04 (test_repeated_picking_locations):
    never ported to the HC lineage at all (opp_hc_2 has no equivalent, at
    any number). An order requiring both L2 and L3 has no simple path
    back through L1 without revisiting it -- the routing constraints allow
    at most one arc into and out of each vertex, so no feasible route
    exists, even with bidirectional edges available.
    """

    def test_repeated_picking_locations(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            bidirectional_edges()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1

        y = {("O1", "B1"): 1, ("O2", "B1"): 0}
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
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertEqual(result, "infeasible", "The model did find a solution.")


if __name__ == "__main__":
    unittest.main()
