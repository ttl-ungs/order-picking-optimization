import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.shared_scenarios.normal.two_stage_scenarios_v5 import one_cold_batch
from tests.opp_v5.opp_test_case_v5 import OPPTestCaseV5


class TestOPPV5ColdChain(OPPTestCaseV5):
    def test_cold_chain_filters_out_the_slow_picker(self):
        scenario = one_cold_batch(cold_limit=10.0)
        _, route_times, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        assignments = self.assignments(values, scenario["P"], scenario["B"])
        self.assertEqual(assignments, {"B1": "P_fast"})
        self.assertLessEqual(2.0 + route_times["B1"] / 2.0, scenario["T_frio_max"])
        self.assertGreater(2.0 + route_times["B1"], scenario["T_frio_max"])

    def test_preflight_detects_when_no_picker_is_eligible(self):
        scenario = one_cold_batch(cold_limit=8.0)
        _, route_times, _, _ = self.run_pipeline(scenario, solve_stage2=False)

        self.assertEqual(self.eligible_pairs(scenario, route_times), set())
