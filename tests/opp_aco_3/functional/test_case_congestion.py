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


class TestOPPAco3Congestion(OPPTestCaseACO3):
    """
    Test 2: Congestion between two concurrent pickers.

    Two pickers, two batches, and a warehouse layout where BOTH batches must
    pass through the same bottleneck location (L2, with a high service
    time). This is the scenario the ACO literature review targeted (Chen et
    al., 2013 - congestion between order pickers): purpose is to verify that
    opp_aco_3 actually detects and prices the resulting wait, unlike
    opp_aco_2 which parallelizes pickers with no notion of shared space.
    """

    def _build_bottleneck_instance(self):
        model_dto = ModelDTO()
        model_dto.N = {"O1", "O2", "O3", "O4"}
        model_dto.B = {"B1", "B2"}
        model_dto.P = {"P1", "P2"}

        location_graph = OPPLocationGraph(depot_node="D", final_node="F")
        location_graph.add_vertex("D", "depot")
        location_graph.add_vertex("L1", "picking")
        location_graph.add_vertex("L2", "picking")  # bottleneck
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
        params.W_full = 1.0
        params.W_ea_ta = 1.0
        params.W_ea = 0.1
        params.W_ta = 0.5

        params.C_n = {"O1": 3, "O2": 3, "O3": 3, "O4": 3}
        params.C_v = 10.0

        # Both batches require L2 - the shared bottleneck.
        params.A = {
            ("O1", "L1"): 1, ("O1", "L2"): 1, ("O1", "L3"): 0,
            ("O2", "L1"): 0, ("O2", "L2"): 1, ("O2", "L3"): 0,
            ("O3", "L1"): 0, ("O3", "L2"): 1, ("O3", "L3"): 1,
            ("O4", "L1"): 0, ("O4", "L2"): 1, ("O4", "L3"): 0,
        }

        params.B_time = 1.0
        params.B_setup = 2.0
        params.B_picking = 0.5
        params.S = {"L1": 1.0, "L2": 6.0, "L3": 1.0}

        params.Dd = {"O1": 60.0, "O2": 60.0, "O3": 60.0, "O4": 60.0}
        params.M = 1000.0

        params.Bn = {
            ("O1", "B1"): 1, ("O2", "B1"): 1,
            ("O3", "B2"): 1, ("O4", "B2"): 1,
        }

        params.A_ants = 15
        params.Max_it = 40
        params.Min_dwell = 1.0

        return model_dto, params

    def test_congestion_wait_is_detected_and_priced(self):
        model_dto, params = self._build_bottleneck_instance()

        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())

        result, output_graph, solution_info = self.solve_and_capture(model, params)

        self.assertTrue(
            result in ("optimal", "feasible"),
            "The model did not find a solution for the bottleneck scenario.",
        )

        # Both batches are still assigned and sequenced consistently.
        self.assert_every_batch_has_one_picker(solution_info, model_dto.P)
        self.assert_no_time_overlap(solution_info, model_dto.P)
        self.assert_congestion_waits_non_negative(solution_info)
        self.assert_objective_consistent_with_congestion(solution_info)

        # The core assertion: since both batches are forced through the same
        # capacity-1 bottleneck node (L2) at essentially the same time, the
        # congestion mechanism must detect a real, positive wait somewhere.
        total_wait = sum(solution_info.get("batch_congestion_wait", {}).values())
        self.assertGreater(
            total_wait,
            0.0,
            "Expected a positive congestion wait for two pickers sharing bottleneck L2, got 0.",
        )
        self.assertAlmostEqual(
            total_wait, solution_info.get("congestion_objective_value", 0.0), places=6
        )


if __name__ == "__main__":
    unittest.main()
