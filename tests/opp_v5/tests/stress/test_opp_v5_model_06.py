from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_v5.tests.stress.stress_test_case import OPPV5StressTestCase


class TestOPPV5Stress06(OPPV5StressTestCase):
    def test_4_orders_per_batch_10_pickers(self):
        self.assert_stress_pipeline(migrated_stress_scenario(25, 10, 100, 10, 10))
