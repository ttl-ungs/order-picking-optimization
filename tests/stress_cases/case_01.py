from tests.shared_scenarios.stress.stress_scenarios import migrated_stress_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress01(OPPTestCase):
    def test_25_orders_per_batch_30_batches_100x100(self):
        self.assert_stress_pipeline(migrated_stress_scenario(30, 30, 750, 100, 100))
