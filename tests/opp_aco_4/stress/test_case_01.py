from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_aco_4.stress.v5_stress_test_case import OPPAco4StressTestCase


class TestOPPAco4StressMigrated100x10030batches750orders(OPPAco4StressTestCase):
    def test_25_orders_per_batch_30_batches_100x100(self):
        """Same instance as opp_v5_1_mono/v5_2_split stress 01."""
        self.assert_stress_pipeline(migrated_stress_scenario(30, 30, 750, 100, 100))
