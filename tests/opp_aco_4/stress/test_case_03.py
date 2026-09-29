from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_aco_4.stress.v5_stress_test_case import OPPAco4StressTestCase


class TestOPPAco4StressMigrated7x740batches1picker(OPPAco4StressTestCase):
    def test_8_orders_per_batch_7x7_320_orders(self):
        """Same instance as opp_v5_1_mono/v5_2_split stress 03."""
        self.assert_stress_pipeline(migrated_stress_scenario(40, 1, 320, 7, 7))
