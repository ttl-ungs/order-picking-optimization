import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.support.dat_files_builder import build_dat_files
from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.support.zpl_utils import extract_active_arcs, solve_zpl
from tests.shared_scenarios.stress.scenario_custom_setup import scenario_custom_setup


class TestOPPModelZIMPL(OPPTestCaseV4):
    """
    Stress test 04: 4 orders per batch. 25 batches, 100 orders. 10x10 grid.

    Purpose: stress the exact model's scalability (mirrors opp_v3's own
    stress suite / opp_hc_2's picker-aware stress test #04, see
    docs/specs/model_analysis.md sec. 5 for the "exponential blow-up vs. V"
    hypothesis this is meant to check). Reuses opp_hc_2's scenario builder
    (pure graph/order construction, no model coupling) instead of duplicating it.
    """

    def test_4_orders_per_batch(self):
        opp_location_graph, V, B, N, y, a = scenario_custom_setup(
            25, 100, 10, 10
        )

        cap_n = {n: 10.0 for n in N}
        due_date = {n: 30.0 for n in N}

        cap_vehicle = 40.0
        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        P = {"P1"}

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
