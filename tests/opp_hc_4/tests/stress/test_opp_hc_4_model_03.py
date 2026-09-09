import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO
from models.opp_hc_4.opp_hc_4 import OPPHillClimbing
from models.opp_hc_4.utils.output_handler import OutputHandler
from tests.opp_hc_4.tests.opp_hc_4_test_case import OPPTestCaseHC4
from tests.opp_hc_2.scenarios.common.six_missions_three_pickers_grid_graph import (
    scenario_six_missions_two_periods_grid_graph,
)


# Ported from opp_hc_2's test_opp_hc_2_model_03.py for opp_hc_4/analysis parity (V_p unset, T_frio_max default +inf -> pure equivalence).
class TestOPPModel(OPPTestCaseHC4):
    """
    Test 3: 12 orders, 6 batches, 3 pickers. 25x25 grid.
    Purpose: stress the model.

    With 6 batches and 3 pickers, batches should be distributed (X_pb) with
    an even workload, and batches on the same picker must not overlap in time.
    """

    def test_625_locations(self):
        opp_location_graph, V, B = scenario_six_missions_two_periods_grid_graph(25, 25)
        N = {"O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9", "O10", "O11", "O12"}

        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "V6")] = 1
        a[("O2", "V11")] = 1
        a[("O3", "V7")] = 1
        a[("O4", "V12")] = 1
        a[("O5", "V3")] = 1
        a[("O6", "V8")] = 1
        a[("O7", "V5")] = 1
        a[("O8", "V10")] = 1
        a[("O9", "V10")] = 1
        a[("O10", "V15")] = 1
        a[("O11", "V9")] = 1
        a[("O12", "V14")] = 1

        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B2")] = 1
        y[("O4", "B2")] = 1
        y[("O5", "B3")] = 1
        y[("O6", "B3")] = 1
        y[("O7", "B4")] = 1
        y[("O8", "B4")] = 1
        y[("O9", "B5")] = 1
        y[("O10", "B5")] = 1
        y[("O11", "B6")] = 1
        y[("O12", "B6")] = 1

        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        cap_vehicle = 20.0
        cap_n = {n: 10.0 for n in N}
        due_date = {n: 15.0 for n in N}

        params = SolveHC4ModelDTO()
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

        P = {"P1", "P2", "P3"}

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = opp_location_graph
        model_dto.B = B
        model_dto.P = P
        model_dto.start_time = self.start_time
        model = OPPHillClimbing(model_dto)
        model.attach(OutputHandler())

        try:
            result, _, solution_info = self.solve_and_capture(model, params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))

        self.assert_every_batch_has_one_picker(solution_info, P)
        self.assert_workload_balance(solution_info, P, max_difference=1)
        self.assert_no_time_overlap(solution_info, P)


if __name__ == "__main__":
    unittest.main()
