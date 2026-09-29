import unittest

import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_aco_3 import OPPAntColonyOptimization
from models.opp_aco_3.utils.output_handler import OutputHandler
from dtos.opp.model_dto import ModelDTO
from dtos.aco.solve_aco_3_model_dto import SolveAco3ModelDTO
from models.base.opp_location_graph import OPPLocationGraph

from tests.opp_aco_3.opp_aco_3_test_case import OPPTestCaseACO3


class TestOPPAco3ZeroCongestionEquivalence(OPPTestCaseACO3):
    """
    Test 3: the same bottleneck instance as test #02
    (test_congestion_wait_is_detected_and_priced), but with a single
    picker instead of two.

    opp_aco_3's README claims the congestion + multi-pheromone mechanism is
    "purely additive to the cost function": a solution with no contention
    (e.g. a single picker) must reduce exactly to opp_aco_2's behaviour --
    zero congestion wait. Test #02 only proves the mechanism fires when
    there IS contention; this is the other half of that claim.
    """

    def _build_single_picker_instance(self):
        model_dto = ModelDTO()
        model_dto.N = {"O1", "O2", "O3", "O4"}
        model_dto.B = {"B1", "B2"}
        model_dto.P = {"P1"}  # single picker -> both batches run sequentially

        location_graph = OPPLocationGraph(depot_node="D", final_node="F")
        location_graph.add_vertex("D", "depot")
        location_graph.add_vertex("L1", "picking")
        location_graph.add_vertex("L2", "picking")  # bottleneck, but nobody to share it with
        location_graph.add_vertex("L3", "picking")
        location_graph.add_vertex("F", "final")

        distances = {
            ("D", "L1"): 5, ("D", "L2"): 8, ("D", "L3"): 8,
            ("L1", "L2"): 3, ("L2", "L3"): 3,
            ("L1", "F"): 8, ("L2", "F"): 5, ("L3", "F"): 8,
        }
        for (i, j), dist in distances.items():
            location_graph.add_edge(i, j, dist)
            location_graph.add_edge(j, i, dist)

        model_dto.location_graph = location_graph
        model_dto.start_time = self.start_time

        params = SolveAco3ModelDTO()
        params.W_c = 1.0
        params.W_pen = 1.0
        params.W_e = 0.1
        params.W_t = 0.5

        params.C_n = {"O1": 3, "O2": 3, "O3": 3, "O4": 3}
        params.C_v = 10.0

        params.A = {
            ("O1", "L1"): 1, ("O1", "L2"): 1, ("O1", "L3"): 0,
            ("O2", "L1"): 0, ("O2", "L2"): 1, ("O2", "L3"): 0,
            ("O3", "L1"): 0, ("O3", "L2"): 1, ("O3", "L3"): 1,
            ("O4", "L1"): 0, ("O4", "L2"): 1, ("O4", "L3"): 0,
        }

        params.T_travel = 1.0
        params.T_setup = 2.0
        params.T_pick = 0.5
        params.S = {"L1": 1.0, "L2": 6.0, "L3": 1.0}

        params.T_due_n = {"O1": 60.0, "O2": 60.0, "O3": 60.0, "O4": 60.0}
        params.M = 1000.0

        params.B_nb = {
            ("O1", "B1"): 1, ("O2", "B1"): 1,
            ("O3", "B2"): 1, ("O4", "B2"): 1,
        }

        params.A_ants = 15
        params.Max_it = 40
        params.Min_dwell = 1.0

        return model_dto, params

    def test_single_picker_has_zero_congestion_wait(self):
        model_dto, params = self._build_single_picker_instance()

        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())

        result, _, solution_info = self.solve_and_capture(model, params)

        self.assertIn(result, ("optimal", "feasible"))

        self.assert_congestion_waits_non_negative(solution_info)
        self.assert_objective_consistent_with_congestion(solution_info)

        total_wait = sum(solution_info.get("batch_congestion_wait", {}).values())
        self.assertEqual(
            total_wait,
            0.0,
            "A single picker has nothing to contend with -- congestion wait "
            "must be exactly zero (the 'purely additive' equivalence with "
            "opp_aco_2 this model's README claims).",
        )


if __name__ == "__main__":
    unittest.main()
