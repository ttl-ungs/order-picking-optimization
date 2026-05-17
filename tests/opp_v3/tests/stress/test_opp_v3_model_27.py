import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos import SolveModelDTO, ModelDTO
from models.opp_v3.opp_model_v3 import OPPModelV3
from models.opp_v3.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase

from tests.opp_v3.scenarios.stress.scenario_custom_setup import scenario_custom_setup


class TestOPPModel(OPPTestCase):

    def test_50_orders_per_batch_5_x_5(self):
        opp_location_graph, V, B, N, y, a = scenario_custom_setup(
            10, 500, 5, 5
        )

        cap_n = {f"O{n}": 10 for n in range(1, len(N) + 1)}
        due_date = {f"O{n}": 30 for n in range(1, len(N) + 1)}

        cap_vehicle = 40
        w1 = 9.0 # Mucho peso del tiempo de cumplimiento
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        params = SolveModelDTO()
        params.w1 = w1
        params.w2 = w2
        params.gamma = gamma
        params.delta = delta
        params.cap_n = cap_n
        params.cap_vehicle = cap_vehicle
        params.a = a
        params.beta_time = beta_time
        params.beta_setup = beta_setup
        params.beta_picking = beta_picking
        params.due_date = due_date
        params.M = M
        params.y = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = opp_location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPModelV3(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertTrue(
            result in ("optimal", "feasible"),
            "The model did not find a feasible solution.",
        )


if __name__ == "__main__":
    unittest.main()

