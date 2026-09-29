import unittest
import sys
import os

from dtos.hc.solve_hc_model_dto import SolveHCModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from dtos import ModelDTO
from models.opp_hc_1 import OPPHillClimbing
from models.opp_hc_1.utils.output_handler import OutputHandler
from tests.infra.cases.opp_test_case import OPPTestCase

from tests.shared_scenarios.functional.one_mission_one_picker_grid_graph import (
    scenario_one_mission_one_picker_grid_graph,
)


class TestSingleOrderExceedsVehicle(OPPTestCase):
    """Medium: single order whose capacity exceeds vehicle capacity => infeasible"""

    opp_location_graph, V, B = scenario_one_mission_one_picker_grid_graph(6, 6)

    def test_single_order_exceeds_vehicle(self):
        N = {"O1"}
        a = {(n, v): 0 for n in N for v in self.V}
        # require visiting two distant locations to force travel
        a[("O1", "V2")] = 1
        a[("O1", "V18")] = 1

        y = {(n, b): 0 for n in N for b in self.B}
        # assign order to first batch
        first_b = sorted(self.B)[0]
        y[("O1", first_b)] = 1

        # set order capacity larger than vehicle
        cap_vehicle = 10.0
        cap_n = {"O1": 25.0}

        due_date = {"O1": 100.0}

        params = SolveHCModelDTO()
        params.W_c = 1.0
        params.W_pen = 1.0
        params.W_e = 1.0
        params.W_t = 1.0
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.T_travel = 0.5
        params.T_setup = 1.0
        params.T_pick = 1.0
        params.T_due_n = due_date
        params.M = 1000.0
        params.B_nb = y

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


if __name__ == "__main__":
    unittest.main()
