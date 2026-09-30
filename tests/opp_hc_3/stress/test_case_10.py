import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.hc.solve_hc_3_model_dto import SolveHC3ModelDTO
from models.opp_hc_3 import OPPHillClimbing
from models.opp_hc_3.utils.output_handler import OutputHandler
from tests.infra.cases.opp_test_case import OPPTestCase
from tests.shared_scenarios.stress.scenario_custom_setup import scenario_custom_setup


class TestOPPModel(OPPTestCase):
    """
    Stress test 10: 25 orders per batch. 30 batches, 750 orders. 25x25 grid.

    Ported from opp_hc_2's stress test #10 (same scenario builder,
    same numeric parameters) so opp_hc_3 is exercised against the exact
    same instances as its sibling models -- required for the cross-model
    comparison in analysis/ (quality gap, time, and, where applicable,
    congestion) to be an apples-to-apples join.
    """

    def test_25_orders_per_batch_30_batches_25x25(self):
        opp_location_graph, V, B, N, y, a = scenario_custom_setup(
            30, 750, 25, 25
        )

        cap_n = {n: 10.0 for n in N}
        due_date = {n: 30.0 for n in N}

        cap_vehicle = 250.0
        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        params = SolveHC3ModelDTO()
        params.W_c = w1
        params.W_pen = w2
        params.W_e = gamma
        params.W_t = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.T_travel = beta_time
        params.T_setup = beta_setup
        params.T_pick = beta_picking
        params.T_due_n = due_date
        params.M = M
        params.B_nb = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = opp_location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time

        model = OPPHillClimbing(model_dto)
        model.attach(OutputHandler())

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
