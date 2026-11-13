import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.infra.cases.exact_model_case import ExactModelTestCase

from tests.shared_scenarios.functional.scenario_01_v4 import basic_two_orders_capacity_limit


class Case33(ExactModelTestCase):
    """Ported from opp_hc_2's test #29: service time (S_i) set to zero,
    one, or a mix across vertices -- must not crash and must remain
    feasible either way."""

    def _solve(self, S_i):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, _ = (
            basic_two_orders_capacity_limit()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1

        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}
        due_date = {"O1": 15.0, "O2": 15.0}

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
            "T_pick": 1.0,
            "C_v": cap_vehicle,
            "M": 1000.0,
            "C_n": cap_n,
            "T_due_n": due_date,
            "D_ij": D_ij,
            "S_i": S_i,
            "A_ni": a,
            "B_nb": y,
        }

        build_dat_files(self.dat_dir, scenario_data)

        try:
            status, _ = self.solve(
                params={
                    "N": len(N), "B": len(B), "V": len(V), "P": len(P),
                    "C_n": cap_n, "B_nb": y, "C_v": cap_vehicle,
                },
            )
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")

        self.assertIn(status, ("optimal", "feasible"))
        return status

    def test_service_time_zero(self):
        """Case 33c."""
        V, _, _, _, _, _, _, _, _, _ = basic_two_orders_capacity_limit()
        self._solve({v: 0.0 for v in V})

    def test_service_time_one(self):
        """Case 33b."""
        V, _, _, _, _, _, _, _, _, _ = basic_two_orders_capacity_limit()
        self._solve({v: 1.0 for v in V})

    def test_service_time_mixed(self):
        """Case 33a."""
        V, _, _, _, _, _, _, _, _, _ = basic_two_orders_capacity_limit()
        s = {v: 0.5 + (i % 3) * 0.5 for i, v in enumerate(sorted(V))}
        self._solve(s)


if __name__ == "__main__":
    unittest.main()
