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


class TestOPPAntColonyOptimization4ColdChainBoundary(OPPTestCaseACO4):
    """
    Ported from opp_v5_1_mono's test_case_34
    (TestOPPMonoColdChainEdgeCases.test_picker_exactly_at_the_cold_chain_limit_is_still_eligible):
    T_cold set to EXACTLY the picker's T_exec_pb. PB_elig uses `<=`, so
    this must still be eligible -- not excluded by an off-by-one at the
    boundary.

    Single order at M (distance D->M->F = 12.0, T_travel=1.0): fixed_time =
    T_setup(1.0) + T_pick(1.0)*C_n["O1"](1.0) = 2.0, so
    T_exec_pb(P1) = 2.0 + 12.0/1.0 = 14.0 exactly.
    """

    def test_picker_exactly_at_the_cold_chain_limit_is_still_eligible(self):
        location_graph = OPPLocationGraph(depot_node="D", final_node="F")
        location_graph.add_vertex("M", "picking")
        location_graph.add_edge("D", "M", 6.0)
        location_graph.add_edge("M", "F", 6.0)

        V = location_graph.get_vertices()
        N = {"O1"}
        B = {"B1"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "M")] = 1
        y = {("O1", "B1"): 1}
        cap_n = {"O1": 1.0}

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
        params.T_due_n = {"O1": 1000.0}
        params.M = 1000.0
        params.B_nb = y
        params.V_p = {"P1": 1.0}
        params.T_cold = 14.0
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
        self.assert_cold_chain_respected(solution_info, params.T_cold)
        self.assertEqual(solution_info["picker_assignments"]["B1"], "P1")
        self.assertAlmostEqual(solution_info["batch_times"]["B1"], 14.0, places=4)


if __name__ == "__main__":
    unittest.main()
