import unittest
import sys
import os

from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_aco import OPPAntColonyOptimization
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO

from tests.opp_aco.opp_aco_test_case import OPPTestCaseACO


class TestOPPAntColonyOptimizationInvalidSpeedRejected(OPPTestCaseACO):
    """
    Case 36c: a speed of 0 would divide by zero in T_exec_pb, and a negative
    one would yield a negative duration; both must be refused up front, not
    crash or silently look "eligible" for any T_cold. The check is
    invalid_speeds() in models/opp_split/utils/cold_chain_validation.py, shared by
    OPP-ACO and OPP-HC and called before any batch is evaluated.
    """

    def _graph(self):
        location_graph = OPPLocationGraph(depot_node="D", final_node="F")
        location_graph.add_vertex("M", "picking")
        location_graph.add_edge("D", "M", 6.0)
        location_graph.add_edge("M", "F", 6.0)
        return location_graph

    def _solve_with_speed(self, speed):
        location_graph = self._graph()
        V = location_graph.get_vertices()
        N = {"O1"}
        a = {(n, v): 0 for n in N for v in V}
        a[("O1", "M")] = 1
        y = {("O1", "B1"): 1}
        cap_n = {"O1": 1.0}

        params = SolveAcoModelDTO()
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
        params.V_p = {"P1": speed}
        params.T_cold = float("inf")
        params.Seed = 1

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = {"B1"}
        model_dto.P = {"P1"}
        model_dto.start_time = self.start_time
        model = OPPAntColonyOptimization(model_dto)

        return model.solve(params)

    def test_zero_speed_is_rejected(self):
        result, output_graph = self._solve_with_speed(0.0)
        self.assertEqual(result, "infeasible")
        self.assertIsNone(output_graph)

    def test_negative_speed_is_rejected(self):
        result, output_graph = self._solve_with_speed(-1.0)
        self.assertEqual(result, "infeasible")
        self.assertIsNone(output_graph)


if __name__ == "__main__":
    unittest.main()
