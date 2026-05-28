import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.opp.solve_model_dto import SolveModelDTO
from models.opp_v3.opp_model_v3 import OPPModelV3
from models.opp_v3.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.opp_v3.scenarios.normal.scenario_18 import detour_single_mission_route
from tests.opp_v2.tests.route_assertions import (
    assert_correct_path,
    assert_route_covers_orders,
)


class TestOPPModel(OPPTestCase):
    def test_detour_single_mission_route(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            detour_single_mission_route()
        )

        N = {"O1", "O2", "O3", "O4", "O5"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1
        a[("O3", "L5")] = 1
        a[("O4", "L7")] = 1
        a[("O5", "L4")] = 1

        y = {
            ("O1", "B1"): 1,
            ("O2", "B1"): 1,
            ("O3", "B1"): 1,
            ("O4", "B1"): 1,
            ("O5", "B1"): 1,
        }
        cap_n = {n: 2.0 for n in N}

        params = SolveModelDTO()
        params.W_full = w1
        params.W_ea_ta = w2
        params.W_ea = gamma
        params.W_ta = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = 0.5
        params.B_setup = 1.0
        params.B_picking = 1.0
        params.Dd = {n: 20.0 for n in N}
        params.M = 1000.0
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPModelV3(model_dto)
        model.attach(OutputHandler())

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertEqual(result, "optimal")
        assert_route_covers_orders(self, output_graph, {"L2", "L3", "L4", "L5", "L7"})

        expected_path = ["L1", "L2", "L3", "L4", "L6", "L5", "L7", "L8"]
        assert_correct_path(self, output_graph, expected_path)


if __name__ == "__main__":
    unittest.main()

