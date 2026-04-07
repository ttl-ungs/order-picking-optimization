import unittest
from tests.opp.tests.opp_test_case import OPPTestCase
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "..")))

from models.opp.utils.opp_location_graph import OPPLocationGraph
from utils.output_handler import OutputHandler
from models.opp.opp_model import OPPModel
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.opp_model_dto import OppModelDTO

from tests.opp.scenarios.scenario_2 import two_orders_two_aisles


class TestOPPModel(OPPTestCase):
    """
    Test 2.1: Medium. 8 vertex, 8 edges, 2 orders, 2 missions.
    Purpose: To test the functionality of the model when it has to follow a route.
    """

    def test_two_orders_two_aisles(self):
        V, H, K, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        # Order 1 must visit locations 2, 3, 4
        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1
        a[("O1", "L4")] = 1

        # Order 2 must visit locations 5, 6, 7
        a[("O2", "L5")] = 1
        a[("O2", "L6")] = 1
        a[("O2", "L7")] = 1

        y = {("O1", "M1"): 1, ("O1", "M2"): 0, ("O2", "M1"): 0, ("O2", "M2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

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
        params.start_time = self.start_time

        model_dto = OppModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.H = H
        model_dto.K = K
        model_dto.P = P
        model_dto.B = B
        model = OPPModel(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        expected_graph = OPPLocationGraph(
            depot_node="L1",
            final_node="L8",
        )

        for i in location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge("L1", "L2", location_graph.get_distance("L1", "L2"))
        expected_graph.add_edge("L2", "L3", location_graph.get_distance("L2", "L3"))
        expected_graph.add_edge("L3", "L4", location_graph.get_distance("L3", "L4"))
        expected_graph.add_edge("L4", "L8", location_graph.get_distance("L4", "L8"))

        expected_graph.add_edge("L1", "L5", location_graph.get_distance("L1", "L5"))
        expected_graph.add_edge("L5", "L6", location_graph.get_distance("L5", "L6"))
        expected_graph.add_edge("L6", "L7", location_graph.get_distance("L6", "L7"))
        expected_graph.add_edge("L7", "L8", location_graph.get_distance("L7", "L8"))

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "The model did not find a solution.",
        )

        self.assertEqual(output_graph, expected_graph)

    """
        Test 2.2: Medium. 8 vertex, 8 edges, 2 orders, 2 missions.
        Purpose: To test the functionality of the model when we have few vertex assigned to orders.
    """

    def test_two_orders_two_aisles_one_picking_point_per_order(self):
        V, H, K, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        # Order 1 must visit location 3
        a[("O1", "L3")] = 1

        # Order 2 must visit location 5
        a[("O2", "L5")] = 1

        y = {("O1", "M1"): 1, ("O1", "M2"): 0, ("O2", "M1"): 0, ("O2", "M2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

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
        params.start_time = self.start_time

        model_dto = OppModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.H = H
        model_dto.K = K
        model_dto.P = P
        model_dto.B = B
        model = OPPModel(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        expected_graph = OPPLocationGraph(
            depot_node="L1",
            final_node="L8",
        )

        for i in location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge("L1", "L2", location_graph.get_distance("L1", "L2"))
        expected_graph.add_edge("L2", "L3", location_graph.get_distance("L2", "L3"))
        expected_graph.add_edge("L3", "L4", location_graph.get_distance("L3", "L4"))
        expected_graph.add_edge("L4", "L8", location_graph.get_distance("L4", "L8"))

        expected_graph.add_edge("L1", "L5", location_graph.get_distance("L1", "L5"))
        expected_graph.add_edge("L5", "L6", location_graph.get_distance("L5", "L6"))
        expected_graph.add_edge("L6", "L7", location_graph.get_distance("L6", "L7"))
        expected_graph.add_edge("L7", "L8", location_graph.get_distance("L7", "L8"))

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "The model did not find a solution.",
        )

        self.assertEqual(output_graph, expected_graph)

    """
        Test 2.3
    """

    def test_two_orders_two_aisles_using_one_aisle(self):
        V, H, K, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        # Both orders must visit first aisle
        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1

        y = {("O1", "M1"): 1, ("O1", "M2"): 0, ("O2", "M1"): 0, ("O2", "M2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

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
        params.start_time = self.start_time

        model_dto = OppModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.H = H
        model_dto.K = K
        model_dto.P = P
        model_dto.B = B
        model = OPPModel(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        expected_graph = OPPLocationGraph(
            depot_node="L1",
            final_node="L8",
        )

        for i in location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge("L1", "L2", location_graph.get_distance("L1", "L2"))
        expected_graph.add_edge("L2", "L3", location_graph.get_distance("L2", "L3"))
        expected_graph.add_edge("L3", "L4", location_graph.get_distance("L3", "L4"))
        expected_graph.add_edge("L4", "L8", location_graph.get_distance("L4", "L8"))

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "The model did not find a solution.",
        )

        self.assertEqual(output_graph, expected_graph)


if __name__ == "__main__":
    # pyscipopt.SCIP_PARAMSETTING_DEFAULT.set("limits/time", 60)
    unittest.main()
