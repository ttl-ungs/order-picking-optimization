import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from models.utils.dat_files_builder import build_dat_files
from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.utils.zpl_utils import extract_active_arcs, solve_zpl
from tests.shared_scenarios.common.six_missions_three_pickers_grid_graph import (
    scenario_six_missions_two_periods_grid_graph,
)


class TestOPPModelZIMPL(OPPTestCaseV4):
    """
    Stress test 03: 12 orders, 6 batches, 3 pickers. 25x25 grid (625 locations).

    Purpose: stress the exact model's scalability (mirrors opp_v3's own
    stress suite / opp_hc_2's picker-aware stress test #03, see
    specs/model_analysis.md sec. 5 for the "exponential blow-up vs. V"
    hypothesis this is meant to check). Reuses opp_hc_2's scenario builder
    (pure graph/order construction, no model coupling) instead of duplicating it.
    """

    def test_625_locations(self):
        opp_location_graph, V, B = scenario_six_missions_two_periods_grid_graph(25, 25)
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

        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        cap_vehicle = 20.0
        cap_n = {n: 10.0 for n in N}
        due_date = {n: 15.0 for n in N}

        P = {"P1", "P2", "P3"}


        S_i = {v: 0.0 for v in V}

        E = set()
        d_ij = {}
        for i in opp_location_graph.get_vertices():
            for j in opp_location_graph.get_vertices():
                if opp_location_graph.has_edge(i, j):
                    E.add((i, j))
                    d_ij[(i, j)] = opp_location_graph.get_distance(i, j)

        scenario_data = {
            "N": N,
            "V": set(opp_location_graph.get_vertices()),
            "P": P,
            "B": B,
            "E": E,
            "depot": opp_location_graph.get_depot(),
            "final": opp_location_graph.get_final(),
            "W_full": w1,
            "W_ea_ta": w2,
            "W_ea": gamma,
            "W_ta": delta,
            "B_time": beta_time,
            "B_setup": beta_setup,
            "B_picking": beta_picking,
            "C_v": cap_vehicle,
            "M": M,
            "C_n": cap_n,
            "Dd": due_date,
            "d_ij": d_ij,
            "S_i": S_i,
            "A_ni": a,
            "Bn": y,
        }

        build_dat_files(DAT_DIR, scenario_data)

        try:
            status, var_values = solve_zpl(
                ZPL_PATH,
                dat_dir=DAT_DIR,
                params={
                    "N": len(N),
                    "B": len(B),
                    "V": len(set(opp_location_graph.get_vertices())),
                    "P": len(P),
                    "W_full": w1,
                    "W_ea_ta": w2,
                    "W_ea": gamma,
                    "W_ta": delta,
                    "B_time": beta_time,
                    "B_setup": beta_setup,
                    "B_picking": beta_picking,
                    "C_v": cap_vehicle,
                    "C_n": cap_n,
                    "Dd": due_date,
                    "d_ij": d_ij,
                    "S_i": S_i,
                    "A_ni": a,
                    "Bn": y,
                },
            )
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")

        self.assertIn(status, ("optimal", "feasible"), "El modelo no encontro una solucion.")


if __name__ == "__main__":
    unittest.main()
