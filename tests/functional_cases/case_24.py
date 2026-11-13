import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.shared_scenarios.functional.two_stage_scenarios import one_cold_batch
from tests.infra.cases.exact_model_case import ExactModelTestCase


class Case24ColdChain(ExactModelTestCase):
    """The cold-chain limit filters out the picker that is too slow for the batch."""

    def test_cold_chain_filters_out_the_slow_picker(self):
        """Case 24a."""
        scenario = one_cold_batch(cold_limit=10.0)
        _, route_times, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        assignments = self.assignments(values, scenario["P"], scenario["B"])
        self.assertEqual(assignments, {"B1": "P_fast"})
        self.assertLessEqual(2.0 + route_times["B1"] / 2.0, scenario["T_cold"])
        self.assertGreater(2.0 + route_times["B1"], scenario["T_cold"])
