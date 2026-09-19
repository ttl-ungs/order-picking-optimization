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
from tests.shared_scenarios.normal.scenario_01 import basic_two_orders_capacity_limit


class TestOPPAntColonyOptimization4Model2PickerSpeed(OPPTestCaseACO4):
    """
    Test ACO4-2: Picker speed. Same graph as ACO4-1, but both orders share
    a single batch (B1) and there are two pickers with very different
    speeds. Purpose: with cold chain disabled (T_frio_max=+inf), ACO must
    still learn (via the (batch, picker) pheromone table) that assigning
    the batch to the FASTER picker lowers the objective (W_full weights
    recollection time only).
    """

    def test_faster_picker_is_preferred(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            basic_two_orders_capacity_limit()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        # Both orders require locations within the same aisle (L1-L2-L3-L4),
        # so a single feasible route exists for the shared batch.
        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1

        # Both orders in ONE batch (B1); B2 stays empty.
        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 1, ("O2", "B2"): 0}
        cap_n = {"O1": 2.0, "O2": 2.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 1000.0, "O2": 1000.0}

        params = SolveAco4ModelDTO()
        params.W_full = 1.0
        params.W_ea_ta = 0.0  # isolate the recollection-time term
        params.W_ea = 0.0
        params.W_ta = 0.0
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = beta_time
        params.B_setup = beta_setup
        params.B_picking = beta_picking
        params.Dd = due_date
        params.M = M
        params.Bn = y
        params.V_p = {"P1": 1.0, "P2": 10.0}  # P1 slow, P2 fast
        params.T_frio_max = float("inf")  # cold chain disabled
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
        self.assert_no_time_overlap(solution_info, {"P1", "P2"})

        # Best feasible route for {L2, L3}: L1->L2->L3->L4, distance 25.
        # fixed_time = B_setup + B_picking * sum(C_n) = 1.0 + 1.0*4.0 = 5.0
        # route_time = B_time * distance = 0.5 * 25 = 12.5
        # t_exec_pb(P1) = 5.0 + 12.5/1.0  = 17.5
        # t_exec_pb(P2) = 5.0 + 12.5/10.0 =  6.25
        self.assertEqual(
            solution_info["picker_assignments"]["B1"], "P2",
            "ACO should learn to assign the batch to the faster picker to lower the objective",
        )
        self.assertAlmostEqual(solution_info["batch_times"]["B1"], 6.25, places=4)


if __name__ == "__main__":
    unittest.main()
