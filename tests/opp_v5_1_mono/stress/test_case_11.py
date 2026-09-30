from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_1_mono.stress.stress_test_case import OPPMonoStressTestCase


class TestOPPMonoStress11(OPPMonoStressTestCase):
    def test_realistic_crew_cold_chain(self):
        """Same instance as opp_v5_2_split's stress 11, solved in one MIP."""
        self.assert_stress_pipeline(realistic_crew_scenario(13, pickers=4, t_cold=280))
