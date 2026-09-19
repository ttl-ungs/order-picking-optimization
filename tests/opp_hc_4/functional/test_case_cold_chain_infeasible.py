import unittest
import sys
import os

from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_hc_4 import OPPHillClimbing
from tests.support.opp_test_case import OPPTestCase
from dtos.opp.model_dto import ModelDTO

from tests.shared_scenarios.functional.scenario_01 import basic_two_orders_capacity_limit


class TestOPPHillClimbing4Model3ColdChainInfeasible(OPPTestCase):
    """
    Test HC4-3: Cold chain infeasibility. Same batch/graph as HC4-2, but
    with a single (slow) picker and a cold-chain deadline no picker can
    meet.
    Purpose: mirrors opp_v5's B_sin_picker_elegible short-circuit - when
    every (picker, batch) pair violates T_frio_max, solve() must return
    "infeasible" up front instead of running Hill Climbing on an
    unsatisfiable instance.
    """

    def test_unreachable_cold_chain_deadline_is_infeasible(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            basic_two_orders_capacity_limit()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1

        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 1, ("O2", "B2"): 0}
        cap_n = {"O1": 2.0, "O2": 2.0}

        params = SolveHC4ModelDTO()
        params.W_full = 1.0
        params.W_ea_ta = 0.0
        params.W_ea = 0.0
        params.W_ta = 0.0
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = 0.5
        params.B_setup = 1.0
        params.B_picking = 1.0
        params.Dd = {"O1": 1000.0, "O2": 1000.0}
        params.M = 1000.0
        params.Bn = y
        params.V_p = {"P1": 1.0}
        # Best achievable t_exec_pb(P1, B1) = 5.0 + 12.5/1.0 = 17.5 -- unreachable at 10.0.
        params.T_frio_max = 10.0

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.P = {"P1"}
        model_dto.start_time = self.start_time
        model = OPPHillClimbing(model_dto)

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertEqual(result, "infeasible")
        self.assertIsNone(output_graph)


if __name__ == "__main__":
    unittest.main()
