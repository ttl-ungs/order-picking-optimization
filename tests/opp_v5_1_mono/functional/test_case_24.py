import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.shared_scenarios.functional.two_stage_scenarios_v5 import one_cold_batch
from tests.opp_v5_1_mono.opp_test_case_v5_1_mono import OPPTestCaseMono


class TestOPPMonoColdChain(OPPTestCaseMono):
    def test_cold_chain_filters_out_the_slow_picker(self):
        scenario = one_cold_batch(cold_limit=10.0)
        _, route_times, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        assignments = self.assignments(values, scenario["P"], scenario["B"])
        self.assertEqual(assignments, {"B1": "P_fast"})
        self.assertLessEqual(2.0 + route_times["B1"] / 2.0, scenario["T_cold"])
        self.assertGreater(2.0 + route_times["B1"], scenario["T_cold"])

    # opp_v5_2_split's test_preflight_detects_when_no_picker_is_eligible is not ported: it
    # solves stage 1 alone (run_pipeline(solve_stage2=False)) to check the Python
    # pre-check, and this monolithic model has no separate routing stage.
