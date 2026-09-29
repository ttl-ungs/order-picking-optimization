from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_hc_4.stress.v5_stress_test_case import OPPHc4StressTestCase


class TestOPPHc4StressLargerCrew8batches4pickers(OPPHc4StressTestCase):
    def test_larger_crew_8_batches_4_pickers(self):
        """Same instance as opp_v5_1_mono/v5_2_split stress 12."""
        self.assert_stress_pipeline(realistic_crew_scenario(7, batches=8, pickers=4))
