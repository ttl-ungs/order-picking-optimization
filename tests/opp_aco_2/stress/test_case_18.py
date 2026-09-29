import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from dtos.opp.model_dto import ModelDTO
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.opp_aco_2 import OPPAntColonyOptimization
from models.opp_aco_2.utils.output_handler import OutputHandler
from tests.infra.cases.opp_test_case import OPPTestCase
from tests.shared_scenarios.stress.scenario_custom_setup import scenario_custom_setup


class TestOPPModel(OPPTestCase):
    """
    Stress test 18 (intermediate, scenario G): 100 orders, 20 batches (density 5), 20x20 grid (400 nodes) -- same N/B as E/F, only V changes further.

    Added to widen the N/V/B sample for the Pearson-correlation section of
    analysis/ (previously only 8-11 OK points per model -- too few, and N/V
    moved together too often to tell their effects apart). Density kept in
    the 2-10 orders/batch range, well clear of the ~20-25+ zone that
    collapses ant/route construction regardless of hyperparameters (see
    analysis/README.md "Nota sobre ACO en estres"). Same scenario builder
    and parameters as opp_hc_2's equivalent (scenario G) so the
    instance is directly comparable across models.
    """

    def test_100_orders_20_batches_20x20(self):
        opp_location_graph, V, B, N, y, a = scenario_custom_setup(
            20, 100, 20, 20
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

        params = SolveAcoModelDTO()
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

        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())

        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
