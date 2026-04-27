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

    def test_grid_empty_batch_has_route(self):
        V, _, B, _, _, _, _, _, _, _ = grid_4x4_two_pickers_four_batches()

        N = {f"O{i}" for i in range(1, 13)}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "V2")] = 1
        a[("O2", "V3")] = 1
        a[("O3", "V6")] = 1
        a[("O4", "V7")] = 1
        a[("O5", "V4")] = 1
        a[("O6", "V8")] = 1
        a[("O7", "V9")] = 1
        a[("O8", "V10")] = 1
        a[("O9", "V5")] = 1
        a[("O10", "V11")] = 1
        a[("O11", "V12")] = 1
        a[("O12", "V13")] = 1

        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B1")] = 1
        y[("O3", "B1")] = 1
        y[("O4", "B1")] = 1
        y[("O5", "B2")] = 1
        y[("O6", "B2")] = 1
        y[("O7", "B2")] = 1
        y[("O8", "B2")] = 1
        y[("O9", "B3")] = 1
        y[("O10", "B3")] = 1
        y[("O11", "B3")] = 1
        y[("O12", "B3")] = 1

        cap_n = {n: 1.0 for n in N}
        result, model, location_graph, batches, _ = self._solve_grid(N, a, y, cap_n)

        self.assertIn(result, ("optimal", "feasible"))

        required_by_batch = {
            "B1": {"V2", "V3", "V6", "V7"},
            "B2": {"V4", "V8", "V9", "V10"},
            "B3": {"V5", "V11", "V12", "V13"},
            "B4": set(),
        }

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
