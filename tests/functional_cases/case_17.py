import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.infra.cases.exact_model_case import ExactModelTestCase
from tests.infra.zimpl.zpl_utils import extract_active_arcs

from tests.shared_scenarios.functional.scenario_17 import branched_single_mission_route

class Case17(ExactModelTestCase):

    def test_branched_single_mission_route(self):
        """Case 17a."""
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
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
        # Adaptación de variables para el formato ZIMPL V4
        A_ni = a if 'a' in locals() else {} 
        B_nb = y if 'y' in locals() else {}
        C_n = cap_n if 'cap_n' in locals() else {}
        T_due_n = due_date if 'due_date' in locals() else {n: 0.0 for n in N}
        
        # Tiempo de servicio por defecto (si V2 no lo tenía explícito)
        S_i = {v: 0.0 for v in V}

        # Generación de conjunto de Arcos válidos E y distancias D_ij
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
        
        # Aserción Genérica de V4: Cada lote se asigna a 1 picker
        assignments = {b: 0 for b in B}
        for key, val in var_values.items():
            if key.lower().startswith("x_pb") and val > 0.5:
                for b in B:
                    if b in key: assignments[b] += 1
                    
        for b in B:
            self.assertEqual(assignments[b], 1, f"El lote {b} no fue asignado exactamente a un picker.")
            
        # Extracción de grafo resultante
        active_arcs = extract_active_arcs(var_values, B)
        output_graph = OPPLocationGraph(depot_node=location_graph.get_depot(), final_node=location_graph.get_final())
        for i in location_graph.get_vertices():
            if i not in output_graph.get_vertices():
                output_graph.add_vertex(i, "picking")
        for b, arcs in active_arcs.items():
            for i, j in arcs:
                if not output_graph.has_edge(i, j):
                    output_graph.add_edge(i, j, location_graph.get_distance(i, j))

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

        self.assertIn(
            status,
            ("optimal", "feasible"),
            "El modelo no encontró una solución.",
        )
        
        self.assertEqual(output_graph, expected_graph)
        # --- NUEVAS VALIDACIONES INTELIGENTES V4 ---
        if len(P) > 1 and len(B) > 1:
            self.assert_workload_balance(var_values, P, B, max_difference=1)
            
        self.assert_no_time_overlap(var_values, P, B)


if __name__ == "__main__":
    unittest.main()
