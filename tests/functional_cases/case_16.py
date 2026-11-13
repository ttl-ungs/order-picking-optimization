import unittest
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)

from tests.infra.zimpl.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.infra.cases.exact_model_case import ExactModelTestCase
from tests.infra.zimpl.zpl_utils import extract_active_arcs

from tests.shared_scenarios.functional.three_missions_two_pickers_grid_graph import (
    scenario_three_missions_two_pickers_two_periods_grid_graph,
)


class Case16(ExactModelTestCase):
    """
    Test 13: 6 orders, 3 missions, 2 pickers on a 4x4 grid with transversal aisles.
    Each order visits more than one location.
    """

    P, opp_location_graph, V, B = (
        scenario_three_missions_two_pickers_two_periods_grid_graph(4, 4)
    )

    def get_orders(self):
        orders = {"O1", "O2", "O3", "O4", "O5", "O6"}

        a = {(n, v): 0 for n in orders for v in self.V}

        # Each order requires at least two locations.
        a[("O1", "V2")] = 1
        a[("O1", "V6")] = 1

        a[("O2", "V2")] = 1
        a[("O2", "V7")] = 1

        a[("O3", "V5")] = 1
        a[("O3", "V9")] = 1

        a[("O4", "V6")] = 1
        a[("O4", "V14")] = 1

        a[("O5", "V4")] = 1
        a[("O5", "V8")] = 1

        a[("O6", "V11")] = 1
        a[("O6", "V14")] = 1

        y = {(n, b): 0 for n in orders for b in self.B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B2")] = 1
        y[("O4", "B2")] = 1
        y[("O5", "B3")] = 1
        y[("O6", "B3")] = 1

        return orders, a, y

    def test_6_orders_3_missions_2_pickers(self):
        """Case 16a."""
        N, a, y = self.get_orders()

        cap_vehicle = 25
        cap_n = {"O1": 10, "O2": 10, "O3": 10, "O4": 10, "O5": 10, "O6": 10}
        due_date = {"O1": 30, "O2": 30, "O3": 30, "O4": 30, "O5": 30, "O6": 30}

        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

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

        build_dat_files(self.dat_dir, scenario_data)

        try:
            status, var_values = self.solve(
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
