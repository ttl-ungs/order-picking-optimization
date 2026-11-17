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

from tests.shared_scenarios.common.six_missions_three_pickers_grid_graph import (
    scenario_six_missions_three_pickers_one_period_grid_graph,
)


class Case14(ExactModelTestCase):
    """12 orders, 6 batches, 3 pickers: two batches per picker and two orders
    per batch. One period per picker."""

    def test_one_period_two_orders_per_vehicle(self):
        """Case 14a."""
        P, x, opp_location_graph, V, B = (
            scenario_six_missions_three_pickers_one_period_grid_graph()
        )
        N = {"O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8", "O9", "O10", "O11", "O12"}

        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "V6")] = 1
        a[("O2", "V11")] = 1
        a[("O3", "V7")] = 1
        a[("O4", "V12")] = 1
        a[("O5", "V3")] = 1
        a[("O6", "V8")] = 1
        a[("O7", "V5")] = 1
        a[("O8", "V10")] = 1
        a[("O9", "V10")] = 1
        a[("O10", "V15")] = 1
        a[("O11", "V9")] = 1
        a[("O12", "V14")] = 1

        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B2")] = 1
        y[("O4", "B2")] = 1
        y[("O5", "B3")] = 1
        y[("O6", "B3")] = 1
        y[("O7", "B4")] = 1
        y[("O8", "B4")] = 1
        y[("O9", "B5")] = 1
        y[("O10", "B5")] = 1
        y[("O11", "B6")] = 1
        y[("O12", "B6")] = 1

        w1 = 9.0  # completion time: high weight
        w2 = 1.0  # penalties: low weight
        gamma = 1.0  # earliness
        delta = 1.0  # tardiness

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        cap_vehicle = 20.0  # Two orders per vehicle
        cap_n = {
            "O1": 10.0,
            "O2": 10.0,
            "O3": 10.0,
            "O4": 10.0,
            "O5": 10.0,
            "O6": 10.0,
            "O7": 10.0,
            "O8": 10.0,
            "O9": 10.0,
            "O10": 10.0,
            "O11": 10.0,
            "O12": 10.0,
        }

        due_date = {
            "O1": 15.0,
            "O2": 15.0,
            "O3": 15.0,
            "O4": 15.0,
            "O5": 15.0,
            "O6": 15.0,
            "O7": 15.0,
            "O8": 15.0,
            "O9": 15.0,
            "O10": 15.0,
            "O11": 15.0,
            "O12": 15.0,
        }
        # Parameter names of the ZIMPL models
        A_ni = a if "a" in locals() else {}
        B_nb = y if "y" in locals() else {}
        C_n = cap_n if "cap_n" in locals() else {}
        T_due_n = due_date if "due_date" in locals() else {n: 0.0 for n in N}

        # No service time at any location
        S_i = {v: 0.0 for v in V}

        # Arcs (E) and distances (D_ij) of the graph
        E = set()
        D_ij = {}
        for i in opp_location_graph.get_vertices():
            for j in opp_location_graph.get_vertices():
                if opp_location_graph.has_edge(i, j):
                    E.add((i, j))
                    D_ij[(i, j)] = opp_location_graph.get_distance(i, j)

        scenario_data = {
            "N": N,
            "V": set(opp_location_graph.get_vertices()),
            "P": P,
            "B": B,
            "E": E,
            "depot": opp_location_graph.get_depot(),
            "final": opp_location_graph.get_final(),
            "W_c": w1,
            "W_pen": w2,
            "W_e": gamma,
            "W_t": delta,
            "T_travel": 0.5,
            "T_setup": 1.0,
            "T_pick": 1.0,
            "C_v": cap_vehicle,
            "M": 1000.0,
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
                    "B": len(B),
                    "V": len(set(opp_location_graph.get_vertices())),
                    "P": len(P),
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

        self.assertIn(
            status,
            ("optimal", "feasible"),
            "El modelo no encontró una solución.",
        )

        if len(P) > 1 and len(B) > 1:
            self.assert_workload_balance(var_values, P, B, max_difference=1)

        self.assert_no_time_overlap(var_values, P, B)


if __name__ == "__main__":
    unittest.main()
