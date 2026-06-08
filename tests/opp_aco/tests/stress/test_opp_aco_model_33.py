import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos import SolveAcoModelDTO, ModelDTO
from models.opp_aco.opp_aco import OPPAntColonyOptimization
from models.opp_aco.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase

from tests.opp_aco.scenarios.stress.scenario_custom_setup import scenario_custom_setup


class TestOPPModel(OPPTestCase):

    def test_10_orders_per_batch_7_x_7_500_orders(self):
        opp_location_graph, V, B, N, y, a = scenario_custom_setup(
            50, 500, 7, 7
        )

        cap_n = {f"O{n}": 10 for n in range(1, len(N) + 1)}
        due_date = {f"O{n}": 30 for n in range(1, len(N) + 1)}

        cap_vehicle = 200
        w1 = 9.0 # Mucho peso del tiempo de cumplimiento
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
        model_dto.location_graph = opp_location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)
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

