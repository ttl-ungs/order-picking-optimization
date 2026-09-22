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
import models.utils.solve_registry as solve_registry

from tests.opp_aco_3.opp_aco_3_test_case import OPPTestCaseACO3


class TestOPPAco3Cataclysm(OPPTestCaseACO3):
    """
    Test 4: the anti-stagnation "cataclysm" mechanism (Chen et al., 2013,
    Sec. 4.3; Lesch et al., 2023, Algorithm 2) is wired into opp_aco_3's
    DTO (SolveAco3ModelDTO.Max_iter_wo_improvement / Max_cataclysms) and
    README, but nothing in the suite ever forced it to actually fire.

    With Max_iter_wo_improvement=1, any iteration that fails to improve the
    global best triggers a pheromone reset -- on a small, easy instance run
    for enough iterations, at least one reset is all but guaranteed. This
    checks the reset actually happens (Cataclysms_used > 0 in the
    SolveResult opp_aco_3 registers), not just that the DTO field exists.
    """

    def _build_instance(self, max_iter_wo_improvement, max_cataclysms, max_it):
        model_dto = ModelDTO()
        model_dto.N = {"O1", "O2"}
        model_dto.B = {"B1"}
        model_dto.P = {"P1"}

        location_graph = OPPLocationGraph(depot_node="D", final_node="F")
        location_graph.add_vertex("D", "depot")
        location_graph.add_vertex("L1", "picking")
        location_graph.add_vertex("L2", "picking")
        location_graph.add_vertex("F", "final")

        distances = {
            ("D", "L1"): 4, ("D", "L2"): 6,
            ("L1", "L2"): 3,
            ("L1", "F"): 6, ("L2", "F"): 4,
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

        params.C_n = {"O1": 3, "O2": 3}
        params.C_v = 10.0

        params.A = {
            ("O1", "L1"): 1, ("O1", "L2"): 0,
            ("O2", "L1"): 0, ("O2", "L2"): 1,
        }

        params.B_time = 1.0
        params.B_setup = 1.0
        params.B_picking = 0.5
        params.S = {"L1": 0.0, "L2": 0.0}

        params.Dd = {"O1": 60.0, "O2": 60.0}
        params.M = 1000.0

        params.Bn = {("O1", "B1"): 1, ("O2", "B1"): 1}

        params.A_ants = 5
        params.Max_it = max_it
        params.Min_dwell = 0.0
        params.Max_iter_wo_improvement = max_iter_wo_improvement
        params.Max_cataclysms = max_cataclysms

        return model_dto, params

    def test_cataclysm_triggers_after_prolonged_stagnation(self):
        model_dto, params = self._build_instance(
            max_iter_wo_improvement=1, max_cataclysms=2, max_it=30
        )

        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())

        result, _ = model.solve(params)
        self.assertIn(result, ("optimal", "feasible"))

        solve_result = solve_registry.get_last()
        self.assertIsNotNone(solve_result, "Expected a SolveResult to have been registered.")

        cataclysms_used = solve_result.params.get("Cataclysms_used")
        self.assertIsNotNone(
            cataclysms_used,
            "SolveResult.params should carry Cataclysms_used (see opp_aco_3.py's "
            "solve_result construction).",
        )
        self.assertGreater(
            cataclysms_used,
            0,
            "With Max_iter_wo_improvement=1 over 30 iterations on a two-node "
            "instance, at least one cataclysm reset must have fired.",
        )
        self.assertLessEqual(
            cataclysms_used,
            2,
            "Cataclysms_used must never exceed the configured Max_cataclysms budget.",
        )


if __name__ == "__main__":
    unittest.main()
