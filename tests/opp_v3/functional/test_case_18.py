import unittest
from models.opp_v3.opp_model_v3 import OPPModelV3
from models.opp_v3.utils.output_handler import OutputHandler
from observer.observer import Observer
from tests.support.opp_test_case import OPPTestCase
import sys
import os

from tests.shared_scenarios.functional.single_order_params_v2 import single_order_params

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "..")))


class ResultCapture(Observer):
    # Captures ta and ea values after the model is solved.
    def __init__(self):
        self.ta = {}
        self.ea = {}

    def update(self, model, N, ta, ea, **kwargs):
        if model.getStatus() in ("optimal", "feasible"):
            for n in N:
                self.ta[n] = model.getVal(ta[n])
                self.ea[n] = model.getVal(ea[n])


class TestOPPModel(OPPTestCase):
    """
    Test 22 and 23: Earliness/tardiness calculation
    4×4 grid, 1 picker (P1), 1 batch (B1), 1 order (O1).
    """

    def test_earliness_when_batch_finishes_before_due_date(self):
        """
        - V1 -> V2: 4  (1 vertical edge weight 4)
        - V2 -> V16: 20 (2 vertical + 3 horizontal edges, each weight 4)
        Expected execution time: beta_setup(1) + beta_picking(1)*cap_n(1) + beta_time(0.5)*distance(24) = 14.0

        due_date=10000 > expected completion (14) → ea > 0 and ta = 0.
        """
        params, model_dto = single_order_params(due_date_value=10000.0, start_time=self.start_time)

        capture = ResultCapture()
        model = OPPModelV3(model_dto)
        model.attach(OutputHandler())
        model.attach(capture)

        result, _ = model.solve(params)

        self.assertIn(result, ("optimal", "feasible"))
        self.assertGreater(capture.ea["O1"], 0.0, "Expected positive earliness")
        self.assertAlmostEqual(capture.ta["O1"], 0.0, places=4, msg="Expected zero tardiness")

    def test_tardiness_when_batch_finishes_after_due_date(self):
        """
        due_date=0 < expected completion (14) --> ta > 0 and ea = 0.
        A tight due_date never causes infeasibility: the ta variable absorbs the excess.
        """
        params, model_dto = single_order_params(due_date_value=0.0, start_time=self.start_time)

        capture = ResultCapture()
        model = OPPModelV3(model_dto)
        model.attach(OutputHandler())
        model.attach(capture)

        result, _ = model.solve(params)

        self.assertIn(result, ("optimal", "feasible"),
                      "A tight due_date must not make the model infeasible")
        self.assertGreater(capture.ta["O1"], 0.0, "Expected positive tardiness")
        self.assertAlmostEqual(capture.ea["O1"], 0.0, places=4, msg="Expected zero earliness")


if __name__ == "__main__":
    unittest.main()
