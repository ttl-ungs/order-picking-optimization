import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_v2.opp_model_v2 import OPPModelV2
from tests.opp.tests.opp_test_case import OPPTestCase
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_v2.utils.output_handler import OutputHandler

from tests.opp_v2.scenarios.scenario_5 import bidirectional_edges


class TestOPPModel(OPPTestCase):
    """
    Test 5: Add an extra vertex to avoid cycle. 6 vertex, 1 batch, 3 orders, 2 pickers.
    Purpose: Try to find an optimal solution for Test 4, with an extra vertex that avoids
    a cycle in the graph.
    Conclusion: Optimal solution found.
    """

    def test_repeated_picking_locations_2(self):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            bidirectional_edges()
        )

        N = {"O1", "O2", "O3"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1

        y = {("O1", "B1"): 1, ("O2", "B1"): 1, ("O3", "B1"): 1}

        cap_n = {"O1": 3.0, "O2": 3.0, "O3": 15.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0, "O3": 15.0}

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
        params.x = x
        params.y = y

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

        expected_graph.add_edge("L1", "L2", location_graph.get_distance("L1", "L2"))
        expected_graph.add_edge("L2", "L4", location_graph.get_distance("L2", "L4"))
        expected_graph.add_edge("L4", "L3", location_graph.get_distance("L4", "L3"))
        expected_graph.add_edge("L3", "LC", location_graph.get_distance("L3", "L4"))
        expected_graph.add_edge("LC", "L5", location_graph.get_distance("LC", "L5"))

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
