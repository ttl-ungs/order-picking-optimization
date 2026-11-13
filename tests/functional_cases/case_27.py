import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.infra.cases.exact_model_case import ExactModelTestCase

from tests.shared_scenarios.functional.scenario_01 import basic_two_orders_capacity_limit


class Case27(ExactModelTestCase):
    """
    Ported from opp_hc_2's test #05 (test_basic_two_orders_with_different_weights):
    same scenario as test_case_01, different objective weights.
    """

    def test_basic_two_orders_with_different_weights(self):
        """Case 27a."""
        V, P, B, _, _, _, _, location_graph, cap_vehicle, _ = (
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
            "W_c": 2.0,  # Higher weight on completion time
            "W_pen": 0.5,  # Lower weight on penalties
            "W_e": 0.1,
            "W_t": 0.5,
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

        build_dat_files(self.dat_dir, scenario_data)

        try:
            status, var_values = self.solve(
                params={
                    "N": len(N), "B": len(B), "V": len(V), "P": len(P),
                    "C_n": cap_n, "B_nb": y, "C_v": cap_vehicle,
                },
            )
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")

        self.assertIn(status, ("optimal", "feasible"), "El modelo no encontró una solución.")


if __name__ == "__main__":
    unittest.main()
