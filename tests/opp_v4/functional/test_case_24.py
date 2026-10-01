import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.shared_scenarios.functional.scenario_13_v4 import (
    bridge_graph_disconnected,
    bridge_graph_two_pickers_four_batches,
)
from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.infra.zimpl.zpl_utils import extract_active_arcs, solve_zpl


class TestOPPModelBridgeZIMPL(OPPTestCaseV4):
    def _solve_bridge_zpl(
        self,
        N,
        a,
        y,
        cap_n,
        disconnected=False,
        due_date_override=None,
        beta_picking_override=1.0,
    ):

        if disconnected:
            V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, _ = (
                bridge_graph_disconnected()
            )
        else:
            V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, _ = (
                bridge_graph_two_pickers_four_batches()
            )

        due_date_by_order = self.normalize_due_dates(N, due_date_override)
        E = set()
        D_ij = {}
        for i in location_graph.get_vertices():
            for j in location_graph.get_vertices():
                if location_graph.has_edge(i, j):
                    E.add((i, j))
                    D_ij[(i, j)] = location_graph.get_distance(i, j)

        scenario_data = {
            "N": N,
            "V": set(location_graph.get_vertices()),
            "P": P,
            "B": B,
            "E": E,
            "depot": location_graph.get_depot(),
            "final": location_graph.get_final(),
            "W_c": w1,
            "W_pen": w2,
            "W_e": gamma,
            "W_t": delta,
            "T_travel": 0.5,
            "T_setup": 1.0,
            "T_pick": beta_picking_override,
            "C_v": cap_vehicle,
            "M": 10000.0,
            "C_n": cap_n,
            "T_due_n": due_date_by_order,
            "D_ij": D_ij,
            "S_i": {v: 0.0 for v in V},
            "A_ni": a,
            "B_nb": y,
        }

        build_dat_files(DAT_DIR, scenario_data)
        status, var_values = solve_zpl(
            ZPL_PATH,
            dat_dir=DAT_DIR,
            params={
                "N": len(N),
                "B": len(B),
                "V": len(V),
                "P": len(P),
                "C_n": cap_n,
                "B_nb": y,
                "C_v": cap_vehicle,
            },
        )
        return status, var_values, location_graph, B, V

    def test_bridge_disconnected_required_location_with_capacities(self):
        V, _, B, _, _, _, _, _, _, _ = bridge_graph_disconnected()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}
        y = {(n, b): 0 for n in N for b in B}

        # Test puente roto -> debe fallar
        cap_n = {n: 2.0 for n in N}
        status, _, _, _, _ = self._solve_bridge_zpl(N, a, y, cap_n, disconnected=True)
        self.assertEqual(status, "infeasible")

    def test_bridge_shared_locations_across_batches(self):
        V, _, B, _, _, _, _, _, _, _ = bridge_graph_two_pickers_four_batches()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L8")] = 1
        a[("O3", "L9")] = 1
        a[("O4", "L3")] = 1
        a[("O5", "L10")] = 1
        a[("O6", "L11")] = 1
        a[("O7", "L4")] = 1
        a[("O8", "L8")] = 1
        a[("O9", "L10")] = 1
        a[("O10", "L5")] = 1
        a[("O11", "L9")] = 1
        a[("O12", "L11")] = 1

        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B1")] = 1
        y[("O4", "B2")] = 1
        y[("O5", "B2")] = 1
        y[("O6", "B2")] = 1
        y[("O7", "B3")] = 1
        y[("O8", "B3")] = 1
        y[("O9", "B3")] = 1
        y[("O10", "B4")] = 1
        y[("O11", "B4")] = 1
        y[("O12", "B4")] = 1

        cap_n = {n: 2.0 for n in N}
        status, _, _, _, _ = self._solve_bridge_zpl(N, a, y, cap_n)
        self.assertIn(status, ("optimal", "feasible"))

    def test_bridge_tardiness_beta_picking(self):
        V, _, B, _, _, _, _, _, _, _ = bridge_graph_two_pickers_four_batches()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L8")] = 1
        a[("O3", "L9")] = 1
        a[("O4", "L3")] = 1
        a[("O5", "L10")] = 1
        a[("O6", "L11")] = 1
        a[("O7", "L4")] = 1
        a[("O8", "L8")] = 1
        a[("O9", "L10")] = 1
        a[("O10", "L5")] = 1
        a[("O11", "L9")] = 1
        a[("O12", "L11")] = 1

        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B1")] = 1
        y[("O4", "B2")] = 1
        y[("O5", "B2")] = 1
        y[("O6", "B2")] = 1
        y[("O7", "B3")] = 1
        y[("O8", "B3")] = 1
        y[("O9", "B3")] = 1
        y[("O10", "B4")] = 1
        y[("O11", "B4")] = 1
        y[("O12", "B4")] = 1

        cap_n = {n: 2.0 for n in N}

        status_fast, _, _, _, _ = self._solve_bridge_zpl(
            N, a, y, cap_n, due_date_override=10.0, beta_picking_override=0.5,
        )
        self.assertIn(status_fast, ("optimal", "feasible"))

        status_slow, _, _, _, _ = self._solve_bridge_zpl(
            N, a, y, cap_n, due_date_override=10.0, beta_picking_override=2.0,
        )
        self.assertIn(status_slow, ("optimal", "feasible"))

    def test_bridge_earliness_order_size(self):
        V, _, B, _, _, _, _, _, _, _ = bridge_graph_two_pickers_four_batches()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L8")] = 1
        a[("O3", "L9")] = 1
        a[("O4", "L3")] = 1
        a[("O5", "L10")] = 1
        a[("O6", "L11")] = 1
        a[("O7", "L4")] = 1
        a[("O8", "L8")] = 1
        a[("O9", "L10")] = 1
        a[("O10", "L5")] = 1
        a[("O11", "L9")] = 1
        a[("O12", "L11")] = 1

        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B1")] = 1
        y[("O4", "B2")] = 1
        y[("O5", "B2")] = 1
        y[("O6", "B2")] = 1
        y[("O7", "B3")] = 1
        y[("O8", "B3")] = 1
        y[("O9", "B3")] = 1
        y[("O10", "B4")] = 1
        y[("O11", "B4")] = 1
        y[("O12", "B4")] = 1

        cap_n_small = {n: 1.0 for n in N}
        status_small, _, _, _, _ = self._solve_bridge_zpl(
            N, a, y, cap_n_small, due_date_override=5000.0,
        )
        self.assertIn(status_small, ("optimal", "feasible"))

        cap_n_large = {n: 2.0 for n in N}
        status_large, _, _, _, _ = self._solve_bridge_zpl(
            N, a, y, cap_n_large, due_date_override=5000.0,
        )
        self.assertIn(status_large, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
