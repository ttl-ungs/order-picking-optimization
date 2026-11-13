import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.shared_scenarios.functional.two_stage_scenarios_v5 import (
    cold_limit_between_route_and_total,
    cold_limit_within_tolerance,
    two_cold_batches,
)
from tests.infra.cases.exact_model_case import ExactModelTestCase

ROUTE_VIA_B = 14.0  # R_b of a batch whose only location is B (see the scenario builders)


class Case35ColdChainCoverage(ExactModelTestCase):
    """Cold-chain rules the earlier tests left open: the limit bounds the WHOLE
    execution time of EACH batch -- fixed part included, waiting excluded --
    with the documented 1e-9 tolerance."""

    def test_fixed_time_counts_toward_the_cold_limit(self):
        """Case 35c: P_fast's route share (14 / 2 = 7) fits under T_cold = 8, but its
        execution time (2 + 7 = 9) does not, so no picker is eligible."""
        scenario = cold_limit_between_route_and_total()
        self.assertLessEqual(ROUTE_VIA_B / scenario["V_p"]["P_fast"], scenario["T_cold"])

        _, _, status, values = self.run_pipeline(scenario)
        self.assertEqual(status, "infeasible")
        self.assertEqual(values, {})

    def test_cold_limit_applies_to_each_batch_not_the_whole_shift(self):
        """Case 35a: Only P_fast is eligible for either batch (9 <= 10 < 16), so it runs
        both back to back. The second completes at 18, past the limit, and that
        is valid: the limit bounds each batch's execution, not the waiting before
        it. Objective = W_c * (9 + 18) = 27."""
        scenario = two_cold_batches()
        _, route_times, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        self.assertEqual(self.assignments(values, scenario["P"], scenario["B"]), {"B1": "P_fast", "B2": "P_fast"})
        completions = self.completion_times(values, scenario["P"], scenario["B"])
        ends = sorted(completions[("P_fast", batch)] for batch in scenario["B"])
        self.assertAlmostEqual(ends[0], 9.0, places=5)
        self.assertAlmostEqual(ends[1], 18.0, places=5)
        self.assertGreater(ends[1], scenario["T_cold"])
        self.assertAlmostEqual(self.objective_value(), 27.0, places=5)
        self.assert_no_overlap(values, scenario, route_times)

    def test_cold_limit_tolerance_keeps_a_picker_within_rounding_noise(self):
        """Case 35b: T_exec_pb(P_fast, B1) = 9.0 exceeds T_cold = 9.0 - 5e-10 by less
        than the 1e-9 tolerance, so P_fast must stay eligible and take the batch."""
        scenario = cold_limit_within_tolerance()
        _, route_times, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        self.assertIn(("P_fast", "B1"), self.eligible_pairs(scenario, route_times))
        self.assertEqual(self.assignments(values, scenario["P"], scenario["B"]), {"B1": "P_fast"})
