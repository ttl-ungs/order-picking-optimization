import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from models.utils.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.opp_v4.tests.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.utils.zpl_utils import extract_active_arcs, solve_zpl

from tests.opp_v4.scenarios.normal.one_mission_one_picker_grid_graph import (

class TestOPPModelZIMPL(OPPTestCaseV4):

    """
    Test 15: 3 orders, 1 mission, 1 picker. Each order is assigned to the same mission and picker. 4x4 graph.
    """

    P, x, opp_location_graph, V, B = scenario_one_mission_one_picker_grid_graph(4, 4)

    def get_orders(self):
        orders = {"O1", "O2", "O3"}

        a = {(n, v): 0 for n in orders for v in self.V}
        a[("O1", "V1")] = 1
        a[("O1", "V13")] = 1
        a[("O1", "V10")] = 1

        a[("O2", "V3")] = 1
        a[("O2", "V10")] = 1

        a[("O3", "V1")] = 1
        a[("O3", "V2")] = 1
        a[("O3", "V3")] = 1
        a[("O3", "V7")] = 1
        a[("O3", "V9")] = 1

        y = {(n, b): 0 for n in orders for b in self.B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B1")] = 1

        return orders, a, y

    def get_output_graph(self):
        expected_graph = OPPLocationGraph(
            depot_node="V1",
            final_node="V16",
        )

        for i in self.opp_location_graph.get_vertices():
            if i not in expected_graph.get_vertices():
                expected_graph.add_vertex(i, "picking")

        expected_graph.add_edge(
            "V1", "V2", self.opp_location_graph.get_distance("V1", "V2")
        )
        expected_graph.add_edge(
            "V2", "V3", self.opp_location_graph.get_distance("V2", "V3")
        )
        expected_graph.add_edge(
            "V3", "V7", self.opp_location_graph.get_distance("V3", "V7")
        )
        expected_graph.add_edge(
            "V7", "V11", self.opp_location_graph.get_distance("V7", "V11")
        )
        expected_graph.add_edge(
            "V11", "V10", self.opp_location_graph.get_distance("V11", "V10")
        )
        expected_graph.add_edge(
            "V10", "V9", self.opp_location_graph.get_distance("V10", "V9")
        )
        expected_graph.add_edge(
            "V9", "V13", self.opp_location_graph.get_distance("V9", "V13")
        )
        expected_graph.add_edge(
            "V13", "V14", self.opp_location_graph.get_distance("V13", "V14")
        )
        expected_graph.add_edge(
            "V14", "V15", self.opp_location_graph.get_distance("V14", "V15")
        )
        expected_graph.add_edge(
            "V15", "V16", self.opp_location_graph.get_distance("V15", "V16")
        )

        return expected_graph

    def test_3_orders_1_mission_1_picker(self):
        N, a, y = self.get_orders()

        cap_vehicle = 60
        cap_n = {"O1": 30, "O2": 10, "O3": 15}
        due_date = {"O1": 10, "O2": 5, "O3": 8}

        w1 = 9.0  # cumplimiento peso alto
        w2 = 1.0  # demoras y adelanto peso bajo
        gamma = 1.0  # peso del adelanto bajo
        delta = 1.0  # peso de demora bajo

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0
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
