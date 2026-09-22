from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.opp_v5_1_mono.stress.stress_test_case import OPPMonoStressTestCase


class TestOPPMonoStress06(OPPMonoStressTestCase):
    def test_4_orders_per_batch_10_pickers(self):
        self.assert_stress_pipeline(migrated_stress_scenario(25, 10, 100, 10, 10))
