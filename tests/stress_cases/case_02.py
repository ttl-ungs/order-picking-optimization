from tests.shared_scenarios.stress.stress_scenarios import migrated_stress_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress02(OPPTestCase):
    def test_10_orders_per_batch(self):
        self.assert_stress_pipeline(migrated_stress_scenario(10, 10, 100, 10, 10))
