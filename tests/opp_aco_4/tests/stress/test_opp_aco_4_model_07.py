import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO
from models.opp_aco_4 import OPPAntColonyOptimization
from models.opp_aco_4.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.opp_hc_2.scenarios.stress.scenario_custom_setup import scenario_custom_setup


# Ported from opp_aco_2's test_opp_aco_2_model_07.py for opp_aco_4/analysis parity (V_p unset, T_frio_max default +inf -> pure equivalence).
class TestOPPModel(OPPTestCase):
    """
    Stress test 07: Infeasible capacity. 10 orders, 2 batches. 4x4 grid.

    Ported from opp_hc_2's stress test #07 (same scenario builder,
    same numeric parameters) so opp_aco_2 is exercised against the exact
    same instances as its sibling models -- required for the cross-model
    comparison in analysis/ (quality gap, time, and, where applicable,
    congestion) to be an apples-to-apples join.
    """

    def test_infeasible_capacity(self):
        opp_location_graph, V, B, N, y, a = scenario_custom_setup(
            2, 10, 4, 4
        )

        cap_n = {n: 10.0 for n in N}
        due_date = {n: 30.0 for n in N}

        cap_vehicle = 40.0
        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        params = SolveAco4ModelDTO()
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
        params.Dd = due_date
        params.M = M
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = opp_location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time

        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("infeasible", "infeasible_or_unbounded"))


if __name__ == "__main__":
    unittest.main()
