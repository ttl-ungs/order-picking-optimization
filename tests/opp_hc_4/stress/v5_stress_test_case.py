"""Base test case for running v5's stress scenarios through opp_hc_4.

Mirrors tests/opp_v5_1_mono/stress/stress_test_case.py's
assert_stress_pipeline: same three checks (solved, routes cover every
required location, no time overlap on a picker), translated to opp_hc_4's
solution_info shape instead of ZIMPL variable names.
"""

from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO
from models.opp_hc_4 import OPPHillClimbing

from tests.infra.cases.opp_test_case import OPPTestCase
from tests.infra.factories.v5_scenario_adapter import build_model_dto_and_params
from tests.opp_hc_4.opp_hc_4_test_case import SolutionInfoCapture


class OPPHc4StressTestCase(OPPTestCase):
    def assert_stress_pipeline(self, scenario, max_it=200, max_imp=60, max_time=30.0):
        model_dto, params = build_model_dto_and_params(scenario, SolveHC4ModelDTO)
        model_dto.start_time = self.start_time
        params.Max_it = max_it
        params.Max_imp = max_imp
        params.Max_time = max_time
        model = OPPHillClimbing(model_dto)
        capture = SolutionInfoCapture()
        model.attach(capture)

        try:
            result, output_graph = model.solve(params)
        except Exception as e:
            self.fail(f"Model execution failed: {e}")

        self.assertIn(result, ("optimal", "feasible"))
        solution_info = capture.solution_info

        self.assertEqual(set(solution_info["picker_assignments"]), scenario["B"])
        self._assert_routes_cover_requirements(solution_info, scenario)

        picker_ids = list(scenario["P"])
        for picker in picker_ids:
            batches = [b for b, p in solution_info["picker_assignments"].items() if p == picker]
            intervals = sorted(
                (solution_info["batch_completions"][b] - solution_info["batch_times"][b],
                 solution_info["batch_completions"][b], b)
                for b in batches
            )
            for i in range(len(intervals) - 1):
                self.assertGreaterEqual(
                    intervals[i + 1][0], intervals[i][1] - 1e-5,
                    f"Time overlap on picker {picker}: {intervals[i]} vs {intervals[i + 1]}",
                )

    def _assert_routes_cover_requirements(self, solution_info, scenario):
        # depot/final are always implicit endpoints of any route (every
        # batch starts at the depot and ends at the final node), but
        # solution_info["routes"] only lists the picking stops in between --
        # unlike v5's own check, which derives "visited" from active arcs
        # and so always includes them. Some stress scenarios (see
        # stress_scenarios_v5.py's module docstring, degeneracy #5) assign
        # an order's location by cycling through EVERY vertex including
        # depot/final, so this must be added back or a batch that
        # (nonsensically) "requires" the depot/final node would always
        # look like it misses it.
        endpoints = {scenario["depot"], scenario["final"]}
        for batch, visited in solution_info["routes"].items():
            required = {
                location for location in scenario["V"]
                if any(
                    scenario["A_ni"][(order, location)] and scenario["B_nb"][(order, batch)]
                    for order in scenario["N"]
                )
            }
            self.assertTrue(
                required <= set(visited) | endpoints,
                f"{batch} misses {required - set(visited) - endpoints}",
            )
