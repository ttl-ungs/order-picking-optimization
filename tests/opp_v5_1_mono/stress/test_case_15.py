from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_1_mono.stress.stress_test_case import OPPMonoStressTestCase


class TestOPPMonoStress15(OPPMonoStressTestCase):
    def test_over_staffed_wave_6_batches_9_pickers(self):
        """Same instance as opp_v5_2_split's stress 15, solved in one MIP."""
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=6, pickers=9))
