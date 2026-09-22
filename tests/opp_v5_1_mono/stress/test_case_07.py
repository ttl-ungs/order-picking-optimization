from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_v5_1_mono.stress.stress_test_case import OPPMonoStressTestCase


class TestOPPMonoStress07(OPPMonoStressTestCase):
    def test_10_orders_per_batch_25_pickers(self):
        self.assert_stress_pipeline(migrated_stress_scenario(10, 25, 100, 10, 10))
