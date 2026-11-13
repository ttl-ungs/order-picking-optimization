import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.shared_scenarios.functional.two_stage_scenarios_v5 import one_cold_batch
from tests.opp_v5_2_split.opp_test_case_v5_2_split import OPPTestCaseSplit


class Case24bPreflightEligibility(OPPTestCaseSplit):
    """Before compiling Stage 2, the Split detects that no picker can run a batch within the cold-chain limit."""

    def test_preflight_detects_when_no_picker_is_eligible(self):
        scenario = one_cold_batch(cold_limit=8.0)
        _, route_times, _, _ = self.run_pipeline(scenario, solve_stage2=False)

        self.assertEqual(self.eligible_pairs(scenario, route_times), set())
