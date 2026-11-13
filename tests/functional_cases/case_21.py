import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from tests.infra.cases.exact_model_case import ExactModelTestCase
from tests.shared_scenarios.functional.scenario_13_v4 import (
    bridge_graph_disconnected,
    bridge_graph_two_pickers_four_batches,
)
from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.infra.zimpl.zpl_utils import extract_active_arcs


class Case21(ExactModelTestCase):
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

        build_dat_files(self.dat_dir, scenario_data)
        status, var_values = self.solve(
            params={"N": len(N), "B": len(B), "V": len(V), "P": len(P)},
        )
        return status, var_values, location_graph, B, V

    def test_bridge_disconnected_required_location(self):
        """Case 21a."""
        V, _, B, _, _, _, _, _, _, _ = bridge_graph_disconnected()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}
        y = {(n, b): 0 for n in N for b in B}

        # Test puente roto -> debe fallar
        cap_n = {n: 2.0 for n in N}
        status, _, _, _, _ = self._solve_bridge_zpl(N, a, y, cap_n, disconnected=True)
        self.assertEqual(status, "infeasible")


if __name__ == "__main__":
    unittest.main()
