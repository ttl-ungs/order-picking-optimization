import unittest
from models.base.opp_location_graph import OPPLocationGraph
from tests.infra.cases.opp_test_case import OPPTestCase
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_v1.utils.output_handler import OutputHandler
from models.opp_v1.opp_model_v1 import OPPModel
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.model_dto import ModelDTO
from tests.shared_scenarios.functional.one_mission_one_picker_grid_graph_v1 import (
    scenario_one_mission_one_picker_grid_graph,
)


class TestOPPModel(OPPTestCase):
    """
    Test 15: 3 orders, 1 mission, 1 picker. Each order is assigned to the same mission and picker. 4x4 graph.
    """

    H, K, P, x, opp_location_graph, V, B = scenario_one_mission_one_picker_grid_graph(
        4, 4
    )

    def get_orders(self):
        orders = {"O1", "O2", "O3"}

        a = {(n, v): 0 for n in orders for v in self.V}
        a[("O1", "V1")] = 1
        a[("O1", "V13")] = 1
        a[("O1", "V10")] = 1

        a[("O2", "V3")] = 1
        # a[("O2", "V10")] = 1

        # a[("O3", "V1")] = 1
        a[("O3", "V2")] = 1
        # a[("O3", "V3")] = 1
        a[("O3", "V7")] = 1
        a[("O3", "V9")] = 1

        y = {(n, h): 0 for n in orders for h in self.H}
        y[("O1", "M1")] = 1
        y[("O2", "M1")] = 1
        y[("O3", "M1")] = 1

        return orders, a, y

    def get_output_graph(self):
        expected_graph = OPPLocationGraph(
            depot_node="V1",
            final_node="V16",
        )

        for i in self.opp_location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge(
            "V1", "V2", self.opp_location_graph.get_distance("V1", "V2")
        )
        expected_graph.add_edge(
            "V2", "V3", self.opp_location_graph.get_distance("V2", "V3")
        )
        expected_graph.add_edge(
            "V3", "V7", self.opp_location_graph.get_distance("V3", "V7")
        )
        expected_graph.add_edge(
            "V7", "V11", self.opp_location_graph.get_distance("V7", "V11")
        )
        expected_graph.add_edge(
            "V11", "V10", self.opp_location_graph.get_distance("V11", "V10")
        )
        expected_graph.add_edge(
            "V10", "V9", self.opp_location_graph.get_distance("V10", "V9")
        )
        expected_graph.add_edge(
            "V9", "V13", self.opp_location_graph.get_distance("V9", "V13")
        )
        expected_graph.add_edge(
            "V13", "V14", self.opp_location_graph.get_distance("V13", "V14")
        )
        expected_graph.add_edge(
            "V14", "V15", self.opp_location_graph.get_distance("V14", "V15")
        )
        expected_graph.add_edge(
            "V15", "V16", self.opp_location_graph.get_distance("V15", "V16")
        )

        return expected_graph

    def test_3_orders_1_mission_1_picker(self):
        N, a, y = self.get_orders()

        cap_vehicle = 60
        cap_n = {"O1": 25, "O2": 10, "O3": 15}
        due_date = {"O1": 10, "O2": 5, "O3": 8}

        w1 = 9.0  # cumplimiento peso alto
        w2 = 1.0  # demoras y adelanto peso bajo
        gamma = 1.0  # peso del adelanto bajo
        delta = 1.0  # peso de demora bajo

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        params = SolveModelDTO()
        params.W_c = w1
        params.W_pen = w2
        params.W_e = gamma
        params.W_t = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.T_travel = beta_time
        params.T_setup = beta_setup
        params.T_pick = beta_picking
        params.T_due_n = due_date
        params.M = M
        params.x = self.x
        params.B_nb = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = self.opp_location_graph
        model_dto.H = self.H
        model_dto.K = self.K
        model_dto.P = self.P
        model_dto.B = self.B
        model_dto.start_time = self.start_time
        model = OPPModel(model_dto)
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

        self.assertEqual(output_graph, self.get_output_graph())


if __name__ == "__main__":
    # pyscipopt.SCIP_PARAMSETTING_DEFAULT.set("limits/time", 60)
    unittest.main()
