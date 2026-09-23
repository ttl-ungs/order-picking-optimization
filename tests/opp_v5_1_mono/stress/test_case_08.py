from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_1_mono.stress.stress_test_case import OPPMonoStressTestCase


class TestOPPMonoStress08(OPPMonoStressTestCase):
    def test_realistic_crew_16x16_warehouse(self):
        """Same instance as opp_v5_2_split's stress 08, solved in one MIP."""
        self.assert_stress_pipeline(realistic_crew_scenario(16))
