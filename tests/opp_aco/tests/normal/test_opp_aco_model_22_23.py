import unittest
import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
)

from models.opp_aco.opp_aco import OPPAntColonyOptimization
from models.opp_aco.utils.output_handler import OutputHandler
from tests.opp.tests.opp_test_case import OPPTestCase
from tests.shared_scenarios.normal.single_order_params_aco import single_order_params


class TestOPPModel(OPPTestCase):
    """
    Test 22 and 23: Earliness/tardiness calculation for ACO.
    4×4 grid, 1 picker (B1), 1 order (O1) at V2.
    """

    def _solve(self, due_date_value):
        params, model_dto = single_order_params(
            due_date_value=due_date_value, start_time=self.start_time
        )
        model = OPPAntColonyOptimization(model_dto)
        model.attach(OutputHandler())
        result, _ = model.solve(params)
        return result, model

    def test_earliness_when_batch_finishes_before_due_date(self):
        """due_date=10000 >> completion time → ea > 0, ta = 0."""
        result, model = self._solve(due_date_value=10000.0)

        self.assertIn(result, ("optimal", "feasible"))
        ea = model.last_solution_info["earliness"].get("O1", 0.0)
        ta = model.last_solution_info["tardiness"].get("O1", 0.0)
        self.assertGreater(ea, 0.0, "Expected positive earliness")
        self.assertAlmostEqual(ta, 0.0, places=4, msg="Expected zero tardiness")

    def test_tardiness_when_batch_finishes_after_due_date(self):
        """due_date=0 << completion time → ta > 0, ea = 0."""
        result, model = self._solve(due_date_value=0.0)

        self.assertIn(result, ("optimal", "feasible"))
        ea = model.last_solution_info["earliness"].get("O1", 0.0)
        ta = model.last_solution_info["tardiness"].get("O1", 0.0)
        self.assertGreater(ta, 0.0, "Expected positive tardiness")
        self.assertAlmostEqual(ea, 0.0, places=4, msg="Expected zero earliness")


if __name__ == "__main__":
    unittest.main()