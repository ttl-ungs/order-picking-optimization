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


class TestOPPAntColonyOptimization4ForcedRevisitIsInfeasible(OPPTestCaseACO4):
    """
    Ported from opp_v5_1_mono's test_case_38
    (TestOPPMonoSimplePathLimit.test_route_that_must_revisit_a_vertex_is_infeasible):
    documents a limit of the routing formulation, not a business rule. A
    central hub H with two dead-end aisles (L1, L2), one required order in
    each: any walk that picks both has to pass through H three times
    (D -> H -> L1 -> H -> L2 -> H -> F). v5's routing constraints allow at
    most one arc into and one out of each vertex (a simple path); opp_aco_4
    and opp_hc_4 build routes the same way (no vertex is ever revisited
    during construction -- see models/opp_aco_4/opp_aco_4.py's
    _build_batch_route), so no feasible route exists for the batch either,
    even though a real picker could walk it.
    """

    def test_route_that_must_revisit_a_vertex_is_infeasible(self):
        location_graph = OPPLocationGraph(depot_node="D", final_node="F")
        location_graph.add_vertex("H", "picking")
        location_graph.add_vertex("L1", "picking")
        location_graph.add_vertex("L2", "picking")
        location_graph.add_edge("D", "H", 1.0)
        location_graph.add_edge("H", "L1", 1.0)
        location_graph.add_edge("L1", "H", 1.0)
        location_graph.add_edge("H", "L2", 1.0)
        location_graph.add_edge("L2", "H", 1.0)
        location_graph.add_edge("H", "F", 1.0)

        V = location_graph.get_vertices()
        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "L1")] = 1
        a[("O2", "L2")] = 1

        y = {("O1", "B1"): 1, ("O2", "B1"): 1}
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
        params.T_frio_max = float("inf")
        params.Seed = 1

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = {"B1"}
        model_dto.P = {"P1"}
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)

        result, output_graph = model.solve(params)

        self.assertEqual(result, "infeasible")
        self.assertIsNone(output_graph)


if __name__ == "__main__":
    unittest.main()
