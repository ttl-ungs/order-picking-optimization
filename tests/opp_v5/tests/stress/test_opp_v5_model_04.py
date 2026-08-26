from tests.opp_v5.scenarios.stress.stress_scenarios import migrated_stress_scenario
from tests.opp_v5.tests.stress.stress_test_case import OPPV5StressTestCase


class TestOPPV5Stress04(OPPV5StressTestCase):
    def test_4_orders_per_batch(self):
        self.assert_stress_pipeline(migrated_stress_scenario(25, 25, 100, 10, 10))
