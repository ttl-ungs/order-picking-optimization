import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.shared_scenarios.functional.two_stage_scenarios import one_cold_batch
from tests.opp_split.opp_split_test_case import OPPTestCaseSplit


class Case24bPreflightEligibility(OPPTestCaseSplit):
    """Before compiling Stage 2, the Split detects that no picker can run a batch within the cold-chain limit."""

    def test_preflight_detects_when_no_picker_is_eligible(self):
        scenario = one_cold_batch(cold_limit=8.0)
        _, route_times, _, _ = self.run_pipeline(scenario, solve_stage2=False)

        self.assertEqual(self.eligible_pairs(scenario, route_times), set())
