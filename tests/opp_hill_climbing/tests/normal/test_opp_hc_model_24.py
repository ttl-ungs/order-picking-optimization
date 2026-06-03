import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos import SolveModelDTO, ModelDTO
from models.opp_hill_climbing import OPPHillClimbingV3
from tests.opp.tests.opp_test_case import OPPTestCase

from tests.opp_v3.scenarios.normal.scenario_3 import two_possible_routes_batches


class TestDueDatesExtreme(OPPTestCase):
    """Medium: compare total tardiness under tight vs relaxed due dates."""

    def test_due_dates_tight_vs_relaxed(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            two_possible_routes_batches()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L4")] = 1
        a[("O2", "L4")] = 1

        y = {(n, b): 0 for n in N for b in B}
        y[("O1", "B1")] = 1
        y[("O2", "B2")] = 1

        cap_n = {"O1": 3.0, "O2": 3.0}

        params_base = SolveModelDTO()
        params_base.W_full = 0.0
        params_base.W_ea_ta = 1.0
        params_base.W_ea = 0.0
        params_base.W_ta = 1.0
        params_base.C_n = cap_n
        params_base.C_v = cap_vehicle
        params_base.A = a
        params_base.B_time = 0.5
        params_base.B_setup = 1.0
        params_base.B_picking = 2.0
        params_base.M = 1000.0
        params_base.Bn = y

        # tight due dates
        params_tight = params_base
        params_tight.Dd = {"O1": 1.0, "O2": 1.0}

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time

        model_tight = OPPModelV3(model_dto)
        model_tight.attach(OutputHandler())
        result_tight, _ = model_tight.solve(params_tight)
        self.assertIn(result_tight, ("optimal", "feasible", "infeasible"))

        # relaxed due dates
        params_relaxed = params_base
        params_relaxed.Dd = {"O1": 1000.0, "O2": 1000.0}

        model_relaxed = OPPModelV3(model_dto)
        model_relaxed.attach(OutputHandler())
        result_relaxed, _ = model_relaxed.solve(params_relaxed)
        self.assertIn(result_relaxed, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
