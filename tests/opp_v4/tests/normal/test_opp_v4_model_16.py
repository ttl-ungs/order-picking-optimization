# Corresponds to test test_opp_v2_model_19.py

import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from models.utils.dat_files_builder import build_dat_files
from models.base.opp_location_graph import OPPLocationGraph
from tests.opp_v4.tests.opp_test_case_v4 import OPPTestCaseV4
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.utils.zpl_utils import extract_active_arcs, solve_zpl

from tests.shared_scenarios.normal.scenario_19_v4 import longer_single_mission_route
from tests.opp_v4.tests.route_assertions import assert_route_covers_orders

class TestOPPModelZIMPL(OPPTestCaseV4):
    """
    Test 16 (ZIMPL): Single mission, longer route. 9 vertices, 1 batch, 6 orders.
    Equivalent to test_opp_v3_model_19.py / test_opp_hc_2_model_19.py.
    """

    def _solve_longer_route(
        self,
        due_date,
        w1_override=None,
        w2_override=None,
        gamma_override=None,
        delta_override=None,
        duplicate_location=False,
    ):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, _x = (
            longer_single_mission_route()
        )

        w1, w2, gamma, delta = self.apply_weight_overrides(
            w1,
            w2,
            gamma,
            delta,
            w1_override,
            w2_override,
            gamma_override,
            delta_override,
        )

        N = {"O1", "O2", "O3", "O4", "O5", "O6"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        if duplicate_location:
            a[("O2", "L2")] = 1
        else:
            a[("O2", "L3")] = 1
        a[("O3", "L4")] = 1
        a[("O4", "L5")] = 1
        a[("O5", "L6")] = 1
        a[("O6", "L7")] = 1

        y = {
            ("O1", "B1"): 1,
            ("O2", "B1"): 1,
            ("O3", "B1"): 1,
            ("O4", "B1"): 1,
            ("O5", "B1"): 1,
            ("O6", "B1"): 1,
        }
        cap_n = {n: 2.0 for n in N}

        due_date_by_order = self.normalize_due_dates(N, due_date)

        S_i = {v: 0.0 for v in V}

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
            "M": 10000.0,
            "C_n": cap_n,
            "Dd": due_date_by_order,
            "d_ij": d_ij,
            "S_i": S_i,
            "A_ni": a,
            "Bn": y,
        }

        build_dat_files(DAT_DIR, scenario_data)

        try:
            status, var_values = solve_zpl(
                ZPL_PATH,
                dat_dir=DAT_DIR,
                params={
                    "N": len(N),
                    "B": len(B),
                    "V": len(set(location_graph.get_vertices())),
                    "P": len(P),
                    "W_full": w1,
                    "W_ea_ta": w2,
                    "W_ea": gamma,
                    "W_ta": delta,
                    "B_time": 0.5,
                    "B_setup": 1.0,
                    "B_picking": 1.0,
                    "C_v": cap_vehicle,
                    "C_n": cap_n,
                    "Dd": due_date_by_order,
                    "d_ij": d_ij,
                    "S_i": S_i,
                    "A_ni": a,
                    "Bn": y,
                },
            )
        except Exception as e:
            self.fail(f"ZPL solve failed: {e}")

        return status, var_values, location_graph, B

    def _sum_vars_with_prefix(self, var_values, prefix):
        total = 0.0
        for key, val in var_values.items():
            if key.lower().startswith(prefix):
                total += val
        return total

    def test_longer_single_mission_route(self):
        status, var_values, location_graph, B = self._solve_longer_route(due_date=25.0)

        self.assertIn(status, ("optimal", "feasible"), "El modelo no encontró una solución.")

        active_arcs = extract_active_arcs(var_values, B)
        output_graph = OPPLocationGraph(depot_node=location_graph.get_depot(), final_node=location_graph.get_final())
        for i in location_graph.get_vertices():
            if i not in output_graph.get_vertices():
                output_graph.add_vertex(i, "picking")
        for b, arcs in active_arcs.items():
            for i, j in arcs:
                if not output_graph.has_edge(i, j):
                    output_graph.add_edge(i, j, location_graph.get_distance(i, j))

        # The objective weighs earliness/tardiness (W_ea_ta=10) far more heavily
        # than raw distance (W_full=1), so the model is free to prefer a longer
        # route if it reduces earliness penalties. We only assert that the
        # result is a single valid depot->final path covering every required
        # location, not one specific set of edges.
        assert_route_covers_orders(
            self, output_graph, {"L2", "L3", "L4", "L5", "L6", "L7"}
        )

    def test_longer_single_mission_penalties(self):
        status_low, var_values_low, _, _ = self._solve_longer_route(
            due_date=0.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=0.0,
            delta_override=1.0,
        )

        self.assertIn(status_low, ("optimal", "feasible"), "El modelo no encontró una solución.")
        self.assertGreater(self._sum_vars_with_prefix(var_values_low, "ta_n"), 1e-6)

        status_high, var_values_high, _, _ = self._solve_longer_route(
            due_date=100.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=0.0,
            delta_override=1.0,
        )

        self.assertIn(status_high, ("optimal", "feasible"), "El modelo no encontró una solución.")
        self.assertLessEqual(self._sum_vars_with_prefix(var_values_high, "ta_n"), 1e-6)

    def test_longer_single_mission_duplicate_location(self):
        status, _, _, _ = self._solve_longer_route(
            due_date=25.0,
            duplicate_location=True,
        )

        self.assertIn(status, ("optimal", "feasible"), "El modelo no encontró una solución.")


if __name__ == "__main__":
    unittest.main()
