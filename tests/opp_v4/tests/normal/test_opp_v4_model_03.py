import unittest
from models.utils.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.utils.zpl_utils import extract_active_arcs, solve_zpl

from tests.opp_v4.scenarios.normal.scenario_03 import two_possible_routes_batches

class TestOPPModelZIMPL(OPPTestCase):

    """
    Test 3: Medium. 5 vertex, 6 edges, 2 orders, 2 batches.
    Purpose: To test the functionality of the model when it has to choose between two possible routes.
    """

    def test_two_possible_routes(self):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            two_possible_routes_batches()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        # Orders must visit location 4
        a[("O1", "L4")] = 1
        a[("O2", "L4")] = 1

        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}
        # Adaptación de variables para el formato ZIMPL V4
        A_ni = a if 'a' in locals() else {} 
        Bn = y if 'y' in locals() else {}
        C_n = cap_n if 'cap_n' in locals() else {}
        Dd = due_date if 'due_date' in locals() else {n: 0.0 for n in N}
        
        # Tiempo de servicio por defecto (si V2 no lo tenía explícito)
        S_i = {v: 0.0 for v in V}

        # Generación de conjunto de Arcos válidos E y distancias d_ij
        E = set()
        d_ij = {}
        for i in location_graph.get_vertices():
            for j in location_graph.get_vertices():
                if location_graph.has_edge(i, j):
                    E.add((i, j))
                    d_ij[(i, j)] = location_graph.get_distance(i, j)

        scenario_data = {
            "N":        N,
            "V":        set(location_graph.get_vertices()),
            "P":        P,
            "B":        B,
            "E":        E,
            "depot":    location_graph.get_depot(),
            "final":    location_graph.get_final(),
            "W_full":   w1,
            "W_ea_ta":  w2,
            "W_ea":     gamma,
            "W_ta":     delta,
            "B_time":   0.5,
            "B_setup":  1.0,
            "B_picking":1.0,
            "C_v":      cap_vehicle,
            "M":        10000.0,
            "C_n":      C_n,
            "Dd":       Dd,
            "d_ij":     d_ij,
            "S_i":      S_i,
            "A_ni":     A_ni,
            "Bn":       Bn
        }

        build_dat_files(DAT_DIR, scenario_data)

        try:
            status, var_values = solve_zpl(ZPL_PATH, dat_dir=DAT_DIR, params={
                "N": len(N), "B": len(B), "V": len(set(location_graph.get_vertices())), "P": len(P),
                "W_full": w1, "W_ea_ta": w2, "W_ea": gamma, "W_ta": delta,
                "B_time": 0.5, "B_setup": 1.0, "B_picking": 1.0,
                "C_v": cap_vehicle, "C_n": C_n, "Dd": Dd, "d_ij": d_ij,
                "S_i": S_i, "A_ni": A_ni, "Bn": Bn
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
            "The model did not find a solution.",
        )

        
        self.assertEqual(output_graph, expected_graph)

if __name__ == "__main__":
    unittest.main()
