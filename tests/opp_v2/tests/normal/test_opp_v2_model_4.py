import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from models.opp_v2.opp_model_v2 import OPPModelV2
from tests.opp.tests.opp_test_case import OPPTestCase
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_v2.utils.output_handler import OutputHandler

from tests.opp_v2.scenarios.normal.scenario_4 import bidirectional_edges


class TestOPPModel(OPPTestCase):
    """
    Test 4: 5 vertex, 2 orders, 1 batch.
    Purpose: Force the model to generate a cycle.
    Status: Not feasible solution found.
    """

    def test_repeated_picking_locations(self):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            bidirectional_edges()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1

        y = {("O1", "B1"): 1, ("O2", "B1"): 0}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

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
        model_dto.location_graph = location_graph
        model_dto.P = P
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPModelV2(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertTrue(
            result in ("infeasible",),
            "The model did find a solution.",
        )


if __name__ == "__main__":
    # pyscipopt.SCIP_PARAMSETTING_DEFAULT.set("limits/time", 60)
    unittest.main()

