from tests.shared_scenarios.stress.stress_scenarios import migrated_stress_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress03(OPPTestCase):
    """
    Ported from opp_v4's stress test #08 (40 batches, 320 orders, 7x7 grid,
    single picker -- opp_v4's own test_08 uses P={"P1"} directly rather than
    its 5-arg scenario_custom_setup, so this mirrors that with pickers=1)
    -- was the one opp_v4 stress instance missing from opp_split's battery.
    """

    def test_8_orders_per_batch_7x7_320_orders(self):
        self.assert_stress_pipeline(migrated_stress_scenario(40, 1, 320, 7, 7))
