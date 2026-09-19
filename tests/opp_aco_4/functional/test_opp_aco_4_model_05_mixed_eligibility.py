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


class TestOPPAntColonyOptimization4Model5MixedEligibility(OPPTestCaseACO4):
    """
    Test ACO4-5: Mixed cold-chain eligibility across batches. Three
    single-order batches, each on its own branch off the depot, with
    increasingly long branches (and therefore increasingly long
    t_exec_pb). Two pickers: P1 (slow) and P2 (fast).
    Purpose: cold chain is a PER-(picker, batch) restriction, not a global
    on/off switch -- a T_frio_max that both pickers satisfy for the short
    batches but only the fast picker satisfies for the long one must force
    JUST that batch onto the fast picker, leaving the others free.
    """

    def _build_graph(self):
        graph = OPPLocationGraph(depot_node="L1", final_node="L8")

        # Short branch (B1): L1 -2-> L2 -2-> L8. distance = 4.
        graph.add_vertex("L2", "picking")
        graph.add_edge("L1", "L2", 2)
        graph.add_edge("L2", "L8", 2)

        # Medium branch (B2): L1 -5-> L3 -5-> L4 -5-> L8. distance = 15.
        graph.add_vertex("L3", "picking")
        graph.add_vertex("L4", "picking")
        graph.add_edge("L1", "L3", 5)
        graph.add_edge("L3", "L4", 5)
        graph.add_edge("L4", "L8", 5)

        # Long branch (B3): L1 -10-> L5 -10-> L6 -10-> L7 -10-> L8. distance = 40.
        graph.add_vertex("L5", "picking")
        graph.add_vertex("L6", "picking")
        graph.add_vertex("L7", "picking")
        graph.add_edge("L1", "L5", 10)
        graph.add_edge("L5", "L6", 10)
        graph.add_edge("L6", "L7", 10)
        graph.add_edge("L7", "L8", 10)

        return graph

    def test_only_the_long_batch_is_forced_to_the_fast_picker(self):
        location_graph = self._build_graph()
        V = location_graph.get_vertices()
        B = {"B1", "B2", "B3"}
        N = {"O1", "O2", "O3"}

        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1
        a[("O2", "L4")] = 1
        a[("O3", "L5")] = 1
        a[("O3", "L6")] = 1
        a[("O3", "L7")] = 1

        y = {
            ("O1", "B1"): 1, ("O1", "B2"): 0, ("O1", "B3"): 0,
            ("O2", "B1"): 0, ("O2", "B2"): 1, ("O2", "B3"): 0,
            ("O3", "B1"): 0, ("O3", "B2"): 0, ("O3", "B3"): 1,
        }
        cap_n = {"O1": 2.0, "O2": 2.0, "O3": 2.0}

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
        params.Dd = {n: 1000.0 for n in N}
        params.M = 1000.0
        params.Bn = y
        params.V_p = {"P1": 1.0, "P2": 5.0}
        # fixed_time = 1 + 1*2 = 3 for every batch (single order, cap_n=2).
        # t_exec_pb(P1): B1=3+4=7,  B2=3+15=18, B3=3+40=43
        # t_exec_pb(P2): B1=3+4/5=3.8, B2=3+15/5=6.0, B3=3+40/5=11.0
        # T_frio_max=20: B1/B2 eligible for BOTH pickers; B3 eligible ONLY for P2.
        params.T_frio_max = 20.0
        params.Seed = 3

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.P = {"P1", "P2"}
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)

        try:
            result, output_graph, solution_info = self.solve_and_capture(model, params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))
        self.assert_every_batch_has_one_picker(solution_info, {"P1", "P2"})
        self.assert_no_time_overlap(solution_info, {"P1", "P2"})
        self.assert_cold_chain_respected(solution_info, params.T_frio_max)

        # Only the long batch is actually FORCED onto the fast picker.
        self.assertEqual(solution_info["picker_assignments"]["B3"], "P2")


if __name__ == "__main__":
    unittest.main()
