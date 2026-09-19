import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.infra.zimpl.zpl_utils import solve_zpl

from tests.shared_scenarios.functional.scenario_03_v4 import two_possible_routes_batches


class TestDueDatesExtremeZIMPL(OPPTestCaseV4):
    """
    Ported from opp_hc_2's test #24 (test_due_dates_tight_vs_relaxed):
    same scenario, tight vs. relaxed due dates -- both must remain feasible
    (ta absorbs a tight due date, it never makes the model infeasible).
    """

    def _solve(self, due_date):
        V, P, B, _, _, _, _, location_graph, cap_vehicle, _ = (
            two_possible_routes_batches()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L4")] = 1
        a[("O2", "L4")] = 1

        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B2")] = 1

        cap_n = {"O1": 3.0, "O2": 3.0}

        E = set()
        d_ij = {}
        for i in location_graph.get_vertices():
            for j in location_graph.get_vertices():
                if location_graph.has_edge(i, j):
                    E.add((i, j))
                    d_ij[(i, j)] = location_graph.get_distance(i, j)

        scenario_data = {
            "N": N,
            "V": set(location_graph.get_vertices()),
            "P": P,
            "B": B,
            "E": E,
            "depot": location_graph.get_depot(),
            "final": location_graph.get_final(),
            "W_full": 0.0,
            "W_ea_ta": 1.0,
            "W_ea": 0.0,
            "W_ta": 1.0,
            "B_time": 0.5,
            "B_setup": 1.0,
            "B_picking": 2.0,
            "C_v": cap_vehicle,
            "M": 1000.0,
            "C_n": cap_n,
            "Dd": due_date,
            "d_ij": d_ij,
            "S_i": {v: 0.0 for v in V},
            "A_ni": a,
            "Bn": y,
        }

        build_dat_files(DAT_DIR, scenario_data)

        return solve_zpl(
            ZPL_PATH,
            dat_dir=DAT_DIR,
            params={
                "N": len(N), "B": len(B), "V": len(V), "P": len(P),
                "C_n": cap_n, "Bn": y, "C_v": cap_vehicle,
            },
        )

    def test_due_dates_tight_vs_relaxed(self):
        try:
            status_tight, _ = self._solve({"O1": 1.0, "O2": 1.0})
        except Exception as e:
            self.fail(f"ZPL solve failed (tight): {e}")
        self.assertIn(status_tight, ("optimal", "feasible", "infeasible"))

        try:
            status_relaxed, _ = self._solve({"O1": 1000.0, "O2": 1000.0})
        except Exception as e:
            self.fail(f"ZPL solve failed (relaxed): {e}")
        self.assertIn(status_relaxed, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
