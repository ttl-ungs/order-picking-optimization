# Corresponds to test test_opp_v2_model_04.py

import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from models.utils.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.utils.zpl_utils import extract_active_arcs, solve_zpl

from tests.shared_scenarios.normal.scenario_04_v4 import bidirectional_edges

class TestOPPModelZIMPL(OPPTestCaseV4):

    """
    Test 4: 5 vertex, 2 orders, 1 batch.
    Purpose: Force the model to generate a cycle.
    Status: Not feasible solution found.
    """

    def test_repeated_picking_locations(self):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            bidirectional_edges()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1

        y = {("O1", "B1"): 1, ("O2", "B1"): 0}
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

        self.assertIn(status, ("infeasible",), "El modelo encontró una solución cuando se esperaba que fuera infactible.")


if __name__ == "__main__":
    unittest.main()
