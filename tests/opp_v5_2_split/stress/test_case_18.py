from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase


class TestOPPSplitStress18(OPPSplitStressTestCase):
    def test_large_crew_half_second_batches(self):
        """Large crew, 18 batches over 12 pickers: half the crew takes a second batch."""
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=18, pickers=12))
