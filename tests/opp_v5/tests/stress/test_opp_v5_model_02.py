import unittest

from tests.opp_v5.scenarios.stress.stress_scenarios import migrated_stress_scenario
from tests.opp_v5.tests.stress.stress_test_case import OPPV5StressTestCase
from tests.test_config import RUN_LARGE_TESTS


class TestOPPV5Stress02(OPPV5StressTestCase):
    @unittest.skipUnless(RUN_LARGE_TESTS, "Requires RUN_LARGE_TESTS=1; v5 routing model is large.")
    def test_25_orders_per_batch_30_batches_100x100(self):
        self.assert_stress_pipeline(migrated_stress_scenario(30, 30, 750, 100, 100))
