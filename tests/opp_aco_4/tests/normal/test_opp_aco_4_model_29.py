import unittest
import sys
import os

from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)


from models.opp_aco_4 import OPPAntColonyOptimization
from tests.opp.tests.opp_test_case import OPPTestCase
from dtos.opp.model_dto import ModelDTO
from models.opp_aco_4.utils.output_handler import OutputHandler

from tests.shared_scenarios.normal.scenario_01 import basic_two_orders_capacity_limit


# Ported from opp_aco_2's test_opp_aco_2_model_29.py for opp_aco_4/analysis parity (V_p unset, T_frio_max default +inf -> pure equivalence).
class TestServiceTimeVariations(OPPTestCase):
    def _build_common(self):
        V, B, w1, w2, gamma, delta, location_graph, cap_vehicle = (
            basic_two_orders_capacity_limit()
        )

        N = {"O1", "O2"}
        a = {(n, v): 0 for n in N for v in V}

        a[("O1", "L2")] = 1
        a[("O2", "L3")] = 1

        y = {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1}
        cap_n = {"O1": 3.0, "O2": 3.0}

        beta_time = 0.5
        beta_setup = 1.0
        beta_picking = 1.0
        M = 1000.0

        due_date = {"O1": 15.0, "O2": 15.0}

        params = SolveAco4ModelDTO()
        params.W_full = w1
        params.W_ea_ta = w2
        params.W_ea = gamma
        params.W_ta = delta
        params.C_n = cap_n
        params.C_v = cap_vehicle
        params.A = a
        params.B_time = beta_time
        params.B_setup = beta_setup
        params.B_picking = beta_picking
        params.Dd = due_date
        params.M = M
        params.Bn = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time

        return params, model_dto, V, location_graph

    def _run_and_assert(self, params, model_dto):
        model = OPPAntColonyOptimization(model_dto)
        output_handler = OutputHandler()
        model.attach(output_handler)
        model.attach(OutputHandler())
        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")
        self.assertIn(result, ("optimal", "feasible", "infeasible", "unbounded"))

    def test_service_time_zero(self):
        params, model_dto, V, _ = self._build_common()
        params.S = {v: 0.0 for v in V}
        self._run_and_assert(params, model_dto)

    def test_service_time_one(self):
        params, model_dto, V, _ = self._build_common()
        params.S = {v: 1.0 for v in V}
        self._run_and_assert(params, model_dto)

    def test_service_time_mixed(self):
        params, model_dto, V, location_graph = self._build_common()
        # set service time proportional to vertex name hash to vary values
        s = {}
        for i, v in enumerate(sorted(V)):
            s[v] = 0.5 + (i % 3) * 0.5
        params.S = s
        self._run_and_assert(params, model_dto)


if __name__ == "__main__":
    unittest.main()
