import unittest
import sys
import os

from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_aco_4 import OPPAntColonyOptimization
from dtos.opp.model_dto import ModelDTO

from tests.opp_aco_4.opp_aco_4_test_case import OPPTestCaseACO4
from tests.shared_scenarios.functional.scenario_01 import basic_two_orders_capacity_limit


class TestOPPAntColonyOptimization4Model4ColdChainEligibility(OPPTestCaseACO4):
    """
    Test ACO4-4: Cold chain eligibility. Same batch/graph as ACO4-2/3, with
    two pickers: P1 (slow) violates T_frio_max, P2 (fast) satisfies it.
    Purpose: mirrors stage2_scheduling.zpl's PB_elig -- _select_picker's
    candidate pool must exclude ineligible (picker, batch) pairs, so the
    batch must be assigned to P2, without needing pheromones to "discover"
    it via reinforcement over many iterations (unlike ACO4-2, where both
    pickers were eligible and only the objective favored the fast one).
    """

    def test_only_eligible_picker_is_assigned(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            basic_two_orders_capacity_limit()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1

        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 1, ("O2", "B2"): 0}
        cap_n = {"O1": 2.0, "O2": 2.0}

        params = SolveAco4ModelDTO()
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
        # t_exec_pb(P1) = 17.5 (> 10.0, ineligible); t_exec_pb(P2) = 6.25 (<= 10.0, eligible).
        params.V_p = {"P1": 1.0, "P2": 10.0}
        params.T_frio_max = 10.0
        params.Seed = 1

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.P = {"P1", "P2"}
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)

        try:
            result, output_graph, solution_info = self.solve_and_capture(model, params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))
        self.assert_every_batch_has_one_picker(solution_info, {"P1", "P2"})
        self.assert_cold_chain_respected(solution_info, params.T_frio_max)
        self.assertEqual(solution_info["picker_assignments"]["B1"], "P2")


if __name__ == "__main__":
    unittest.main()
