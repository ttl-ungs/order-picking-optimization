import os
import sys
import unittest

from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from models.opp_hc_4.utils.output_handler import OutputHandler
from models.opp_hc_4 import OPPHillClimbing
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.shared_scenarios.normal.scenario_19 import longer_single_mission_route
from tests.opp_v2.tests.route_assertions import assert_route_covers_orders


# Ported from opp_hc_2's test_opp_hc_2_model_19.py for opp_hc_4/analysis parity (V_p unset, T_frio_max default +inf -> pure equivalence).
class TestOPPHillClimbing2(OPPTestCase):
    def _solve_longer_route(
        self,
        due_date,
        w1_override=None,
        w2_override=None,
        gamma_override=None,
        delta_override=None,
        duplicate_location=False,
    ):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
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

        params = SolveHC4ModelDTO()
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
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time
        model = OPPHillClimbing(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)
        model.attach(OutputHandler())

        result, output_graph = model.solve(params)

        return result, output_graph, model, location_graph

    def test_longer_single_mission_route(self):
        try:
            result, output_graph, _, _ = self._solve_longer_route(due_date=25.0)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertEqual(result, "optimal")
        assert_route_covers_orders(
            self, output_graph, {"L2", "L3", "L4", "L5", "L6", "L7"}
        )

    def test_longer_single_mission_penalties(self):
        try:
            result_low, _, _, _ = self._solve_longer_route(
                due_date=0.0,
                w1_override=0.0,
                w2_override=1.0,
                gamma_override=0.0,
                delta_override=1.0,
            )
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result_low, ("optimal", "feasible"))

        try:
            result_high, _, _, _ = self._solve_longer_route(
                due_date=100.0,
                w1_override=0.0,
                w2_override=1.0,
                gamma_override=0.0,
                delta_override=1.0,
            )
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result_high, ("optimal", "feasible"))

    def test_longer_single_mission_duplicate_location(self):
        try:
            result, _, _, _ = self._solve_longer_route(
                due_date=25.0,
                duplicate_location=True,
            )
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()

