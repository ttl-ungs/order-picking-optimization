import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.opp_location_graph import OPPLocationGraph
from utils.output_handler import OutputHandler
from models.opp_model import OPPModel

from tests.scenarios.scenario_5 import bidirectional_edges

class TestOPPModel(unittest.TestCase):

    """
        Test 5: Add an extra vertex to avoid cicle. 6 vertex, 1 mission, 3 orders, 2 pickers.
        Purpose: Try to find an optimal solution for Test 4, with and extra vertex that avoid 
        a cicle in the graph. 
        Conclusion: Optimal solution found.
    """
        
    def test_repeated_picking_locations(self):
        V, H, K, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            bidirectional_edges()
        )

        N = {"O1", "O2", "O3"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1

        y = {("O1", "M1"): 1, 
             ("O2", "M1"): 1,
             ("O3", "M1"): 1}
        
        cap_n = {"O1": 3.0, "O2": 3.0, "O3": 15.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0, "O3": 15.0}

        model = OPPModel(N, location_graph, H, K, P, B)
        output_handler = OutputHandler()
        model.attach(output_handler)

        try:
            result, output_graph = model.solve(
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

        self.assertEqual(output_graph, expected_graph)

if __name__ == "__main__":
    # pyscipopt.SCIP_PARAMSETTING_DEFAULT.set("limits/time", 60)
    unittest.main()
