import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from models.opp_aco_2.utils.output_handler import OutputHandler
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.opp_aco_2 import OPPAntColonyOptimization
from tests.opp_test_case import OPPTestCase
from tests.shared_scenarios.normal.scenario_13 import (
    bridge_graph_disconnected,
    bridge_graph_two_pickers_four_batches,
)
from tests.opp_v2.route_assertions import assert_batch_routes_cover_locations


class TestOPPACO2Bridge(OPPTestCase):
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
            V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
                bridge_graph_disconnected()
            )
        else:
            V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
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

        params = SolveAcoModelDTO()
        params.W_full = w1
        params.W_ea_ta = w2
        params.W_ea = gamma
        params.W_ta = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = beta_time
        params.B_setup = beta_setup
        params.B_picking = beta_picking
        params.Dd = due_date_by_order
        params.M = 1000.0
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)
        model.attach(OutputHandler())

        result, _ = model.solve(params)

        return result, model, location_graph, B, V

    def test_bridge_shared_locations_across_batches(self):
        V, B, _, _, _, _, _, _ = bridge_graph_two_pickers_four_batches()

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

    def test_bridge_tardiness_beta_picking(self):
        V, B, _, _, _, _, _, _, = bridge_graph_two_pickers_four_batches()

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
    def test_bridge_earliness_order_size(self):
        V, B, _, _, _, _, _, _ = bridge_graph_two_pickers_four_batches()

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
            due_date_override=5000.0,
            w1_override=1.0, # El tiempo de cumplimiento importa --> queremos terminar lo antes posible
            w2_override=1.0,
            gamma_override=0.0, # El adelanto no cuesta --> no forzamos que no haya delanto
            delta_override=1.0,
        )

        self.assertIn(result_small, ("optimal", "feasible"))
        result_large, model_large, _, _, _ = self._solve_bridge(
            N,
            a,
            y,
            cap_n_large,
            due_date_override=5000.0,  # El tiempo de cumplimiento importa --> queremos terminar lo antes posible
            w1_override=1.0,
            w2_override=1.0,
            gamma_override=0.0, # El adelanto no cuesta --> no forzamos que no haya delanto
            delta_override=1.0,
        )

        self.assertIn(result_large, ("optimal", "feasible"))
    def test_bridge_disconnected_required_location(self):
        V, B, _, _, _, _, _, _ = bridge_graph_disconnected()

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
