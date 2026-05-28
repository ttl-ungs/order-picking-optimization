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

from tests.opp_v3.scenarios.normal.three_missions_two_pickers_grid_graph import (
    scenario_three_missions_two_pickers_two_periods_grid_graph,
)

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)


class TestOPPModel(OPPTestCase):
    """
    Test 16: 6 orders, 3 missions, 2 pickers on a 4x4 grid with transversal aisles.
    Each order visits more than one location.
    """

    opp_location_graph, V, B = (
        scenario_three_missions_two_pickers_two_periods_grid_graph(4, 4)
    )

    def get_orders(self):
        orders = {"O1", "O2", "O3", "O4", "O5", "O6"}

        a = {(n, v): 0 for n in orders for v in self.V}

        # Each order requires at least two locations.
        a[("O1", "V2")] = 1
        a[("O1", "V6")] = 1

        a[("O2", "V2")] = 1
        a[("O2", "V7")] = 1

        a[("O3", "V5")] = 1
        a[("O3", "V9")] = 1

        a[("O4", "V6")] = 1
        a[("O4", "V14")] = 1

        a[("O5", "V4")] = 1
        a[("O5", "V8")] = 1

        a[("O6", "V11")] = 1
        a[("O6", "V14")] = 1

        y = {(n, b): 0 for n in orders for b in self.B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B2")] = 1
        y[("O4", "B2")] = 1
        y[("O5", "B3")] = 1
        y[("O6", "B3")] = 1

        return orders, a, y

    def test_6_orders_3_missions_2_pickers(self):
        N, a, y = self.get_orders()

        cap_vehicle = 25
        cap_n = {"O1": 10, "O2": 10, "O3": 10, "O4": 10, "O5": 10, "O6": 10}
        due_date = {"O1": 30, "O2": 30, "O3": 30, "O4": 30, "O5": 30, "O6": 30}

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
        model_dto.location_graph = self.opp_location_graph
        model_dto.B = self.B
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

