import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.opp_aco.opp_aco import OPPAntColonyOptimization
from models.opp_aco.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.opp_aco.scenarios.stress.scenario_double_grid import (
    scenario_two_grids_custom_setup,
)

from tests.test_config import RUN_LARGE_TESTS


class TestOPPModel(OPPTestCase):
    """
    Test 15: 25 orders per batch. 30 batches, 750 orders. Two 50x50 grids with 10 connectors.
    """

    @unittest.skipUnless(
        RUN_LARGE_TESTS, "Requires RUN_LARGE_TESTS=1; model size is huge."
    )
    def test_25_orders_per_batch_30_batches_double_50x50(self):
        location_graph, V, B, N, y, a = scenario_two_grids_custom_setup(
            30, 750, rows=50, cols=50, connectors=10
        )

        cap_n = {n: 10.0 for n in N}
        due_date = {n: 30.0 for n in N}

        cap_vehicle = 250.0
        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        params = SolveAcoModelDTO()
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
        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
