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


class TestOPPAntColonyOptimization4Model7SoftColdChainProtectsSiblings(OPPTestCaseACO4):
    """
    Test ACO4-7: Regression for the 2026-09-09 audit finding (part 2) --
    cold chain used to be a hard check inside ConstraintsValidator.
    validate_solution(), so a SINGLE cold-chain-tight batch made the
    validator reject the WHOLE ant solution, every ant, every iteration --
    starving pheromone updates for every OTHER (easy) batch too, and
    potentially converging to "infeasible" despite the upfront pre-check
    confirming a compliant assignment exists.

    Two independent batches on the same single-picker instance:
    - B1 is the "trap" from test_case_pre_check_uses_tightened_route (nearest-neighbor
      construction is ~94% likely to build the cold-chain-VIOLATING order;
      only ~6% of constructions land on the compliant one).
    - B2 is trivially easy (a single required location, always compliant).

    Before the fix: whenever an ant's B1 came out non-compliant (~94% of
    the time), the WHOLE solution -- B2 included -- was discarded, so B2's
    route pheromone almost never got to update either, on top of B1's own
    problem. After the fix (cold chain is a soft per-batch penalty during
    search, hard only on the reported final answer -- see
    models/opp_aco_4/opp_aco_4.py and utils/constraints_validator.py's
    module docstrings), B2 keeps depositing pheromone normally in every
    ant that clears the (unrelated) hard constraints, regardless of what
    B1 does, and B1 only reinforces its own edges on the iterations where
    it happens to be built compliant.
    """

    def _build_graph(self):
        graph = OPPLocationGraph(depot_node="D", final_node="F")
        graph.add_vertex("R1", "picking")
        graph.add_vertex("R2", "picking")
        graph.add_vertex("E1", "picking")

        # B1's trap (same distances as test_case_pre_check_uses_tightened_route).
        graph.add_edge("D", "R1", 1)
        graph.add_edge("D", "R2", 3)
        graph.add_edge("R1", "R2", 3)
        graph.add_edge("R2", "R1", 3)
        graph.add_edge("R1", "F", 1)
        graph.add_edge("R2", "F", 5)

        # B2: trivially easy, single required location.
        graph.add_edge("D", "E1", 1)
        graph.add_edge("E1", "F", 1)

        return graph

    def test_easy_batch_is_not_starved_by_the_tight_one(self):
        location_graph = self._build_graph()
        V = location_graph.get_vertices()
        N = {"O1", "O2"}
        B = {"B1", "B2"}

        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "R1")] = 1
        a[("O1", "R2")] = 1
        a[("O2", "E1")] = 1

        y = {
            ("O1", "B1"): 1, ("O1", "B2"): 0,
            ("O2", "B1"): 0, ("O2", "B2"): 1,
        }
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
        params.B_setup = 0.0
        params.B_picking = 0.0
        params.Dd = {n: 1000.0 for n in N}
        params.M = 1000.0
        params.Bn = y
        params.V_p = {"P1": 1.0}
        # Tight for B1 (needs the ~6%-likely order), trivially satisfied by
        # B2 (distance 2 for D->E1->F either way).
        params.T_frio_max = 8.0
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

        self.assertIn(
            result, ("optimal", "feasible"),
            "A cold-chain-tight batch must not make the solver fail to find "
            "an assignment for an easy sibling batch either.",
        )
        self.assert_cold_chain_respected(solution_info, params.T_frio_max)
        self.assertAlmostEqual(solution_info["batch_times"]["B1"], 7.0, places=4)
        self.assertAlmostEqual(solution_info["batch_times"]["B2"], 2.0, places=4)


if __name__ == "__main__":
    unittest.main()
