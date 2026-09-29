import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.shared_scenarios.functional.two_stage_scenarios_v5 import (
    slow_picker_late_order,
    two_batches_same_route,
)
from tests.opp_v5_2_split.opp_test_case_v5_2_split import OPPTestCaseSplit


class TestOPPSplitSpeedCoverage(OPPTestCaseSplit):
    """Picker speed beyond the single-batch formula check: how it trades off
    against sequencing, how it reaches the due-date terms, and which speeds
    the model refuses."""

    def test_fast_picker_takes_both_batches_when_four_times_faster(self):
        """With V_p = 4, P_fast runs a batch in 2 + 14/4 = 5.5. Queueing both
        batches on it completes at 5.5 and 11 (sum 16.5), cheaper than giving one
        to P_slow (5.5 + 16 = 21.5)."""
        scenario = two_batches_same_route(fast_speed=4.0)
        _, route_times, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        self.assertEqual(self.assignments(values, scenario["P"], scenario["B"]), {"B1": "P_fast", "B2": "P_fast"})
        completions = self.completion_times(values, scenario["P"], scenario["B"])
        ends = sorted(completions[("P_fast", batch)] for batch in scenario["B"])
        self.assertAlmostEqual(ends[0], 5.5, places=5)
        self.assertAlmostEqual(ends[1], 11.0, places=5)
        self.assertAlmostEqual(self.objective_value(), 16.5, places=5)
        self.assert_no_overlap(values, scenario, route_times)

    def test_batches_are_split_when_fast_picker_is_only_twice_as_fast(self):
        """With V_p = 2, P_fast takes 9 per batch: both on it would complete at
        9 and 18 (sum 27), while one each completes at 9 and 16 (sum 25)."""
        scenario = two_batches_same_route(fast_speed=2.0)
        _, route_times, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        assignments = self.assignments(values, scenario["P"], scenario["B"])
        self.assertEqual(set(assignments.values()), {"P_fast", "P_slow"})
        completions = self.completion_times(values, scenario["P"], scenario["B"])
        by_picker = {picker: completions[(picker, batch)] for batch, picker in assignments.items()}
        self.assertAlmostEqual(by_picker["P_fast"], 9.0, places=5)
        self.assertAlmostEqual(by_picker["P_slow"], 16.0, places=5)
        self.assertAlmostEqual(self.objective_value(), 25.0, places=5)
        self.assert_no_overlap(values, scenario, route_times)

    def test_tardiness_uses_the_speed_scaled_route_time(self):
        """A picker at half speed needs 2 + 14/0.5 = 30 for a batch due at 20:
        the order is exactly 10 late, not early. Objective = 10*30 + 10 = 310."""
        scenario = slow_picker_late_order()
        _, _, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        self.assertAlmostEqual(values["c_b$B1"], 30.0, places=5)
        self.assertAlmostEqual(values.get("ta_n$O1", 0.0), 10.0, places=5)
        self.assertAlmostEqual(values.get("ea_n$O1", 0.0), 0.0, places=5)
        self.assertAlmostEqual(self.objective_value(), 310.0, places=5)

    def test_non_positive_speed_is_rejected_before_solving(self):
        """A speed of 0 would divide by zero in t_exec_pb and a negative one would
        yield a negative duration; both must be refused, naming the picker."""
        for speed in (0.0, -1.0):
            with self.subTest(speed=speed):
                scenario = two_batches_same_route(fast_speed=2.0)
                scenario["V_p"]["P_slow"] = speed
                with self.assertRaises(AssertionError) as caught:
                    self.run_pipeline(scenario)
                self.assertIn("P_slow", str(caught.exception))
