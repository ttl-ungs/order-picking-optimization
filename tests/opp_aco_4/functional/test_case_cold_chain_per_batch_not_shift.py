import unittest
import sys
import os

from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_aco_4 import OPPAntColonyOptimization
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO

from tests.opp_aco_4.opp_aco_4_test_case import OPPTestCaseACO4


class TestOPPAntColonyOptimization4ColdChainPerBatchNotShift(OPPTestCaseACO4):
    """
    Ported from opp_v5_1_mono's test_case_35
    (TestOPPMonoColdChainCoverage.test_cold_limit_applies_to_each_batch_not_the_whole_shift):
    T_frio_max bounds EACH batch's own execution time (t_exec_pb), not a
    picker's cumulative time across batches. A single picker running two
    back-to-back batches, each individually within the limit, must stay
    eligible even though the SECOND batch's absolute completion time ends
    up past T_frio_max.

    Same geometry as test_case_cold_chain_boundary.py: t_exec_pb(P1) =
    2.0 + 12.0/1.0 = 14.0 exactly for either batch. T_frio_max = 14.0 (the
    boundary): both batches individually comply, so P1 runs both, with the
    second completing at 28.0 -- past T_frio_max, which is correct.
    """

    def test_cold_limit_applies_to_each_batch_not_the_whole_shift(self):
        location_graph = OPPLocationGraph(depot_node="D", final_node="F")
        location_graph.add_vertex("M", "picking")
        location_graph.add_edge("D", "M", 6.0)
        location_graph.add_edge("M", "F", 6.0)

        V = location_graph.get_vertices()
        N = {"O1", "O2"}
        B = {"B1", "B2"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "M")] = 1
        a[("O2", "M")] = 1
        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        cap_n = {"O1": 1.0, "O2": 1.0}

        params = SolveAco4ModelDTO()
        params.W_full = 1.0
        params.W_ea_ta = 0.0
        params.W_ea = 0.0
        params.W_ta = 0.0
        params.C_n = cap_n
        params.C_v = 10.0
        params.A = a
        params.B_time = 1.0
        params.B_setup = 1.0
        params.B_picking = 1.0
        params.Dd = {"O1": 1000.0, "O2": 1000.0}
        params.M = 1000.0
        params.Bn = y
        params.V_p = {"P1": 1.0}
        params.T_frio_max = 14.0
        params.Seed = 1

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.P = {"P1"}
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)

        try:
            result, output_graph, solution_info = self.solve_and_capture(model, params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))
        self.assert_every_batch_has_one_picker(solution_info, {"P1"})
        self.assert_cold_chain_respected(solution_info, params.T_frio_max)
        self.assertEqual(
            solution_info["picker_assignments"], {"B1": "P1", "B2": "P1"}
        )
        self.assertAlmostEqual(solution_info["batch_times"]["B1"], 14.0, places=4)
        self.assertAlmostEqual(solution_info["batch_times"]["B2"], 14.0, places=4)

        completions = solution_info["batch_completions"]
        ends = sorted(completions[b] - self.start_time for b in B)
        self.assertAlmostEqual(ends[0], 14.0, places=4)
        self.assertAlmostEqual(ends[1], 28.0, places=4)
        self.assertGreater(
            ends[1], params.T_frio_max,
            "The second batch's absolute completion may exceed T_frio_max: "
            "the limit bounds each batch's own execution time, not the "
            "picker's cumulative shift.",
        )


if __name__ == "__main__":
    unittest.main()
