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


class TestOPPAntColonyOptimization4ColdChainTolerance(OPPTestCaseACO4):
    """
    Ported from opp_v5_1_mono's test_case_35
    (TestOPPMonoColdChainCoverage.test_cold_limit_tolerance_keeps_a_picker_within_rounding_noise):
    T_frio_max set just BELOW the picker's t_exec_pb, by less than the
    documented 1e-9 tolerance (COLD_CHAIN_TOLERANCE, see
    models/opp_v5_2_split/utils/cold_chain_validation.py, shared by
    opp_aco_4 and opp_hc_4). The picker must stay eligible -- rounding
    noise in a derived time must not drop a valid picker.

    Regression for a 2026-09-26 finding: ConstraintsValidator.
    cold_chain_violation() computed `overrun = t_exec_pb - T_frio_max`
    WITHOUT subtracting the tolerance, so a t_exec_pb within tolerance of
    T_frio_max still had overrun > 0 and was never added to
    feasible_ant_solutions in opp_aco_4.py's main loop -- the whole run
    reported "infeasible" despite validate_cold_chain_strict() (which DID
    apply the tolerance) considering it compliant.

    Same geometry as test_case_cold_chain_boundary.py: t_exec_pb(P1) =
    2.0 + 12.0/1.0 = 14.0 exactly.
    """

    def test_cold_limit_tolerance_keeps_a_picker_within_rounding_noise(self):
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
        params.V_p = {"P1": 1.0}
        params.T_frio_max = 14.0 - 5e-10
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
        self.assertEqual(solution_info["picker_assignments"]["B1"], "P1")
        self.assertAlmostEqual(solution_info["batch_times"]["B1"], 14.0, places=4)


if __name__ == "__main__":
    unittest.main()
