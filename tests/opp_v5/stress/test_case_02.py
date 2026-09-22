from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_v5.stress.stress_test_case import OPPV5StressTestCase


class TestOPPV5Stress02(OPPV5StressTestCase):
    def test_25_orders_per_batch_30_batches_100x100(self):
        self.assert_stress_pipeline(migrated_stress_scenario(30, 30, 750, 100, 100))
