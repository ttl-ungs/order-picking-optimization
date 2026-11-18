import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.infra.cases.exact_model_case import ExactModelTestCase

from tests.shared_scenarios.functional.scenario_02 import two_orders_two_aisles


class Case31(ExactModelTestCase):
    """
    B_nb has no ZIMPL constraint enforcing
    "each order in exactly one batch" (it's a fixed parameter, not a
    decision variable) -- exercises the orders_without_exactly_one_batch
    pre-validation (models/utils/input_validation.py) instead.
    """

    def _solve(self, y):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, _ = (
            two_orders_two_aisles()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        a[("O1", "L3")] = 1
        a[("O2", "L5")] = 1

        cap_n = {"O1": 3.0, "O2": 3.0}
        due_date = {"O1": 50.0, "O2": 50.0}

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
            "S_i": {v: 0.0 for v in V},
            "A_ni": a,
            "B_nb": y,
        }

        build_dat_files(self.dat_dir, scenario_data)

        return self.solve(
            params={
                "N": len(N), "B": len(B), "V": len(V), "P": len(P),
                "C_n": cap_n, "B_nb": y, "C_v": cap_vehicle,
            },
        )

    def test_order_assigned_to_multiple_batches_infeasible(self):
        """Case 31a."""
        # O1 in both B1 and B2 -> violates sum_b B_nb[n,b] == 1
        y = {(n, b): 0 for n in {"O1", "O2"} for b in {"B1", "B2"}}
        y[("O1", "B1")] = 1
        y[("O1", "B2")] = 1
        y[("O2", "B2")] = 1

        status, _ = self._solve(y)
        self.assertEqual(status, "infeasible")

    def test_order_assigned_to_single_batch_feasible(self):
        """Case 31b."""
        y = {(n, b): 0 for n in {"O1", "O2"} for b in {"B1", "B2"}}
        y[("O1", "B1")] = 1
        y[("O2", "B2")] = 1

        try:
            status, _ = self._solve(y)
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")
        self.assertIn(status, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
