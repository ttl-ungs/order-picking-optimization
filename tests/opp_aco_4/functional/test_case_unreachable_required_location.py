import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_aco_4 import OPPAntColonyOptimization
from tests.opp_aco_4.opp_aco_4_test_case import OPPTestCaseACO4
from tests.shared_scenarios.functional.scenario_13 import bridge_graph_disconnected


class TestOPPAntColonyOptimization4UnreachableRequiredLocation(OPPTestCaseACO4):
    """A batch that requires a location the graph cannot reach is reported infeasible."""

    def test_disconnected_required_location_is_infeasible(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = bridge_graph_disconnected()

        required_location = {
            "O1": "L2", "O2": "L8", "O3": "L9", "O4": "L3", "O5": "L10", "O6": "L11",
            "O7": "L4", "O8": "L8", "O9": "L10", "O10": "L5", "O11": "L9", "O12": "L11",
        }
        batch_of = {
            "O1": "B1", "O2": "B1", "O3": "B1", "O4": "B2", "O5": "B2", "O6": "B2",
            "O7": "B3", "O8": "B3", "O9": "B3", "O10": "B4", "O11": "B4", "O12": "B4",
        }
        N = set(required_location)
        a = {(n, v): 0 for n in N for v in V}
        for order, location in required_location.items():
            a[(order, location)] = 1
        y = {(n, b): 0 for n in N for b in B}
        for order, batch in batch_of.items():
            y[(order, batch)] = 1

        params = SolveAco4ModelDTO()
        params.W_c = w1
        params.W_pen = w2
        params.W_e = gamma
        params.W_t = delta
        params.C_n = {n: 2.0 for n in N}
        params.C_v = cap_vehicle
        params.A = a
        params.T_travel = 0.5
        params.T_setup = 1.0
        params.T_pick = 1.0
        params.T_due_n = {n: 25.0 for n in N}
        params.M = 1000.0
        params.B_nb = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time

        result, _ = OPPAntColonyOptimization(model_dto).solve(params)

        self.assertEqual(result, "infeasible")


if __name__ == "__main__":
    unittest.main()
