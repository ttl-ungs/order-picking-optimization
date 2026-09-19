import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos import SolveModelDTO, ModelDTO
from models.opp_v2.opp_model_v2 import OPPModelV2
from models.opp_v2.utils.output_handler import OutputHandler
from tests.opp_test_case import OPPTestCase

from tests.opp_v2.scenarios.common.six_missions_three_pickers_grid_graph import (
    scenario_six_missions_three_pickers_one_period_grid_graph,
)

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)


class TestOPPModel(OPPTestCase):
    """
    Test 11: 12 orders, 6 missions, 3 pickers. Each picker has two missions, and each mission has two orders.
    One period per picker and two orders per vehicle.
    """

    def test_one_period_two_orders_per_vehicle(self):
        P, x, opp_location_graph, V, B = (
            scenario_six_missions_three_pickers_one_period_grid_graph()
        )
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

        w1 = 9.0  # cumplimiento peso alto
        w2 = 1.0  # demoras y adelanto peso bajp
        gamma = 1.0  # peso del adelanto bajo
        delta = 1.0  # peso de demora bajo

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        cap_vehicle = 20.0  # Two orders per vehicle
        cap_n = {
            "O1": 10.0,
            "O2": 10.0,
            "O3": 10.0,
            "O4": 10.0,
            "O5": 10.0,
            "O6": 10.0,
            "O7": 10.0,
            "O8": 10.0,
            "O9": 10.0,
            "O10": 10.0,
            "O11": 10.0,
            "O12": 10.0,
        }

        due_date = {
            "O1": 15.0,
            "O2": 15.0,
            "O3": 15.0,
            "O4": 15.0,
            "O5": 15.0,
            "O6": 15.0,
            "O7": 15.0,
            "O8": 15.0,
            "O9": 15.0,
            "O10": 15.0,
            "O11": 15.0,
            "O12": 15.0,
        }

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
        params.x = x
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = opp_location_graph
        model_dto.P = P
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPModelV2(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertTrue(
            result in ("optimal", "feasible"),
            "The model did not find a solution.",
        )


if __name__ == "__main__":
    # pyscipopt.SCIP_PARAMSETTING_DEFAULT.set("limits/time", 60)
    unittest.main()

