import unittest
from tests.infra.cases.opp_test_case import OPPTestCase
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "..")))

from models.base.opp_location_graph import OPPLocationGraph
from models.opp_v1.utils.output_handler import OutputHandler
from models.opp_v1.opp_model_v1 import OPPModel
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.model_dto import ModelDTO

from tests.shared_scenarios.functional.scenario_03_v1 import test_two_possible_routes


class TestOPPModel(OPPTestCase):
    """
    Test 3: Medium. 5 vertex, 6 edges, 2 orders, 2 missions.
    Purpose: To test the functionality of the model when it has to choose between two possible routes.
    """

    def test_two_possible_routes(self):
        V, H, K, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            test_two_possible_routes()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        # Orders must visit location 4
        a[("O1", "L4")] = 1
        a[("O2", "L4")] = 1

        y = {("O1", "M1"): 1, ("O1", "M2"): 0, ("O2", "M1"): 0, ("O2", "M2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

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
        params.x = x
        params.B_nb = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.H = H
        model_dto.K = K
        model_dto.P = P
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPModel(model_dto)
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

        expected_graph.add_edge("L1", "L4", location_graph.get_distance("L1", "L4"))
        expected_graph.add_edge("L4", "L5", location_graph.get_distance("L4", "L5"))

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "The model did not find a solution.",
        )

        self.assertEqual(output_graph, expected_graph)


if __name__ == "__main__":
    # pyscipopt.SCIP_PARAMSETTING_DEFAULT.set("limits/time", 60)
    unittest.main()
