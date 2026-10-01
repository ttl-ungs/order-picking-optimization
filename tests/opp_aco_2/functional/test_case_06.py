import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_aco_2 import OPPAntColonyOptimization
from tests.infra.cases.opp_test_case import OPPTestCase
from models.base.opp_location_graph import OPPLocationGraph
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_aco_2.utils.output_handler import OutputHandler

from tests.shared_scenarios.functional.scenario_06 import test_two_orders_two_locations


class TestOPPModel(OPPTestCase):
    """
    Test 6: 4 vertex, 2 orders, 1 batch.
    Purpose: To test the functionality of the opp_aco_2 model when two orders are linked to two locations.
    """

    def test_two_orders_two_locations(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            test_two_orders_two_locations()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1

        y = {("O1", "B1"): 1, ("O2", "B1"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

        params = SolveAcoModelDTO()
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
        params.B_nb = y

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
            final_node="L4",
        )

        for i in location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge("L1", "L3", location_graph.get_distance("L1", "L3"))
        expected_graph.add_edge("L3", "L2", location_graph.get_distance("L3", "L2"))
        expected_graph.add_edge("L2", "L4", location_graph.get_distance("L2", "L4"))

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
