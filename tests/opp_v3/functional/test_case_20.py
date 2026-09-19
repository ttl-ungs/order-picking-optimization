import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from dtos import SolveModelDTO, ModelDTO
from models.opp_v3.opp_model_v3 import OPPModelV3
from models.opp_v3.utils.output_handler import OutputHandler
from tests.support.opp_test_case import OPPTestCase

from tests.shared_scenarios.functional.three_missions_two_pickers_grid_graph import (
    scenario_three_missions_two_pickers_two_periods_grid_graph,
)


class TestEmptyBatch(OPPTestCase):
    """Medium: a setup with one intentionally empty batch among others."""

    opp_location_graph, V, B = (
        scenario_three_missions_two_pickers_two_periods_grid_graph(5, 5)
    )

    def test_one_empty_batch_allowed(self):
        N = {f"O{i}" for i in range(1, 7)}
        a = {(n, v): 0 for n in N for v in self.V}

        # assign simple locations
        assigns = list(zip(sorted(N), ["V2", "V3", "V6", "V7", "V10", "V11"]))
        for n, v in assigns:
            a[(n, v)] = 1

        y = {(n, b): 0 for n in N for b in self.B}
        # fill all but one batch
        batches = sorted(self.B)
        for idx, n in enumerate(sorted(N)):
            y[(n, batches[idx // 2])] = 1

        # make last batch empty explicitly
        cap_vehicle = 50
        cap_n = {n: 5.0 for n in N}

        params = SolveModelDTO()
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
        model = OPPModelV3(model_dto)
        model.attach(OutputHandler())

        result, _ = model.solve(params)

        self.assertIn(result, ("optimal", "feasible"))


if __name__ == "__main__":
    unittest.main()
