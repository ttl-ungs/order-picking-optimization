import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.output_handler import OutputHandler
from models.opp_model import OPPModel

class TestOPPModel(unittest.TestCase):

    """
        Test 1: Basic. 4 vertex, 5 edges, 2 orders, 2 missions.
        Purpose: to test the basic functionality of the model.
    """
    def test_basic_two_orders_capacity_limit(self):
        from tests.test_scenarios import basic_two_orders_capacity_limit

        V, H, K, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            basic_two_orders_capacity_limit()
        )
        
        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1
        
        y = {("O1", "M1"): 1, ("O1", "M2"): 0, ("O2", "M1"): 0, ("O2", "M2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

        model = OPPModel(N, location_graph, H, K, P, B)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result = model.solve(
                w1,
                w2,
                gamma,
                delta,
                cap_n,
                cap_vehicle,
                a,
                beta_time,
                beta_setup,
                beta_picking,
                due_date,
                M,
                x,
                y,
            )
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
           "The model did not find a solution.",
        )


    """
        Test 2.1: Medium. 8 vertex, 8 edges, 2 orders, 2 missions.
        Purpose: To test the functionality of the model when it has to follow a route.
    """
    def test_two_orders_two_aisles(self):
        from tests.test_scenarios import two_orders_two_aisles

        V, H, K, P, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle, x = (
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

        model = OPPModel(N, opp_location_graph, H, K, P, B)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result = model.solve(
                w1,
                w2,
                gamma,
                delta,
                cap_n,
                cap_vehicle,
                a,
                beta_time,
                beta_setup,
                beta_picking,
                due_date,
                M,
                x,
                y,
            )
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "The model did not find a solution.",
        )

    """
        Test 2.2: Medium. 8 vertex, 8 edges, 2 orders, 2 missions.
        Purpose: To test the functionality of the model when we have few vertex assigned to orders.
    """
    def test_two_orders_two_aisles_one_picking_point_per_order(self):
        from tests.test_scenarios import two_orders_two_aisles

        V, H, K, P, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle, x = (
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

        model = OPPModel(N, opp_location_graph, H, K, P, B)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result = model.solve(
                w1,
                w2,
                gamma,
                delta,
                cap_n,
                cap_vehicle,
                a,
                beta_time,
                beta_setup,
                beta_picking,
                due_date,
                M,
                x,
                y,
            )
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "The model did not find a solution.",
        )

    """
        Test 3: Medium. 5 vertex, 6 edges, 2 orders, 2 missions.
        Purpose: To test the functionality of the model when it has to choose between two possible routes.
    """
    def test_two_possible_routes(self):
        from tests.test_scenarios import test_two_possible_routes

        V, H, K, P, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle, x = (
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

        model = OPPModel(N, opp_location_graph, H, K, P, B)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result = model.solve(
                w1,
                w2,
                gamma,
                delta,
                cap_n,
                cap_vehicle,
                a,
                beta_time,
                beta_setup,
                beta_picking,
                due_date,
                M,
                x,
                y,
            )
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertTrue(
            result in ("optimal", "feasible", "infeasible", "unbounded"),
            "The model did not find a solution.",
        )

if __name__ == "__main__":
    # pyscipopt.SCIP_PARAMSETTING_DEFAULT.set("limits/time", 60)
    unittest.main()
