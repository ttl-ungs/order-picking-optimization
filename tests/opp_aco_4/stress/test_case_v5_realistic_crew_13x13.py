from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_aco_4.stress.v5_stress_test_case import OPPAco4StressTestCase


class TestOPPAco4StressRealisticCrew13x13(OPPAco4StressTestCase):
    def test_realistic_crew_13x13_warehouse(self):
        """Same instance as opp_v5_1_mono/v5_2_split stress 05."""
        self.assert_stress_pipeline(realistic_crew_scenario(13))
