from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_v5_1_mono.stress.stress_test_case import OPPMonoStressTestCase


class TestOPPMonoStress03(OPPMonoStressTestCase):
    def test_30_orders_per_batch_20_batches_100x100(self):
        self.assert_stress_pipeline(migrated_stress_scenario(20, 20, 600, 100, 100))
