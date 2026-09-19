from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_v5.stress.stress_test_case import OPPV5StressTestCase


class TestOPPV5Stress08(OPPV5StressTestCase):
    """
    Ported from opp_v4's stress test #08 (40 batches, 320 orders, 7x7 grid,
    single picker -- opp_v4's own test_08 uses P={"P1"} directly rather than
    its 5-arg scenario_custom_setup, so this mirrors that with pickers=1)
    -- was the one opp_v4 stress instance missing from opp_v5's battery.
    """

    def test_8_orders_per_batch_7x7_320_orders(self):
        self.assert_stress_pipeline(migrated_stress_scenario(40, 1, 320, 7, 7))
