import unittest
import sys
import os

from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from models.opp_hc_4 import OPPHillClimbing
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO

from tests.opp_hc_4.tests.opp_hc_4_test_case import OPPTestCaseHC4


class TestOPPHillClimbing4Model6PreCheckUsesTightenedRoute(OPPTestCaseHC4):
    """
    Test HC4-6: Regression for the 2026-09-09 audit finding -- the
    cold-chain pre-check (batches_without_eligible_picker) used to run
    against the RAW nearest-neighbor construction's route, which is a
    heuristic, not the shortest path. A single order needs two required
    locations (R1, R2) reachable from the depot D and to the final F with
    distances engineered so that greedy nearest-neighbor (which picks R1
    first because D->R1 is the shortest single hop) produces a WORSE total
    route than visiting R2 first:

        D--1-->R1--3-->R2--5-->F   (nearest-neighbor order): distance 9
        D--3-->R2--3-->R1--1-->F   (optimal order):          distance 7

    T_frio_max = 8 sits strictly between these two: the pre-check must use
    the tightened (optimal, here) route -- not the raw nearest-neighbor
    one -- or it declares this genuinely feasible instance "infeasible".
    Verified empirically (2026-09-09) that reverting the fix
    (_two_opt_tighten_route made a no-op) makes this instance report
    "infeasible" instead of "optimal".
    """

    def _build_graph(self):
        graph = OPPLocationGraph(depot_node="D", final_node="F")
        graph.add_vertex("R1", "picking")
        graph.add_vertex("R2", "picking")

        graph.add_edge("D", "R1", 1)
        graph.add_edge("D", "R2", 3)
        graph.add_edge("R1", "R2", 3)
        graph.add_edge("R2", "R1", 3)
        graph.add_edge("R1", "F", 1)
        graph.add_edge("R2", "F", 5)

        return graph

    def test_nearest_neighbor_trap_is_not_reported_infeasible(self):
        location_graph = self._build_graph()
        V = location_graph.get_vertices()
        N = {"O1"}
        B = {"B1"}

        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "R1")] = 1
        a[("O1", "R2")] = 1

        y = {("O1", "B1"): 1}
        cap_n = {"O1": 1.0}

        params = SolveHC4ModelDTO()
        params.W_full = 1.0
        params.W_ea_ta = 0.0
        params.W_ea = 0.0
        params.W_ta = 0.0
        params.C_n = cap_n
        params.C_v = 10.0
        params.A = a
        params.B_time = 1.0  # so route_time == raw distance, for a clean bound
        params.B_setup = 0.0
        params.B_picking = 0.0
        params.Dd = {"O1": 1000.0}
        params.M = 1000.0
        params.Bn = y
        params.V_p = {"P1": 1.0}
        # Between the tightened (optimal here) route's distance (7) and the
        # raw nearest-neighbor construction's distance (9).
        params.T_frio_max = 8.0

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.P = {"P1"}
        model_dto.start_time = self.start_time
        model = OPPHillClimbing(model_dto)

        try:
            result, output_graph, solution_info = self.solve_and_capture(model, params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(
            result, ("optimal", "feasible"),
            "The nearest-neighbor construction's (suboptimal) route must not "
            "make the cold-chain pre-check declare this feasible instance infeasible.",
        )
        self.assert_cold_chain_respected(solution_info, params.T_frio_max)
        self.assertAlmostEqual(solution_info["batch_times"]["B1"], 7.0, places=4)


if __name__ == "__main__":
    unittest.main()
