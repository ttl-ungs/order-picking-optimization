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

from tests.shared_scenarios.functional.one_mission_one_picker_grid_graph import (
    scenario_one_mission_one_picker_grid_graph,
)


class Case15(ExactModelTestCase):
    """3 orders in one batch for one picker, on a 4x4 graph."""

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
        """Case 15a."""
        N, a, y = self.get_orders()

        cap_vehicle = 60
        cap_n = {"O1": 30, "O2": 10, "O3": 15}
        due_date = {"O1": 10, "O2": 5, "O3": 8}

        w1 = 9.0  # completion time: high weight
        w2 = 1.0  # penalties: low weight
        gamma = 1.0  # earliness
        delta = 1.0  # tardiness

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0
        # Parameter names of the ZIMPL models
        A_ni = a if "a" in locals() else {}
        B_nb = y if "y" in locals() else {}
        C_n = cap_n if "cap_n" in locals() else {}
        T_due_n = due_date if "due_date" in locals() else {n: 0.0 for n in N}

        # No service time at any location
        S_i = {v: 0.0 for v in self.V}

        # Arcs (E) and distances (D_ij) of the graph
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

        # Graph of the arcs the solution uses
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
