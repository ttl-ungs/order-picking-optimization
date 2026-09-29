from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_hc_4.stress.v5_stress_test_case import OPPHc4StressTestCase


class TestOPPHc4StressLargeCrewHalfSecondBatches(OPPHc4StressTestCase):
    def test_large_crew_half_second_batches(self):
        """Same instance as opp_v5_1_mono/v5_2_split stress 18."""
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=18, pickers=12))
