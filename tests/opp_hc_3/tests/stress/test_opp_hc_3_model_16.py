import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.hc.solve_hc_3_model_dto import SolveHC3ModelDTO
from models.opp_hc_3 import OPPHillClimbing
from models.opp_hc_3.utils.output_handler import OutputHandler
from tests.opp_test_case import OPPTestCase
from tests.shared_scenarios.stress.scenario_custom_setup import scenario_custom_setup


class TestOPPModel(OPPTestCase):
    """
    Stress test 16 (intermediate, scenario E): 100 orders, 20 batches (density 5), 10x10 grid (100 nodes) -- same V as scenario D, only N/B change.

    Added to widen the N/V/B sample for the Pearson-correlation section of
    analysis/ (previously only 8-11 OK points per model -- too few, and N/V
    moved together too often to tell their effects apart). Density kept in
    the 2-10 orders/batch range, well clear of the ~20-25+ zone that
    collapses ant/route construction regardless of hyperparameters (see
    analysis/README.md "Nota sobre ACO en estres"). Same scenario builder
    and parameters as opp_hc_2's equivalent (scenario E) so the
    instance is directly comparable across models.
    """

    def test_100_orders_20_batches_10x10(self):
        opp_location_graph, V, B, N, y, a = scenario_custom_setup(
            20, 100, 10, 10
        )

        cap_n = {n: 10.0 for n in N}
        due_date = {n: 30.0 for n in N}

        cap_vehicle = 200.0
        w1 = 9.0
        w2 = 1.0
        gamma = 1.0
        delta = 1.0

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        params = SolveHC3ModelDTO()
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

        model = OPPHillClimbing(model_dto)
        model.attach(OutputHandler())

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
