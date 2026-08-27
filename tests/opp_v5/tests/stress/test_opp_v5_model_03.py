from tests.opp_v5.scenarios.stress.stress_scenarios import migrated_stress_scenario
from tests.opp_v5.tests.stress.stress_test_case import OPPV5StressTestCase


class TestOPPV5Stress03(OPPV5StressTestCase):
    def test_30_orders_per_batch_20_batches_100x100(self):
        self.assert_stress_pipeline(migrated_stress_scenario(20, 20, 600, 100, 100))
