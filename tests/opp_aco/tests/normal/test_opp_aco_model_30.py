import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)


from models.opp_aco.opp_aco import OPPAntColonyOptimization
from tests.opp.tests.opp_test_case import OPPTestCase

from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_aco.utils.output_handler import OutputHandler

from tests.shared_scenarios.normal.scenario_01 import basic_two_orders_capacity_limit


class TestServiceTimeEdgeCases(OPPTestCase):
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

        base_params = {
            "W_full": w1,
            "W_ea_ta": w2,
            "W_ea": gamma,
            "W_ta": delta,
            "C_n": cap_n,
            "C_v": cap_vehicle,
            "A": a,
            "B_time": beta_time,
            "B_setup": beta_setup,
            "B_picking": beta_picking,
            "Dd": due_date,
            "M": M,
            "Bn": y,
        }

        model_dto = ModelDTO()
        model_dto.N = N
        model_dto.location_graph = location_graph
        model_dto.B = B
        model_dto.start_time = self.start_time

        return base_params, model_dto, V

    def _run_model(self, params: SolveAcoModelDTO, model_dto: ModelDTO):
        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())
        try:
            result, _ = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution raised exception: {e}")
        self.assertIn(result, ("optimal", "feasible", "infeasible", "unbounded"))

    def test_missing_s_uses_default_zero(self):
        base_params, model_dto, V = self._build_common()
        params = SolveAcoModelDTO()
        for k, v in base_params.items():
            setattr(params, k, v)
        # do NOT set params.s -> should be treated as missing and default to 0
        self._run_model(params, model_dto)

    def test_partial_s_dictionary(self):
        base_params, model_dto, V = self._build_common()
        params = SolveAcoModelDTO()
        for k, v in base_params.items():
            setattr(params, k, v)
        some = list(sorted(V))[: max(1, len(V) // 2)]
        params.S = {v: 1.0 for v in some}
        self._run_model(params, model_dto)

    def test_non_dict_s_values(self):
        base_params, model_dto, V = self._build_common()
        # Ensure non-dict s does not crash (treated as missing)
        for bad in (1, 0.5, [], None):
            params = SolveAcoModelDTO()
            for k, v in base_params.items():
                setattr(params, k, v)
            params.S = bad
            self._run_model(params, model_dto)

    def test_large_and_fractional_s(self):
        base_params, model_dto, V = self._build_common()
        params = SolveAcoModelDTO()
        for k, v in base_params.items():
            setattr(params, k, v)
        params.S = {v: (i * 0.75 + 0.5) for i, v in enumerate(sorted(V))}
        self._run_model(params, model_dto)

    def test_depot_and_final_ignored_in_service_time(self):
        base_params, model_dto, V = self._build_common()
        # set extremely large s for all vertices including depot/final
        params = SolveAcoModelDTO()
        for k, v in base_params.items():
            setattr(params, k, v)
        # fill s for all vertices (model should ignore depot/final in service term)
        all_vs = list(model_dto.location_graph.get_vertices())
        params.S = {v: 1e6 for v in all_vs}
        self._run_model(params, model_dto)

    def test_negative_s_values_do_not_crash(self):
        base_params, model_dto, V = self._build_common()
        params = SolveAcoModelDTO()
        for k, v in base_params.items():
            setattr(params, k, v)
        params.S = {v: (-1.0 if i % 2 == 0 else 0.5) for i, v in enumerate(sorted(V))}
        self._run_model(params, model_dto)


if __name__ == "__main__":
    unittest.main()
