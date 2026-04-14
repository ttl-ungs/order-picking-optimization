import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from dtos.opp.opp_model_dto import OppModelDTO
from dtos.opp.solve_model_dto import SolveModelDTO
from models.opp_v2.opp_model_v2 import OPPModelV2
from models.opp_v2.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.opp_v2.scenarios.scenario_10 import detour_single_mission_route
from tests.opp_v2.tests.route_assertions import assert_route_covers_orders


class TestOPPModel(OPPTestCase):
    def test_detour_single_mission_route(self):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            detour_single_mission_route()
        )

        N = {"O1", "O2", "O3", "O4", "O5"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        a[("O2", "L5")] = 1
        a[("O3", "L6")] = 1
        a[("O4", "L4")] = 1
        a[("O5", "L5")] = 1

        y = {
            ("O1", "B1"): 1,
            ("O2", "B1"): 1,
            ("O3", "B1"): 1,
            ("O4", "B1"): 1,
            ("O5", "B1"): 1,
        }
        cap_n = {n: 2.0 for n in N}

        params = SolveModelDTO()
        params.w1 = w1
        params.w2 = w2
        params.gamma = gamma
        params.delta = delta
        params.cap_n = cap_n
        params.cap_vehicle = cap_vehicle
        params.a = a
        params.beta_time = 0.5
        params.beta_setup = 1.0
        params.beta_picking = 1.0
        params.due_date = {n: 20.0 for n in N}
        params.M = 1000.0
        params.x = x
        params.y = y

        model_dto = OppModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.P = P
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPModelV2(model_dto)
        model.attach(OutputHandler())

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertEqual(result, "optimal")
        assert_route_covers_orders(self, output_graph, {"L2", "L4", "L5", "L6"})


if __name__ == "__main__":
    unittest.main()
