import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_aco_1.opp_aco_1 import OPPAntColonyOptimization
from tests.infra.cases.opp_test_case import OPPTestCase
from models.base.opp_location_graph import OPPLocationGraph
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_aco_1.utils.output_handler import OutputHandler

from tests.shared_scenarios.functional.scenario_08 import (
    test_four_orders_two_locations_two_missions,
)


class TestOPPModel(OPPTestCase):
    """
    Test 8: 5 vertex, 4 orders, 2 batches.
    Purpose: To test the functionality of the model when there are two batches and two orders are linked to two locations.
    """

    def test_four_orders_two_locations_two_missions(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            test_four_orders_two_locations_two_missions()
        )

        N = {"O1", "O2", "O3", "O4"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1
        a[("O3", "L3")] = 1
        a[("O4", "L4")] = 1

        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B2")] = 1
        y[("O4", "B2")] = 1

        cap_n = {"O1": 3.0, "O2": 3.0, "O3": 3.0, "O4": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0, "O3": 15.0, "O4": 15.0}

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
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        expected_graph = OPPLocationGraph(
            depot_node="L1",
            final_node="L5",
        )

        for i in location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge("L1", "L3", location_graph.get_distance("L1", "L3"))
        expected_graph.add_edge("L3", "L2", location_graph.get_distance("L3", "L2"))
        expected_graph.add_edge("L2", "L5", location_graph.get_distance("L2", "L5"))
        expected_graph.add_edge("L1", "L3", location_graph.get_distance("L1", "L3"))
        expected_graph.add_edge("L3", "L4", location_graph.get_distance("L3", "L4"))
        expected_graph.add_edge("L4", "L5", location_graph.get_distance("L4", "L5"))

        self.assertTrue(
            result in ("optimal", "feasible"),
            "The model did not find a solution.",
        )

        print("Output graph:", output_graph.to_string())
        print("Expected graph:", expected_graph.to_string())

        self.assertEqual(output_graph, expected_graph)


if __name__ == "__main__":
    # pyscipopt.SCIP_PARAMSETTING_DEFAULT.set("limits/time", 60)
    unittest.main()

