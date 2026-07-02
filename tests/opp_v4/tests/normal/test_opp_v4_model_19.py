import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from models.utils.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.opp_v4.tests.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.utils.zpl_utils import extract_active_arcs, solve_zpl

from tests.opp_v4.scenarios.normal.scenario_19 import longer_single_mission_route

class TestOPPModelZIMPL(OPPTestCaseV4):

    def _solve_longer_route(
        self,
        due_date,
        w1_override=None,
        w2_override=None,
        gamma_override=None,
        delta_override=None,
        duplicate_location=False,
    ):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            longer_single_mission_route()
        )

        w1, w2, gamma, delta = self.apply_weight_overrides(
            w1,
            w2,
            gamma,
            delta,
            w1_override,
            w2_override,
            gamma_override,
            delta_override,
        )

        N = {"O1", "O2", "O3", "O4", "O5", "O6"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        if duplicate_location:
            a[("O2", "L2")] = 1
        else:
            a[("O2", "L3")] = 1
        a[("O3", "L4")] = 1
        a[("O4", "L5")] = 1
        a[("O5", "L6")] = 1
        a[("O6", "L7")] = 1

        y = {
            ("O1", "B1"): 1,
            ("O2", "B1"): 1,
            ("O3", "B1"): 1,
            ("O4", "B1"): 1,
            ("O5", "B1"): 1,
            ("O6", "B1"): 1,
        }
        cap_n = {n: 2.0 for n in N}

        due_date_by_order = self.normalize_due_dates(N, due_date)
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
