import unittest
import sys
import os

from dtos.hc.solve_hc_model_dto import SolveHCModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from dtos import ModelDTO
from models.opp_hc import OPPHillClimbing
from models.opp_hc.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase

from tests.shared_scenarios.normal.multigrid_graph import (
    multigrid_5x5_3x3_five_pickers_twelve_batches,
)


class TestFractionalZeroCapacities(OPPTestCase):
    """Medium: mix of zero and fractional capacities across orders."""

    V, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle = (
        multigrid_5x5_3x3_five_pickers_twelve_batches()
    )

    def test_fractional_and_zero_capacities_infeasible(self):
        N = {"O1", "O2", "O3", "O4"}
        a = {(n, v): 0 for n in N for v in self.V}

        a[("O1", "V2")] = 1
        a[("O2", "V3")] = 1
        a[("O3", "V4")] = 1
        a[("O4", "V5")] = 1

        y = {(n, b): 0 for n in N for b in self.B}
        batches = sorted(self.B)
        y[("O1", batches[0])] = 1
        y[("O2", batches[0])] = 1
        y[("O3", batches[1])] = 1
        y[("O4", batches[1])] = 1

        cap_n = {"O1": 0.0, "O2": 1.5, "O3": 2.25, "O4": 3.0}
        cap_vehicle = 5.0

        params = SolveHCModelDTO()
        params.W_full = 1.0
        params.W_ea_ta = 1.0
        params.W_ea = 1.0
        params.W_ta = 1.0
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = 0.5
        params.B_setup = 1.0
        params.B_picking = 1.0
        params.Dd = {n: 100.0 for n in N}
        params.M = 1000.0
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = self.opp_location_graph
        model_dto.B = self.B
        model_dto.start_time = self.start_time
        model = OPPHillClimbing(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)
        model.attach(OutputHandler())

        result, _ = model.solve(params)

        self.assertEqual(result, "infeasible")

    def test_fractional_and_zero_capacities_feasible(self):
        N = {"O1", "O2", "O3", "O4"}
        a = {(n, v): 0 for n in N for v in self.V}

        a[("O1", "V2")] = 1
        a[("O2", "V3")] = 1
        a[("O3", "V4")] = 1
        a[("O4", "V5")] = 1

        y = {(n, b): 0 for n in N for b in self.B}
        batches = sorted(self.B)
        y[("O1", batches[0])] = 1
        y[("O2", batches[0])] = 1
        y[("O3", batches[1])] = 1
        y[("O4", batches[1])] = 1

        cap_n = {"O1": 0.0, "O2": 1.5, "O3": 2.25, "O4": 3.0}
        cap_vehicle = 6.0

        params = SolveHCModelDTO()
        params.W_full = 1.0
        params.W_ea_ta = 1.0
        params.W_ea = 1.0
        params.W_ta = 1.0
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = 0.5
        params.B_setup = 1.0
        params.B_picking = 1.0
        params.Dd = {n: 100.0 for n in N}
        params.M = 1000.0
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = self.opp_location_graph
        model_dto.B = self.B
        model_dto.start_time = self.start_time
        model = OPPHillClimbing(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)
        model.attach(OutputHandler())

        result, _ = model.solve(params)

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
