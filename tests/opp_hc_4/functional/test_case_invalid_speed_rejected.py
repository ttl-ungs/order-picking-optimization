import unittest
import sys
import os

from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.opp_hc_4 import OPPHillClimbing
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO

from tests.opp_hc_4.opp_hc_4_test_case import OPPTestCaseHC4


class TestOPPHillClimbing4InvalidSpeedRejected(OPPTestCaseHC4):
    """
    Ported from opp_v5_1_mono's test_case_36
    (TestOPPMonoSpeedCoverage.test_non_positive_speed_is_rejected_before_solving):
    a speed of 0 would divide by zero in t_exec_pb, and a negative one
    would yield a negative duration; both must be refused up front, not
    crash or silently look "eligible" for any T_frio_max (see
    models/opp_v5_2_split/utils/cold_chain_validation.py's invalid_speeds(),
    shared by opp_aco_4 and opp_hc_4, called at opp_aco_4.py:150 /
    opp_hc_4.py:142 before any batch is ever evaluated).
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

        params = SolveHC4ModelDTO()
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
        params.Dd = {"O1": 1000.0}
        params.M = 1000.0
        params.Bn = y
        params.V_p = {"P1": speed}
        params.T_frio_max = float("inf")
        params.Seed = 1
        params.Max_it = 100
        params.Max_imp = 30
        params.Max_time = 10.0

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = {"B1"}
        model_dto.P = {"P1"}
        model_dto.start_time = self.start_time
        model = OPPHillClimbing(model_dto)

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
