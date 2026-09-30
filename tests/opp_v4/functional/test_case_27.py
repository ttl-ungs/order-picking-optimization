import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.infra.zimpl.zpl_utils import solve_zpl

from tests.shared_scenarios.functional.three_missions_two_pickers_grid_graph_v4 import (
    scenario_three_missions_two_pickers_two_periods_grid_graph,
)


class TestEmptyBatchZIMPL(OPPTestCaseV4):
    """Ported from opp_hc_2's test #25 (test_one_empty_batch_allowed):
    a setup with one intentionally empty batch among others."""

    def test_one_empty_batch_allowed(self):
        P, opp_location_graph, V, B = (
            scenario_three_missions_two_pickers_two_periods_grid_graph(5, 5)
        )

        N = {f"O{i}" for i in range(1, 7)}
        a = {(n, v): 0 for n in N for v in V}
        assigns = list(zip(sorted(N), ["V2", "V3", "V6", "V7", "V10", "V11"]))
        for n, v in assigns:
            a[(n, v)] = 1

        y = {(n, b): 0 for n in N for b in B}
        batches = sorted(B)
        for idx, n in enumerate(sorted(N)):
            y[(n, batches[idx // 2])] = 1  # last batch is left empty on purpose

        cap_vehicle = 50.0
        cap_n = {n: 5.0 for n in N}
        due_date = {n: 100.0 for n in N}

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
            "W_c": 1.0,
            "W_pen": 1.0,
            "W_e": 1.0,
            "W_t": 1.0,
            "T_travel": 0.5,
            "T_setup": 1.0,
            "T_pick": 1.0,
            "C_v": cap_vehicle,
            "M": 1000.0,
            "C_n": cap_n,
            "T_due_n": due_date,
            "D_ij": D_ij,
            "S_i": {v: 0.0 for v in V},
            "A_ni": a,
            "B_nb": y,
        }

        build_dat_files(DAT_DIR, scenario_data)

        try:
            status, _ = solve_zpl(
                ZPL_PATH,
                dat_dir=DAT_DIR,
                params={
                    "N": len(N), "B": len(B), "V": len(V), "P": len(P),
                    "C_n": cap_n, "B_nb": y, "C_v": cap_vehicle,
                },
            )
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")

        self.assertIn(status, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
