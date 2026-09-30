# Corresponds to test test_case_12.py

import unittest
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
)

from tests.infra.zimpl.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.infra.zimpl.zpl_utils import extract_active_arcs, solve_zpl

from tests.shared_scenarios.functional.one_mission_one_picker_grid_graph_v4 import (
    scenario_one_mission_one_picker_grid_graph,
)


class TestOPPModelZIMPL(OPPTestCaseV4):
    """
    Test 12: 3 orders, 1 mission, 1 picker. Each order is assigned to the same mission and picker. 4x4 graph.
    """

    P, opp_location_graph, V, B = scenario_one_mission_one_picker_grid_graph(4, 4)

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
        A_ni = a if "a" in locals() else {}
        B_nb = y if "y" in locals() else {}
        C_n = cap_n if "cap_n" in locals() else {}
        T_due_n = due_date if "due_date" in locals() else {n: 0.0 for n in N}

        # Tiempo de servicio por defecto (si V2 no lo tenía explícito)
        S_i = {v: 0.0 for v in self.V}

        # Generación de conjunto de Arcos válidos E y distancias D_ij
        E = set()
        D_ij = {}
        for i in self.opp_location_graph.get_vertices():
            for j in self.opp_location_graph.get_vertices():
                if self.opp_location_graph.has_edge(i, j):
                    E.add((i, j))
                    D_ij[(i, j)] = self.opp_location_graph.get_distance(i, j)

        scenario_data = {
            "N": N,
            "V": set(self.opp_location_graph.get_vertices()),
            "P": self.P,
            "B": self.B,
            "E": E,
            "depot": self.opp_location_graph.get_depot(),
            "final": self.opp_location_graph.get_final(),
            "W_c": w1,
            "W_pen": w2,
            "W_e": gamma,
            "W_t": delta,
            "T_travel": 0.5,
            "T_setup": 1.0,
            "T_pick": 1.0,
            "C_v": cap_vehicle,
            "M": 10000.0,
            "C_n": C_n,
            "T_due_n": T_due_n,
            "D_ij": D_ij,
            "S_i": S_i,
            "A_ni": A_ni,
            "B_nb": B_nb,
        }

        build_dat_files(DAT_DIR, scenario_data)

        try:
            status, var_values = solve_zpl(
                ZPL_PATH,
                dat_dir=DAT_DIR,
                params={
                    "N": len(N),
                    "B": len(self.B),
                    "V": len(set(self.opp_location_graph.get_vertices())),
                    "P": len(self.P),
                    "W_c": w1,
                    "W_pen": w2,
                    "W_e": gamma,
                    "W_t": delta,
                    "T_travel": 0.5,
                    "T_setup": 1.0,
                    "T_pick": 1.0,
                    "C_v": cap_vehicle,
                    "C_n": C_n,
                    "T_due_n": T_due_n,
                    "D_ij": D_ij,
                    "S_i": S_i,
                    "A_ni": A_ni,
                    "B_nb": B_nb,
                },
            )
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")

        # Extracción de grafo resultante
        active_arcs = extract_active_arcs(var_values, self.B)
        output_graph = OPPLocationGraph(depot_node=self.opp_location_graph.get_depot(), final_node=self.opp_location_graph.get_final())
        for i in self.opp_location_graph.get_vertices():
            if i not in output_graph.get_vertices():
                output_graph.add_vertex(i, "picking")
        for b, arcs in active_arcs.items():
            for i, j in arcs:
                if not output_graph.has_edge(i, j):
                    output_graph.add_edge(i, j, self.opp_location_graph.get_distance(i, j))

        print("Output graph:", output_graph.to_string())

        self.assertIn(
            status,
            ("optimal", "feasible"),
            "El modelo no encontró una solución.",
        )


if __name__ == "__main__":
    unittest.main()
