import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.shared_scenarios.functional.two_stage_scenarios_v5 import three_orders_one_batch
from tests.opp_v5_1_mono.opp_test_case_v5_1_mono import OPPTestCaseMono


class TestOPPMonoJustInTime(OPPTestCaseMono):
    """The objective delays a batch on purpose to avoid early deliveries.

    Delaying one unit costs W_full and saves one unit of earliness per order
    still early, so a batch is held back while its early orders outnumber
    W_full. This is what sets the on-time share to (N_b + W_full) / (2 N_b)
    in the stress profile. The batch can complete at 9 at the earliest; all
    three orders are due at 20.
    """

    def test_batch_is_delayed_while_early_orders_outweigh_completion_weight(self):
        """W_full = 1 < 3 orders: the batch waits until the due date. Completion
        20, no earliness or tardiness, objective 20."""
        scenario = three_orders_one_batch(w_full=1.0)
        _, _, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        self.assertAlmostEqual(values["c_b$B1"], 20.0, places=5)
        for order in scenario["N"]:
            self.assertAlmostEqual(values.get(f"ea_n${order}", 0.0), 0.0, places=5)
            self.assertAlmostEqual(values.get(f"ta_n${order}", 0.0), 0.0, places=5)
        self.assertAlmostEqual(self.objective_value(), 20.0, places=5)

    def test_batch_is_not_delayed_when_completion_weight_dominates(self):
        """W_full = 5 > 3 orders: the batch completes as soon as it can, at 9,
        with 11 of earliness per order. Objective 5*9 + 3*11 = 78."""
        scenario = three_orders_one_batch(w_full=5.0)
        _, _, status, values = self.run_pipeline(scenario)

        self.assertIn(status, ("optimal", "feasible"))
        self.assertAlmostEqual(values["c_b$B1"], 9.0, places=5)
        for order in scenario["N"]:
            self.assertAlmostEqual(values.get(f"ea_n${order}", 0.0), 11.0, places=5)
            self.assertAlmostEqual(values.get(f"ta_n${order}", 0.0), 0.0, places=5)
        self.assertAlmostEqual(self.objective_value(), 78.0, places=5)
