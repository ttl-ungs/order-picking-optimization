from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_hc_4.stress.v5_stress_test_case import OPPHc4StressTestCase


class TestOPPHc4StressMigrated10x1010batches(OPPHc4StressTestCase):
    def test_10_orders_per_batch(self):
        """Same instance as opp_v5_1_mono/v5_2_split stress 02."""
        self.assert_stress_pipeline(migrated_stress_scenario(10, 10, 100, 10, 10))
