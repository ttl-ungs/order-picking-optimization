import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.infra.cases.exact_model_case import ExactModelTestCase

from tests.shared_scenarios.functional.multigrid_graph_v4 import (
    multigrid_5x5_3x3_five_pickers_twelve_batches,
)


class Case30(ExactModelTestCase):
    """
    Ported from opp_hc_2's test #26 (test_fractional_and_zero_capacities_*):
    a mix of zero and fractional order capacities. Exercises the new C_v
    pre-validation (models/utils/input_validation.py) at a fractional
    boundary: cap_vehicle=5.0 is infeasible (0+1.5+2.25+3.0 split into two
    batches of 1.5 and 5.25 -- the second overflows), cap_vehicle=6.0 fits.
    """

    def _solve(self, cap_vehicle):
        V, P, B, _, _, _, _, opp_location_graph, _, _ = (
            multigrid_5x5_3x3_five_pickers_twelve_batches()
        )

        N = {"O1", "O2", "O3", "O4"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "A2")] = 1
        a[("O2", "A3")] = 1
        a[("O3", "A4")] = 1
        a[("O4", "A5")] = 1

        y = {(n, b): 0 for n in N for b in B}
        batches = sorted(B)
        y[("O1", batches[0])] = 1
        y[("O2", batches[0])] = 1
        y[("O3", batches[1])] = 1
        y[("O4", batches[1])] = 1

        cap_n = {"O1": 0.0, "O2": 1.5, "O3": 2.25, "O4": 3.0}
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

        build_dat_files(self.dat_dir, scenario_data)

        return self.solve(
            params={
                "N": len(N), "B": len(B), "V": len(V), "P": len(P),
                "C_n": cap_n, "B_nb": y, "C_v": cap_vehicle,
            },
        )

    def test_fractional_and_zero_capacities_infeasible(self):
        """Case 30b."""
        status, _ = self._solve(cap_vehicle=5.0)
        self.assertEqual(status, "infeasible")

    def test_fractional_and_zero_capacities_feasible(self):
        """Case 30a."""
        try:
            status, _ = self._solve(cap_vehicle=6.0)
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")
        self.assertIn(status, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
