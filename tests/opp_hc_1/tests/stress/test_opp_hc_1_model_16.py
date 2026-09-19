import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.hc.solve_hc_model_dto import SolveHCModelDTO
from models.opp_hc_1.opp_hc_1 import OPPHillClimbing
from models.opp_hc_1.utils.output_handler import OutputHandler
from tests.opp_test_case import OPPTestCase
from tests.opp_hc_1.scenarios.stress.scenario_double_grid import (
    scenario_two_grids_custom_setup,
)


class TestOPPModel(OPPTestCase):
    """
    Test 16: 20 orders per batch. 40 batches, 800 orders. Two 50x50 grids with 10 connectors.
    """

    def test_20_orders_per_batch_40_batches_double_50x50(self):
        location_graph, V, B, N, y, a = scenario_two_grids_custom_setup(
            40, 800, rows=50, cols=50, connectors=10
        )

        cap_n = {n: 10.0 for n in N}
        due_date = {n: 30.0 for n in N}

        cap_vehicle = 200.0
        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

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
        model.attach(OutputHandler())

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
