import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.infra.cases.exact_model_case import ExactModelTestCase
from tests.infra.zimpl.zpl_utils import extract_active_arcs

from tests.shared_scenarios.functional.scenario_06 import test_two_orders_two_locations

class Case09(ExactModelTestCase):

    """4 vertices, 2 orders, 1 batch. The two orders are linked to two locations."""

    def test_two_orders_two_locations(self):
        """Case 9a."""
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
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
        # Parameter names of the ZIMPL models
        A_ni = a if 'a' in locals() else {} 
        B_nb = y if 'y' in locals() else {}
        C_n = cap_n if 'cap_n' in locals() else {}
        T_due_n = due_date if 'due_date' in locals() else {n: 0.0 for n in N}
        
        # No service time at any location
        S_i = {v: 0.0 for v in V}

        # Arcs (E) and distances (D_ij) of the graph
        E = set()
        D_ij = {}
        for i in location_graph.get_vertices():
            for j in location_graph.get_vertices():
                if location_graph.has_edge(i, j):
                    E.add((i, j))
                    D_ij[(i, j)] = location_graph.get_distance(i, j)

        scenario_data = {
            "N":        N,
            "V":        set(location_graph.get_vertices()),
            "P":        P,
            "B":        B,
            "E":        E,
            "depot":    location_graph.get_depot(),
            "final":    location_graph.get_final(),
            "W_c":   w1,
            "W_pen":  w2,
            "W_e":     gamma,
            "W_t":     delta,
            "T_travel":   0.5,
            "T_setup":  1.0,
            "T_pick":1.0,
            "C_v":      cap_vehicle,
            "M":        10000.0,
            "C_n":      C_n,
            "T_due_n":       T_due_n,
            "D_ij":     D_ij,
            "S_i":      S_i,
            "A_ni":     A_ni,
            "B_nb":       B_nb
        }

        build_dat_files(self.dat_dir, scenario_data)

        try:
            status, var_values = self.solve(params={
                "N": len(N), "B": len(B), "V": len(set(location_graph.get_vertices())), "P": len(P),
                "W_c": w1, "W_pen": w2, "W_e": gamma, "W_t": delta,
                "T_travel": 0.5, "T_setup": 1.0, "T_pick": 1.0,
                "C_v": cap_vehicle, "C_n": C_n, "T_due_n": T_due_n, "D_ij": D_ij,
                "S_i": S_i, "A_ni": A_ni, "B_nb": B_nb
            })
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")

        self.assertIn(status, ("optimal", "feasible"), "El modelo no encontró una solución.")
        
        # Every batch is assigned to exactly one picker
        assignments = {b: 0 for b in B}
        for key, val in var_values.items():
            if key.lower().startswith("x_pb") and val > 0.5:
                for b in B:
                    if b in key: assignments[b] += 1
                    
        for b in B:
            self.assertEqual(assignments[b], 1, f"El lote {b} no fue asignado exactamente a un picker.")
            
        # Graph of the arcs the solution uses
        active_arcs = extract_active_arcs(var_values, B)
        output_graph = OPPLocationGraph(depot_node=location_graph.get_depot(), final_node=location_graph.get_final())
        for i in location_graph.get_vertices():
            if i not in output_graph.get_vertices():
                output_graph.add_vertex(i, "picking")
        for b, arcs in active_arcs.items():
            for i, j in arcs:
                if not output_graph.has_edge(i, j):
                    output_graph.add_edge(i, j, location_graph.get_distance(i, j))

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

        self.assertIn(
            status,
            ("optimal", "feasible"),
            "El modelo no encontró una solución.",
        )

        self.assertEqual(output_graph, expected_graph)
        if len(P) > 1 and len(B) > 1:
            self.assert_workload_balance(var_values, P, B, max_difference=1)
            
        self.assert_no_time_overlap(var_values, P, B)


if __name__ == "__main__":
    unittest.main()
