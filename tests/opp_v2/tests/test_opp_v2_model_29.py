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
from tests.opp_v2.scenarios.scenario_29 import grid_4x4_two_pickers_four_batches
from tests.opp_v2.tests.route_assertions import assert_batch_routes_cover_locations


class TestOPPModelGridEmptyBatch(OPPTestCase):
    def _solve_grid(
        self,
        N,
        a,
        y,
        cap_n,
        due_date_override=None,
        w1_override=None,
        w2_override=None,
        gamma_override=None,
        delta_override=None,
    ):
        V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x = (
            grid_4x4_two_pickers_four_batches()
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

    def _build_orders(self, V, extra_orders=None):
        order_locations = [
            ("O1", "V2"),
            ("O2", "V3"),
            ("O3", "V6"),
            ("O4", "V7"),
            ("O5", "V4"),
            ("O6", "V8"),
            ("O7", "V9"),
            ("O8", "V10"),
            ("O9", "V5"),
            ("O10", "V11"),
            ("O11", "V12"),
            ("O12", "V13"),
        ]

        orders = {order_id for order_id, _ in order_locations}
        if extra_orders:
            orders.update(extra_orders)

        a = {(n, v): 0 for n in orders for v in V}
        for order_id, location_id in order_locations:
            a[(order_id, location_id)] = 1

        return orders, a, order_locations

    def _build_y(self, orders, batches, assignments):
        y = {(n, b): 0 for n in orders for b in batches}
        for order_id, batch_id in assignments:
            y[(order_id, batch_id)] = 1
        return y

    def _build_required_by_batch(self, batches, order_locations, assignments):
        required = {b: set() for b in batches}
        location_by_order = {
            order_id: location_id for order_id, location_id in order_locations
        }
        for order_id, batch_id in assignments:
            location_id = location_by_order.get(order_id)
            if location_id is not None:
                required[batch_id].add(location_id)
        return required

    def test_grid_empty_batch_has_route(self):
        V, _, B, _, _, _, _, _, _, _ = grid_4x4_two_pickers_four_batches()

        orders, a, order_locations = self._build_orders(V)
        assignments = [
            ("O1", "B1"),
            ("O2", "B1"),
            ("O3", "B1"),
            ("O4", "B1"),
            ("O5", "B2"),
            ("O6", "B2"),
            ("O7", "B2"),
            ("O8", "B2"),
            ("O9", "B3"),
            ("O10", "B3"),
            ("O11", "B3"),
            ("O12", "B3"),
        ]
        y = self._build_y(orders, B, assignments)

        cap_n = {n: 1.0 for n in orders}
        result, model, location_graph, batches, _ = self._solve_grid(
            orders, a, y, cap_n
        )

        self.assertIn(result, ("optimal", "feasible"))

        required_by_batch = self._build_required_by_batch(
            batches, order_locations, assignments
        )

        routes_by_batch = assert_batch_routes_cover_locations(
            self,
            model.model,
            batches,
            location_graph.get_depot(),
            location_graph.get_final(),
            required_by_batch,
        )

        empty_route = routes_by_batch["B4"]
        self.assertEqual(empty_route[0], location_graph.get_depot())
        self.assertEqual(empty_route[-1], location_graph.get_final())

    def test_grid_all_orders_single_batch_tight_capacity(self):
        V, _, B, _, _, _, _, _, _, _ = grid_4x4_two_pickers_four_batches()

        orders, a, order_locations = self._build_orders(V)
        assignments = [(order_id, "B1") for order_id, _ in order_locations]
        y = self._build_y(orders, B, assignments)

        cap_n = {n: 0.5 for n in orders}
        result, model, location_graph, batches, _ = self._solve_grid(
            orders, a, y, cap_n
        )

        self.assertIn(result, ("optimal", "feasible"))

        required_by_batch = self._build_required_by_batch(
            batches, order_locations, assignments
        )

        routes_by_batch = assert_batch_routes_cover_locations(
            self,
            model.model,
            batches,
            location_graph.get_depot(),
            location_graph.get_final(),
            required_by_batch,
        )

        for batch_id in ("B2", "B3", "B4"):
            empty_route = routes_by_batch[batch_id]
            self.assertEqual(empty_route[0], location_graph.get_depot())
            self.assertEqual(empty_route[-1], location_graph.get_final())

    def test_grid_orders_without_locations(self):
        V, _, B, _, _, _, _, _, _, _ = grid_4x4_two_pickers_four_batches()

        extra_orders = {"O13", "O14", "O15"}
        orders, a, order_locations = self._build_orders(V, extra_orders=extra_orders)
        assignments = [
            ("O1", "B1"),
            ("O2", "B1"),
            ("O3", "B1"),
            ("O4", "B1"),
            ("O5", "B2"),
            ("O6", "B2"),
            ("O7", "B2"),
            ("O8", "B2"),
            ("O9", "B3"),
            ("O10", "B3"),
            ("O11", "B3"),
            ("O12", "B3"),
            ("O13", "B4"),
            ("O14", "B4"),
            ("O15", "B4"),
        ]
        y = self._build_y(orders, B, assignments)

        cap_n = {n: 1.0 for n in orders}
        result, model, location_graph, batches, _ = self._solve_grid(
            orders, a, y, cap_n
        )

        self.assertIn(result, ("optimal", "feasible"))

        required_by_batch = self._build_required_by_batch(
            batches, order_locations, assignments
        )

        routes_by_batch = assert_batch_routes_cover_locations(
            self,
            model.model,
            batches,
            location_graph.get_depot(),
            location_graph.get_final(),
            required_by_batch,
        )

        empty_route = routes_by_batch["B4"]
        self.assertEqual(empty_route[0], location_graph.get_depot())
        self.assertEqual(empty_route[-1], location_graph.get_final())


if __name__ == "__main__":
    unittest.main()
