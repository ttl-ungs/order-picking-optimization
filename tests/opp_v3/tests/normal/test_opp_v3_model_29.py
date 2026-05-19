import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)


from models.opp_v3.opp_model_v3 import OPPModelV3
from tests.opp.tests.opp_test_case import OPPTestCase

from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_v3.utils.output_handler import OutputHandler

from tests.opp_v3.scenarios.normal.scenario_1 import basic_two_orders_capacity_limit


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

        params = SolveModelDTO()
        params.w1 = w1
        params.w2 = w2
        params.gamma = gamma
        params.delta = delta
        params.cap_n = cap_n
        params.cap_vehicle = cap_vehicle
        params.a = a
        params.beta_time = beta_time
        params.beta_setup = beta_setup
        params.beta_picking = beta_picking
        params.due_date = due_date
        params.M = M
        params.y = y

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time

        return params, model_dto, V, location_graph

    def _run_and_assert(self, params, model_dto):
        model = OPPModelV3(model_dto)
        model.attach(OutputHandler())
        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")
        self.assertIn(result, ("optimal", "feasible", "infeasible", "unbounded"))

    def test_service_time_zero(self):
        params, model_dto, V, _ = self._build_common()
        params.s = {v: 0.0 for v in V}
        self._run_and_assert(params, model_dto)

    def test_service_time_one(self):
        params, model_dto, V, _ = self._build_common()
        params.s = {v: 1.0 for v in V}
        self._run_and_assert(params, model_dto)

    def test_service_time_mixed(self):
        params, model_dto, V, location_graph = self._build_common()
        # set service time proportional to vertex name hash to vary values
        s = {}
        for i, v in enumerate(sorted(V)):
            s[v] = 0.5 + (i % 3) * 0.5
        params.s = s
        self._run_and_assert(params, model_dto)


if __name__ == "__main__":
    unittest.main()
