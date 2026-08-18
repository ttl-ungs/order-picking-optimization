import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from models.utils.dat_files_builder import build_dat_files
from tests.opp_v4.tests.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.utils.zpl_utils import solve_zpl

from tests.opp_v4.scenarios.normal.scenario_02 import two_orders_two_aisles


class TestOrderAssignedMultipleBatchesZIMPL(OPPTestCaseV4):
    """
    Ported from opp_hc_2's test #27. Bn has no ZIMPL constraint enforcing
    "each order in exactly one batch" (it's a fixed parameter, not a
    decision variable) -- exercises the new orders_without_exactly_one_batch
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
            "W_full": w1,
            "W_ea_ta": w2,
            "W_ea": gamma,
            "W_ta": delta,
            "B_time": 0.5,
            "B_setup": 1.0,
            "B_picking": 1.0,
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

    def test_order_assigned_to_multiple_batches_infeasible(self):
        # O1 in both B1 and B2 -> violates sum_b Bn[n,b] == 1
        y = {(n, b): 0 for n in {"O1", "O2"} for b in {"B1", "B2"}}
        y[("O1", "B1")] = 1
        y[("O1", "B2")] = 1
        y[("O2", "B2")] = 1

        status, _ = self._solve(y)
        self.assertEqual(status, "infeasible")

    def test_order_assigned_to_single_batch_feasible(self):
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
