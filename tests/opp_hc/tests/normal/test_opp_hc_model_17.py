import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO
from models.opp_hc.utils.output_handler import OutputHandler
from dtos.opp.solve_model_dto import SolveModelDTO
from models.opp_hc import OPPHillClimbing
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.opp_v3.scenarios.normal.scenario_17 import branched_single_mission_route
from tests.opp_v2.tests.route_assertions import (
    assert_correct_path,
    assert_route_covers_orders,
)


class TestOPPHillClimbing(OPPTestCase):
    def test_branched_single_mission_route(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            branched_single_mission_route()
        )

        N = {"O1", "O2", "O3", "O4"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1
        a[("O3", "L5")] = 1
        a[("O4", "L6")] = 1

        y = {("O1", "B1"): 1, ("O2", "B1"): 1, ("O3", "B1"): 1, ("O4", "B1"): 1}
        cap_n = {"O1": 2.0, "O2": 2.0, "O3": 2.0, "O4": 2.0}

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
        model = OPPHillClimbing(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)
        model.attach(OutputHandler())

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertEqual(result, "optimal")
        assert_route_covers_orders(self, output_graph, {"L2", "L3", "L5", "L6"})

        expected_graph = OPPLocationGraph("L1", "L7")
        expected_graph.add_vertex("L2", "picking")
        expected_graph.add_vertex("L3", "picking")
        expected_graph.add_vertex("L4", "picking")
        expected_graph.add_vertex("L5", "picking")
        expected_graph.add_vertex("L6", "picking")
        expected_graph.add_edge("L1", "L2", location_graph.get_distance("L1", "L2"))
        expected_graph.add_edge("L2", "L3", location_graph.get_distance("L2", "L3"))
        expected_graph.add_edge("L3", "L5", location_graph.get_distance("L3", "L5"))
        expected_graph.add_edge("L5", "L6", location_graph.get_distance("L5", "L6"))
        expected_graph.add_edge("L6", "L7", location_graph.get_distance("L6", "L7"))

        self.assertEqual(output_graph, expected_graph)
        print(f"Expected graph: {expected_graph.to_string()}")
        print(f"Output graph: {output_graph.to_string()}")

        expected_path = ["L1", "L2", "L3", "L5", "L6", "L7"]
        assert_correct_path(self, output_graph, expected_path)


if __name__ == "__main__":
    unittest.main()

