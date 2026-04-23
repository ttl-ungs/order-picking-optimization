import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.opp.solve_model_dto import SolveModelDTO
from models.opp_v2.opp_model_v2 import OPPModelV2
from models.opp_v2.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.opp_v2.scenarios.multigrid_graph import (
    CORRIDOR_PATH,
    multigrid_5x5_3x3_five_pickers_twelve_batches,
    multigrid_5x5_3x3_single_picker_single_batch_corridor,
)
from tests.opp_v2.tests.route_assertions import (
    assert_correct_path,
    assert_batch_routes_cover_locations,
    get_active_arcs_by_batch,
)


class TestOPPModelMultiGrid(OPPTestCase):
    CONNECTOR_EDGES = {
        ("A13", "B1"),
        ("B1", "A13"),
        ("A23", "B7"),
        ("B7", "A23"),
    }

    def _build_multigrid_orders(self, V, B):
        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        order_locations = [
            "A2",
            "A7",
            "A12",
            "A17",
            "A22",
            "A5",
            "B2",
            "B4",
            "B6",
            "B8",
            "B3",
            "B7",
        ]

        y = {(n, b): 0 for n in N for b in B}
        sorted_batches = sorted(B)
        sorted_orders = sorted(N)

        required_by_batch = {}
        for i, order_id in enumerate(sorted_orders):
            location_id = order_locations[i]
            batch_id = sorted_batches[i]
            a[(order_id, location_id)] = 1
            y[(order_id, batch_id)] = 1
            required_by_batch[batch_id] = {location_id}

        return N, a, y, required_by_batch

    def _solve_multigrid(
        self,
        N,
        a,
        y,
        cap_n,
        connect=True,
        due_date_override=None,
        w1_override=None,
        w2_override=None,
        gamma_override=None,
        delta_override=None,
        beta_time_override=None,
        beta_setup_override=None,
        beta_picking_override=None,
    ):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            multigrid_5x5_3x3_five_pickers_twelve_batches(connect=connect)
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

    def _build_multigrid_orders_per_batch(self, location_graph, V, B, orders_per_batch):
        depot = location_graph.get_depot()
        final = location_graph.get_final()
        locations = [v for v in V if v not in {depot, final}]
        total_orders = len(B) * orders_per_batch

        N = {f"O{i}" for i in range(1, total_orders + 1)}
        a = {(n, v): 0 for n in N for v in V}
        y = {(n, b): 0 for n in N for b in B}

        sorted_batches = sorted(B)
        sorted_orders = sorted(N)

        required_by_batch = {}
        location_count = len(locations)
        order_index = 0
        for batch_index, batch_id in enumerate(sorted_batches):
            start = (batch_index * orders_per_batch) % location_count
            required = set()
            for j in range(orders_per_batch):
                order_id = sorted_orders[order_index]
                location_id = locations[(start + j) % location_count]
                a[(order_id, location_id)] = 1
                y[(order_id, batch_id)] = 1
                required.add(location_id)
                order_index += 1
            required_by_batch[batch_id] = required

        return N, a, y, required_by_batch

    def test_multigrid_routes_cover_locations(self):
        V, _, B, _, _, _, _, _, _, _ = multigrid_5x5_3x3_five_pickers_twelve_batches()
        N, a, y, required_by_batch = self._build_multigrid_orders(V, B)

        cap_n = {n: 2.0 for n in N}
        result, model, location_graph, batches, _ = self._solve_multigrid(
            N,
            a,
            y,
            cap_n,
        )

        self.assertIn(result, ("optimal", "feasible"))

        routes_by_batch = assert_batch_routes_cover_locations(
            self,
            model.model,
            batches,
            location_graph.get_depot(),
            location_graph.get_final(),
            required_by_batch,
        )

        arcs_by_batch = get_active_arcs_by_batch(model.model, batches)
        for batch_id, route in routes_by_batch.items():
            self.assertTrue(
                any(
                    edge in arcs_by_batch.get(batch_id, [])
                    for edge in self.CONNECTOR_EDGES
                ),
                f"Batch {batch_id} did not use a connector edge: {route}",
            )

    def test_multigrid_single_batch_exact_path(self):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            multigrid_5x5_3x3_single_picker_single_batch_corridor()
        )

        order_locations = [
            "A2",
            "A3",
            "A4",
            "A5",
            "A10",
            "A15",
            "A20",
            "A25",
            "A24",
            "A23",
            "B7",
            "B8",
        ]
        N = {f"O{i}" for i in range(1, len(order_locations) + 1)}
        a = {(n, v): 0 for n in N for v in V}
        y = {(n, "B1"): 1 for n in N}

        for order_id, location_id in zip(sorted(N), order_locations):
            a[(order_id, location_id)] = 1

        cap_n = {n: 1.0 for n in N}

        params = SolveModelDTO()
        params.w1 = w1
        params.w2 = w2
        params.gamma = gamma
        params.delta = delta
        params.cap_n = cap_n
        params.cap_vehicle = cap_vehicle
        params.a = a
        params.beta_time = 0.5
        params.beta_setup = 1.0
        params.beta_picking = 1.0
        params.due_date = {n: 100.0 for n in N}
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

        result, output_graph = model.solve(params)

        self.assertEqual(result, "optimal")
        self.assertIsNotNone(output_graph)
        assert_correct_path(self, output_graph, CORRIDOR_PATH)

    def test_multigrid_many_orders_per_batch(self):
        V, _, B, _, _, _, _, location_graph, _, _ = (
            multigrid_5x5_3x3_five_pickers_twelve_batches()
        )
        orders_per_batch = 5
        N, a, y, required_by_batch = self._build_multigrid_orders_per_batch(
            location_graph,
            V,
            B,
            orders_per_batch,
        )

        cap_n = {n: 1.0 for n in N}
        result, model, _, batches, _ = self._solve_multigrid(N, a, y, cap_n)

        self.assertIn(result, ("optimal", "feasible"))

        assert_batch_routes_cover_locations(
            self,
            model.model,
            batches,
            location_graph.get_depot(),
            location_graph.get_final(),
            required_by_batch,
        )

    def test_multigrid_tardiness_beta_picking(self):
        V, _, B, _, _, _, _, _, _, _ = multigrid_5x5_3x3_five_pickers_twelve_batches()
        N, a, y, _ = self._build_multigrid_orders(V, B)

        cap_n = {n: 2.0 for n in N}

        result_fast, model_fast, _, _, _ = self._solve_multigrid(
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

        result_slow, model_slow, _, _, _ = self._solve_multigrid(
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

    def test_multigrid_earliness_order_size(self):
        V, _, B, _, _, _, _, _, _, _ = multigrid_5x5_3x3_five_pickers_twelve_batches()
        N, a, y, _ = self._build_multigrid_orders(V, B)

        cap_n_small = {n: 1.0 for n in N}
        cap_n_large = {n: 10.0 for n in N}

        result_small, model_small, _, _, _ = self._solve_multigrid(
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

        result_large, model_large, _, _, _ = self._solve_multigrid(
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
        self.assertGreater(total_earliness_small, total_earliness_large + 1e-6)

    def test_multigrid_disconnected_infeasible(self):
        V, _, B, _, _, _, _, _, _, _ = multigrid_5x5_3x3_five_pickers_twelve_batches(
            connect=False
        )
        N, a, y, _ = self._build_multigrid_orders(V, B)

        cap_n = {n: 2.0 for n in N}
        result, _, _, _, _ = self._solve_multigrid(
            N,
            a,
            y,
            cap_n,
            connect=False,
        )

        self.assertEqual(result, "infeasible")


if __name__ == "__main__":
    unittest.main()
