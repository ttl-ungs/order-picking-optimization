import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from tests.opp_v4.opp_test_case_v4 import OPPTestCaseV4
from tests.shared_scenarios.functional.scenario_12_v4 import grid_5x3_two_pickers_four_batches
from tests.infra.zimpl.dat_files_builder import build_dat_files
from tests.opp_v4.config import DAT_DIR, ZPL_PATH
from tests.infra.zimpl.zpl_utils import extract_active_arcs, solve_zpl


class TestOPPModelGridZIMPL(OPPTestCaseV4):
    def _solve_grid_zpl(
        self,
        N,
        a,
        y,
        cap_n,
        cap_vehicle_override=None,
        due_date_override=None,
        w1_override=None,
        w2_override=None,
        gamma_override=None,
        delta_override=None,
    ):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, _ = (
            grid_5x3_two_pickers_four_batches()
        )

        if cap_vehicle_override is not None:
            cap_vehicle = cap_vehicle_override
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
        due_date_by_order = self.normalize_due_dates(N, due_date_override)

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
            "S_i": {v: 0.0 for v in V},
            "A_ni": a,
            "Bn": y,
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
                "Bn": y,
                "C_v": cap_vehicle,
            },
        )

        return status, var_values, location_graph, B, V

    def test_grid_multi_location_orders_with_capacities(self):
        V, _, B, _, _, _, _, _, _, _ = grid_5x3_two_pickers_four_batches()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        # Setup de locaciones
        locs = {
            "O1": ["V2", "V7"],
            "O2": ["V3"],
            "O3": ["V8"],
            "O4": ["V4"],
            "O5": ["V9"],
            "O6": ["V10"],
            "O7": ["V5"],
            "O8": ["V11"],
            "O9": ["V12"],
            "O10": ["V6"],
            "O11": ["V13"],
            "O12": ["V14"],
        }
        for order, loc_list in locs.items():
            for loc in loc_list:
                a[(order, loc)] = 1

        y = {(n, b): 0 for n in N for b in B}
        batches = {
            "O1": "B1",
            "O2": "B1",
            "O3": "B1",
            "O4": "B2",
            "O5": "B2",
            "O6": "B2",
            "O7": "B3",
            "O8": "B3",
            "O9": "B3",
            "O10": "B4",
            "O11": "B4",
            "O12": "B4",
        }
        for order, b in batches.items():
            y[(order, b)] = 1

        cap_n = {n: 2.0 for n in N}
        status, var_values, _, _, _ = self._solve_grid_zpl(N, a, y, cap_n)
        self.assertIn(
            status,
            ("optimal", "feasible"),
            "El modelo no encontró una solución.",
        )

        # Validar cobertura de locaciones extrayendo arcos
        active_arcs = extract_active_arcs(var_values, B)
        required_by_batch = {
            "B1": {"V2", "V7", "V3", "V8"},
            "B2": {"V4", "V9", "V10"},
            "B3": {"V5", "V11", "V12"},
            "B4": {"V6", "V13", "V14"},
        }

        for batch, required_locs in required_by_batch.items():
            visited = set(node for edge in active_arcs.get(batch, []) for node in edge)
            for loc in required_locs:
                self.assertIn(loc, visited, f"El lote {batch} no visitó {loc}")

    def test_grid_penalties_due_date(self):
        V, _, B, _, _, _, _, _, _, _ = grid_5x3_two_pickers_four_batches()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "V2")] = 1
        a[("O1", "V7")] = 1
        a[("O2", "V3")] = 1
        a[("O3", "V8")] = 1
        a[("O4", "V4")] = 1
        a[("O5", "V9")] = 1
        a[("O6", "V10")] = 1
        a[("O7", "V5")] = 1
        a[("O8", "V11")] = 1
        a[("O9", "V12")] = 1
        a[("O10", "V6")] = 1
        a[("O11", "V13")] = 1
        a[("O12", "V14")] = 1

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

        status_low, _, _, _, _ = self._solve_grid_zpl(
            N, a, y, cap_n,
            due_date_override=0.0,
            w1_override=0.0, w2_override=1.0, gamma_override=0.0, delta_override=1.0,
        )
        self.assertIn(status_low, ("optimal", "feasible"))

        status_high, _, _, _, _ = self._solve_grid_zpl(
            N, a, y, cap_n,
            due_date_override=100.0,
            w1_override=0.0, w2_override=1.0, gamma_override=0.0, delta_override=1.0,
        )
        self.assertIn(status_high, ("optimal", "feasible"))

    def test_grid_penalties_order_size_equal_to_cart(self):
        V, _, B, _, _, _, _, _, _, _ = grid_5x3_two_pickers_four_batches()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "V2")] = 1
        a[("O1", "V7")] = 1
        a[("O2", "V3")] = 1
        a[("O3", "V8")] = 1
        a[("O4", "V4")] = 1
        a[("O5", "V9")] = 1
        a[("O6", "V10")] = 1
        a[("O7", "V5")] = 1
        a[("O8", "V11")] = 1
        a[("O9", "V12")] = 1
        a[("O10", "V6")] = 1
        a[("O11", "V13")] = 1
        a[("O12", "V14")] = 1

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

        status_small, _, _, _, _ = self._solve_grid_zpl(
            N, a, y, cap_n_small,
            due_date_override=10.0,
            w1_override=0.0, w2_override=1.0, gamma_override=0.0, delta_override=1.0,
        )
        self.assertIn(status_small, ("optimal", "feasible"))

        # 2.0 per order * 3 orders per batch = 6.0, exactly cap_vehicle -> still feasible,
        # boundary case for the new C_v pre-validation (see models/utils/capacity_validation.py).
        cap_n_large = {n: 2.0 for n in N}
        status_large, _, _, _, _ = self._solve_grid_zpl(
            N, a, y, cap_n_large,
            due_date_override=10.0,
            w1_override=0.0, w2_override=1.0, gamma_override=0.0, delta_override=1.0,
        )
        self.assertIn(status_large, ("optimal", "feasible"))

    def test_grid_order_size_bigger_than_cart_infeasible(self):
        """
        Was disabled with the note "El modelo ya no evalúa que las órdenes
        entren en el carro, el test ya no tiene sentido" -- opp_model_v4.zpl
        dropped the C_v parameter entirely (see models.tex / the ZPL file
        itself). Re-enabled now that solve_zpl() pre-validates vehicle
        capacity against C_n/Bn before ever calling ZIMPL/SCIP (see
        models/utils/capacity_validation.py), matching opp_hc_2/opp_aco_2's
        behaviour for the same instance.
        """
        V, _, B, _, _, _, _, _, _, _ = grid_5x3_two_pickers_four_batches()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}
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

        # 3.0 per order * 3 orders per batch = 9.0 > cap_vehicle (6.0)
        cap_n = {n: 3.0 for n in N}
        status, _, _, _, _ = self._solve_grid_zpl(N, a, y, cap_n)

        self.assertEqual(status, "infeasible")

    def test_grid_batch_infeasible_order_size(self):
        V, _, B, _, _, _, _, _, _, _ = grid_5x3_two_pickers_four_batches()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "V2")] = 1
        a[("O2", "V7")] = 1
        a[("O3", "V11")] = 1
        a[("O4", "V3")] = 1
        a[("O5", "V8")] = 1
        a[("O6", "V12")] = 1
        a[("O7", "V4")] = 1
        a[("O8", "V9")] = 1
        a[("O9", "V13")] = 1
        a[("O10", "V5")] = 1
        a[("O11", "V10")] = 1
        a[("O12", "V14")] = 1

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
        cap_n["O1"] = 3.0  # 3 + 2 + 2 = 7 > cap_vehicle (6.0) for batch B1
        status, _, _, _, _ = self._solve_grid_zpl(N, a, y, cap_n)

        self.assertEqual(status, "infeasible")

    def test_grid_shared_locations_across_batches(self):
        V, _, B, _, _, _, _, _, _, _ = grid_5x3_two_pickers_four_batches()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "V2")] = 1
        a[("O2", "V7")] = 1
        a[("O3", "V11")] = 1
        a[("O4", "V3")] = 1
        a[("O5", "V8")] = 1
        a[("O6", "V12")] = 1
        a[("O7", "V4")] = 1
        a[("O8", "V7")] = 1
        a[("O9", "V13")] = 1
        a[("O10", "V5")] = 1
        a[("O11", "V8")] = 1
        a[("O12", "V14")] = 1

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
        status, _, _, _, _ = self._solve_grid_zpl(N, a, y, cap_n)

        self.assertIn(status, ("optimal", "feasible"))

    def test_grid_duplicate_location_within_batch(self):
        V, _, B, _, _, _, _, _, _, _ = grid_5x3_two_pickers_four_batches()
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "V2")] = 1
        a[("O2", "V2")] = 1
        a[("O3", "V7")] = 1
        a[("O4", "V3")] = 1
        a[("O5", "V8")] = 1
        a[("O6", "V12")] = 1
        a[("O7", "V4")] = 1
        a[("O8", "V9")] = 1
        a[("O9", "V13")] = 1
        a[("O10", "V5")] = 1
        a[("O11", "V10")] = 1
        a[("O12", "V14")] = 1

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
        status, _, _, _, _ = self._solve_grid_zpl(N, a, y, cap_n)

        self.assertIn(status, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
