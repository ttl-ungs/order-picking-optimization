from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase


class TestOPPSplitStress01(OPPSplitStressTestCase):
    def test_25_orders_per_batch_30_batches_25x25(self):
        self.assert_stress_pipeline(migrated_stress_scenario(30, 30, 750, 25, 25))
