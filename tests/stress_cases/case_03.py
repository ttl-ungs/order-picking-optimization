from tests.shared_scenarios.stress.stress_scenarios import grid_stress_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress03(OPPTestCase):
    """
    40 batches, 320 orders on a 7x7 grid with a single picker (pickers=1).
    """

    def test_8_orders_per_batch_7x7_320_orders(self):
        self.assert_stress_pipeline(grid_stress_scenario(40, 1, 320, 7, 7))
