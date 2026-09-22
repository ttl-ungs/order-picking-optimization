import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.opp.solve_model_dto import SolveModelDTO
from models.opp_v3.opp_model_v3 import OPPModelV3
from models.opp_v3.utils.output_handler import OutputHandler
from tests.infra.cases.opp_test_case import OPPTestCase
from tests.shared_scenarios.common.six_missions_three_pickers_grid_graph import (
    scenario_six_missions_two_periods_grid_graph,
)


class TestOPPModel(OPPTestCase):
    """
    Test 1: 12 orders, 6 batches. 10x10 grid.
    Purpose: stress the model.
    """

    def test_100_locations(self):
        opp_location_graph, V, B = scenario_six_missions_two_periods_grid_graph(10, 10)
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

        params = SolveModelDTO()
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
        model_dto.location_graph = opp_location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPModelV3(model_dto)
        model.attach(OutputHandler())

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
