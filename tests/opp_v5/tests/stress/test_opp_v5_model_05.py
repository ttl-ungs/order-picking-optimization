from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_v5.tests.stress.stress_test_case import OPPV5StressTestCase


class TestOPPV5Stress05(OPPV5StressTestCase):
    def test_10_orders_per_batch(self):
        self.assert_stress_pipeline(migrated_stress_scenario(10, 10, 100, 10, 10))
