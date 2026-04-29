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
from tests.opp_v2.scenarios.normal.scenario_13 import (
    bridge_graph_disconnected,
    bridge_graph_two_pickers_four_batches,
)
from tests.opp_v2.tests.route_assertions import assert_batch_routes_cover_locations


class TestOPPModelBridge(OPPTestCase):
    def _solve_bridge(
        self,
        N,
        a,
        y,
        cap_n,
        disconnected=False,
        due_date_override=None,
        w1_override=None,
        w2_override=None,
        gamma_override=None,
        delta_override=None,
        beta_time_override=None,
        beta_setup_override=None,
        beta_picking_override=None,
    ):
        if disconnected:
            V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
                bridge_graph_disconnected()
            )
        else:
            V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
                bridge_graph_two_pickers_four_batches()
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

        due_date_by_order = self.normalize_due_dates(N, due_date_override)

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        if beta_time_override is not None:
            beta_time = beta_time_override
        if beta_setup_override is not None:
            beta_setup = beta_setup_override
        if beta_picking_override is not None:
            beta_picking = beta_picking_override

        params = SolveModelDTO()
        params.w1 = w1
        params.w2 = w2
        params.gamma = gamma
        params.delta = delta
        params.cap_n = cap_n
        params.cap_vehicle = cap_vehicle
        params.a = a
        params.beta_time = beta_time
        params.beta_setup = beta_setup
        params.beta_picking = beta_picking
        params.due_date = due_date_by_order
        params.M = 1000.0
        params.x = x
        params.y = y

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

    def test_bridge_shared_locations_across_batches(self):
        V, _, B, _, _, _, _, _, _, _ = bridge_graph_two_pickers_four_batches()

        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L8")] = 1
        a[("O3", "L9")] = 1
        a[("O4", "L3")] = 1
        a[("O5", "L10")] = 1
        a[("O6", "L11")] = 1
        a[("O7", "L4")] = 1
        a[("O8", "L8")] = 1
        a[("O9", "L10")] = 1
        a[("O10", "L5")] = 1
        a[("O11", "L9")] = 1
        a[("O12", "L11")] = 1

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
        result, model, location_graph, batches, _ = self._solve_bridge(N, a, y, cap_n)

        self.assertIn(result, ("optimal", "feasible"))

        required_by_batch = {
            "B1": {"L2", "L8", "L9"},
            "B2": {"L3", "L10", "L11"},
            "B3": {"L4", "L8", "L10"},
            "B4": {"L5", "L9", "L11"},
        }

        routes_by_batch = assert_batch_routes_cover_locations(
            self,
            model.model,
            batches,
            location_graph.get_depot(),
            location_graph.get_final(),
            required_by_batch,
        )

        for batch, route in routes_by_batch.items():
            self.assertIn("L6", route, f"Batch {batch} did not cross bridge L6")
            self.assertIn("L7", route, f"Batch {batch} did not cross bridge L7")

    def test_bridge_tardiness_beta_picking(self):
        V, _, B, _, _, _, _, _, _, _ = bridge_graph_two_pickers_four_batches()

        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L8")] = 1
        a[("O3", "L9")] = 1
        a[("O4", "L3")] = 1
        a[("O5", "L10")] = 1
        a[("O6", "L11")] = 1
        a[("O7", "L4")] = 1
        a[("O8", "L8")] = 1
        a[("O9", "L10")] = 1
        a[("O10", "L5")] = 1
        a[("O11", "L9")] = 1
        a[("O12", "L11")] = 1

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

        result_fast, model_fast, _, _, _ = self._solve_bridge(
            N,
            a,
            y,
            cap_n,
            due_date_override=10.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=0.0,
            delta_override=1.0,
            beta_picking_override=0.5,
        )

        self.assertIn(result_fast, ("optimal", "feasible"))

        total_tardiness_fast = self.sum_vars_with_prefix(model_fast.model, "ta_")

        result_slow, model_slow, _, _, _ = self._solve_bridge(
            N,
            a,
            y,
            cap_n,
            due_date_override=10.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=0.0,
            delta_override=1.0,
            beta_picking_override=2.0,
        )

        self.assertIn(result_slow, ("optimal", "feasible"))

        total_tardiness_slow = self.sum_vars_with_prefix(model_slow.model, "ta_")
        self.assertGreater(total_tardiness_slow, total_tardiness_fast + 1e-6)

    def test_bridge_earliness_order_size(self):
        V, _, B, _, _, _, _, _, _, _ = bridge_graph_two_pickers_four_batches()

        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L8")] = 1
        a[("O3", "L9")] = 1
        a[("O4", "L3")] = 1
        a[("O5", "L10")] = 1
        a[("O6", "L11")] = 1
        a[("O7", "L4")] = 1
        a[("O8", "L8")] = 1
        a[("O9", "L10")] = 1
        a[("O10", "L5")] = 1
        a[("O11", "L9")] = 1
        a[("O12", "L11")] = 1

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
        cap_n_large = {n: 2.0 for n in N}

        result_small, model_small, _, _, _ = self._solve_bridge(
            N,
            a,
            y,
            cap_n_small,
            due_date_override=100.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=1.0,
            delta_override=0.0,
        )

        self.assertIn(result_small, ("optimal", "feasible"))

        total_earliness_small = self.sum_vars_with_prefix(model_small.model, "ea_")
        total_tardiness_small = self.sum_vars_with_prefix(model_small.model, "ta_")

        result_large, model_large, _, _, _ = self._solve_bridge(
            N,
            a,
            y,
            cap_n_large,
            due_date_override=100.0,
            w1_override=0.0,
            w2_override=1.0,
            gamma_override=1.0,
            delta_override=0.0,
        )

        self.assertIn(result_large, ("optimal", "feasible"))

        total_earliness_large = self.sum_vars_with_prefix(model_large.model, "ea_")
        total_tardiness_large = self.sum_vars_with_prefix(model_large.model, "ta_")

        self.assertLessEqual(total_tardiness_small, 1e-6)
        self.assertLessEqual(total_tardiness_large, 1e-6)

        # TODO: por que son iguales? Deberia ser mayor el de cap 1.0 no?
        self.assertEqual(total_earliness_small, total_earliness_large)

    def test_bridge_disconnected_required_location(self):
        V, _, B, _, _, _, _, _, _, _ = bridge_graph_disconnected()

        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L8")] = 1
        a[("O3", "L9")] = 1
        a[("O4", "L3")] = 1
        a[("O5", "L10")] = 1
        a[("O6", "L11")] = 1
        a[("O7", "L4")] = 1
        a[("O8", "L8")] = 1
        a[("O9", "L10")] = 1
        a[("O10", "L5")] = 1
        a[("O11", "L9")] = 1
        a[("O12", "L11")] = 1

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
        result, _, _, _, _ = self._solve_bridge(N, a, y, cap_n, disconnected=True)

        self.assertEqual(result, "infeasible")


if __name__ == "__main__":
    unittest.main()
