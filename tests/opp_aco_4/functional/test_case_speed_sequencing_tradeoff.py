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


class TestOPPAntColonyOptimization4SpeedSequencingTradeoff(OPPTestCaseACO4):
    """
    Ported from opp_v5_1_mono's test_case_36 (TestOPPMonoSpeedCoverage):
    picker speed beyond the single-batch "which picker gets it" check
    (test_case_picker_speed.py) -- how speed trades off against
    sequencing two batches across two pickers, and how it reaches the
    tardiness term.

    Geometry: two single-order batches, both requiring location M
    (distance D->M->F = 14.0, T_travel=1.0). fixed_time =
    T_setup(1.0) + T_pick(1.0)*C_n(1.0) = 2.0, so
    T_exec_pb = 2.0 + 14.0/V_p.
    """

    def _graph(self):
        location_graph = OPPLocationGraph(depot_node="D", final_node="F")
        location_graph.add_vertex("M", "picking")
        location_graph.add_edge("D", "M", 7.0)
        location_graph.add_edge("M", "F", 7.0)
        return location_graph

    def _two_batches_params(self, fast_speed):
        location_graph = self._graph()
        V = location_graph.get_vertices()
        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "M")] = 1
        a[("O2", "M")] = 1

        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        cap_n = {"O1": 1.0, "O2": 1.0}

        params = SolveAco4ModelDTO()
        params.W_c = 1.0
        params.W_pen = 0.0
        params.W_e = 0.0
        params.W_t = 0.0
        params.C_n = cap_n
        params.C_v = 10.0
        params.A = a
        params.T_travel = 1.0
        params.T_setup = 1.0
        params.T_pick = 1.0
        params.T_due_n = {"O1": 1000.0, "O2": 1000.0}
        params.M = 1000.0
        params.B_nb = y
        params.V_p = {"P_slow": 1.0, "P_fast": fast_speed}
        params.T_cold = float("inf")
        params.Seed = 1

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = {"B1", "B2"}
        model_dto.P = {"P_slow", "P_fast"}
        model_dto.start_time = self.start_time
        return model_dto, params

    def test_fast_picker_takes_both_batches_when_four_times_faster(self):
        """T_exec_pb(P_fast, V_p=4) = 2.0 + 14.0/4.0 = 5.5. Queueing both
        batches on it completes at 5.5 and 11.0, cheaper than giving one to
        P_slow (T_exec_pb = 2.0 + 14.0 = 16.0)."""
        model_dto, params = self._two_batches_params(fast_speed=4.0)
        model = OPPAntColonyOptimization(model_dto)

        try:
            result, output_graph, solution_info = self.solve_and_capture(model, params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))
        self.assertEqual(
            solution_info["picker_assignments"],
            {"B1": "P_fast", "B2": "P_fast"},
        )
        self.assert_no_time_overlap(solution_info, {"P_slow", "P_fast"})

        completions = solution_info["batch_completions"]
        ends = sorted(completions[b] - self.start_time for b in model_dto.B)
        self.assertAlmostEqual(ends[0], 5.5, places=4)
        self.assertAlmostEqual(ends[1], 11.0, places=4)

    def test_batches_are_split_when_fast_picker_is_only_twice_as_fast(self):
        """T_exec_pb(P_fast, V_p=2) = 2.0 + 14.0/2.0 = 9.0. Splitting the
        batches (9.0 + 16.0 = 25.0) beats queueing both on P_fast
        (9.0 + 18.0 = 27.0)."""
        model_dto, params = self._two_batches_params(fast_speed=2.0)
        model = OPPAntColonyOptimization(model_dto)

        try:
            result, output_graph, solution_info = self.solve_and_capture(model, params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))
        assignments = solution_info["picker_assignments"]
        self.assertEqual(set(assignments.values()), {"P_slow", "P_fast"})
        self.assert_no_time_overlap(solution_info, {"P_slow", "P_fast"})

        completions = solution_info["batch_completions"]
        by_picker = {
            picker: completions[batch] - self.start_time
            for batch, picker in assignments.items()
        }
        self.assertAlmostEqual(by_picker["P_fast"], 9.0, places=4)
        self.assertAlmostEqual(by_picker["P_slow"], 16.0, places=4)

    def test_tardiness_uses_the_speed_scaled_route_time(self):
        """A picker at half speed needs 2.0 + 14.0/0.5 = 30.0 for a batch
        due at 20.0: exactly 10.0 late, not early."""
        location_graph = self._graph()
        V = location_graph.get_vertices()
        N = {"O1"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "M")] = 1
        y = {("O1", "B1"): 1}
        cap_n = {"O1": 1.0}

        params = SolveAco4ModelDTO()
        params.W_c = 10.0
        params.W_pen = 1.0
        params.W_e = 1.0
        params.W_t = 1.0
        params.C_n = cap_n
        params.C_v = 10.0
        params.A = a
        params.T_travel = 1.0
        params.T_setup = 1.0
        params.T_pick = 1.0
        params.T_due_n = {"O1": 20.0}
        params.M = 1000.0
        params.B_nb = y
        params.V_p = {"P_only": 0.5}
        params.T_cold = float("inf")
        params.Seed = 1

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = {"B1"}
        model_dto.P = {"P_only"}
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)

        try:
            result, output_graph, solution_info = self.solve_and_capture(model, params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))
        self.assertAlmostEqual(solution_info["batch_times"]["B1"], 30.0, places=4)
        self.assertAlmostEqual(solution_info["tardiness"]["O1"] - self.start_time, 10.0, places=4)
        self.assertAlmostEqual(solution_info["earliness"]["O1"], 0.0, places=4)


if __name__ == "__main__":
    unittest.main()
