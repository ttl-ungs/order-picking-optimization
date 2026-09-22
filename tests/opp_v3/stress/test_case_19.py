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
from tests.shared_scenarios.stress.scenario_custom_setup import scenario_custom_setup


class TestOPPModel(OPPTestCase):
    """
    Test 19: Extremely linear grid edge case. 50 orders per batch. 20 batches, 1000 orders. 2x500 grid.
    """

    def test_extremely_linear_grid(self):
        location_graph, V, B, N, y, a = scenario_custom_setup(
            batches=20, orders=1000, rows=2, cols=500
        )

        cap_n = {n: 10.0 for n in N}
        due_date = {n: 30.0 for n in N}

        cap_vehicle = 500.0
        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

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
        model_dto.location_graph = location_graph
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
