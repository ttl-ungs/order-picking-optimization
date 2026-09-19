import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from models.utils.dat_files_builder import build_dat_files
from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.utils.zpl_utils import solve_zpl

from tests.shared_scenarios.normal.scenario_01_v4 import basic_two_orders_capacity_limit


class TestOPPModelZIMPLDifferentWeights(OPPTestCaseV4):
    """
    Ported from opp_hc_2's test #05 (test_basic_two_orders_with_different_weights):
    same scenario as test_case_01, different objective weights.
    """

    def test_basic_two_orders_with_different_weights(self):
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
            "W_full": 2.0,  # Higher weight on completion time
            "W_ea_ta": 0.5,  # Lower weight on penalties
            "W_ea": 0.1,
            "W_ta": 0.5,
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

        try:
            status, var_values = solve_zpl(
                ZPL_PATH,
                dat_dir=DAT_DIR,
                params={
                    "N": len(N), "B": len(B), "V": len(V), "P": len(P),
                    "C_n": cap_n, "Bn": y, "C_v": cap_vehicle,
                },
            )
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")

        self.assertIn(status, ("optimal", "feasible"), "El modelo no encontró una solución.")


if __name__ == "__main__":
    unittest.main()
