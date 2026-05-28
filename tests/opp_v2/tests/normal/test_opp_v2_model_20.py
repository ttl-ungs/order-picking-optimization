import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.opp.solve_model_dto import SolveModelDTO
from models.opp_v2.opp_model_v2 import OPPModelV2
from models.opp_v2.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.opp_v2.scenarios.normal.scenario_12 import grid_5x3_two_pickers_four_batches
from tests.opp_v2.tests.route_assertions import assert_batch_routes_cover_locations


class TestOPPModelGrid(OPPTestCase):
    def _solve_grid(
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
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
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

        params = SolveModelDTO()
        params.W_full = w1
        params.W_ea_ta = w2
        params.W_ea = gamma
        params.W_ta = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = 0.5
        params.B_setup = 1.0
        params.B_picking = 1.0
        params.Dd = due_date_by_order
        params.M = 1000.0
        params.x = x
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.P = P
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPModelV2(model_dto)
        model.attach(OutputHandler())

        result, _ = model.solve(params)

        return result, model, location_graph, B, V

    def test_grid_multi_location_orders(self):
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
        result, model, location_graph, batches, _ = self._solve_grid(N, a, y, cap_n)

        self.assertIn(result, ("optimal", "feasible"))

        required_by_batch = {
            "B1": {"V2", "V7", "V3", "V8"},
            "B2": {"V4", "V9", "V10"},
            "B3": {"V5", "V11", "V12"},
            "B4": {"V6", "V13", "V14"},
        }

        assert_batch_routes_cover_locations(
            self,
            model.model,
            batches,
            location_graph.get_depot(),
            location_graph.get_final(),
            required_by_batch,
        )

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

        result_low, model_low, _, _, _ = self._solve_grid(
            N,
            a,
            y,
            cap_n,
            due_date_override=0.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=0.0,
            delta_override=1.0,
        )

        self.assertIn(result_low, ("optimal", "feasible"))

        total_tardiness_low = self.sum_vars_with_prefix(model_low.model, "ta_")
        self.assertGreater(total_tardiness_low, 1e-6)

        result_high, model_high, _, _, _ = self._solve_grid(
            N,
            a,
            y,
            cap_n,
            due_date_override=100.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=0.0,
            delta_override=1.0,
        )

        self.assertIn(result_high, ("optimal", "feasible"))

        total_tardiness_high = self.sum_vars_with_prefix(model_high.model, "ta_")
        self.assertLessEqual(total_tardiness_high, 1e-6)

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
        cap_n_large = {n: 2.0 for n in N}  # Capacity equal to cart size

        result_small, model_small, _, _, _ = self._solve_grid(
            N,
            a,
            y,
            cap_n_small,
            due_date_override=10.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=0.0,
            delta_override=1.0,
        )

        self.assertIn(result_small, ("optimal", "feasible"))

        total_tardiness_small = self.sum_vars_with_prefix(model_small.model, "ta_")

        result_large, model_large, _, _, _ = self._solve_grid(
            N,
            a,
            y,
            cap_n_large,
            due_date_override=10.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=0.0,
            delta_override=1.0,
        )

        self.assertIn(result_large, ("optimal", "feasible"))

        total_tardiness_large = self.sum_vars_with_prefix(model_large.model, "ta_")

        # With order size equal to cart size, we expect more tardiness
        self.assertGreater(total_tardiness_large, total_tardiness_small + 1e-6)

    def test_grid_order_size_bigger_than_cart_infeasible(self):
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

        cap_n = {n: 3.0 for n in N}

        result, model, _, _, _ = self._solve_grid(
            N,
            a,
            y,
            cap_n,
            due_date_override=10.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=0.0,
            delta_override=1.0,
        )

        self.assertEqual(result, "infeasible")

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
        cap_n["O1"] = 3.0  # Order size bigger than cart capacity
        result, _, _, _, _ = self._solve_grid(N, a, y, cap_n)

        self.assertEqual(result, "infeasible")

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
        result, model, location_graph, batches, _ = self._solve_grid(N, a, y, cap_n)

        self.assertIn(result, ("optimal", "feasible"))

        required_by_batch = {
            "B1": {"V2", "V7", "V11"},
            "B2": {"V3", "V8", "V12"},
            "B3": {"V4", "V7", "V13"},
            "B4": {"V5", "V8", "V14"},
        }

        assert_batch_routes_cover_locations(
            self,
            model.model,
            batches,
            location_graph.get_depot(),
            location_graph.get_final(),
            required_by_batch,
        )

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
        result, _, _, _, _ = self._solve_grid(N, a, y, cap_n)

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()

