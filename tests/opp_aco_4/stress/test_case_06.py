from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_aco_4.stress.v5_stress_test_case import OPPAco4StressTestCase


class TestOPPAco4StressRealisticCrew14x14(OPPAco4StressTestCase):
    def test_realistic_crew_14x14_warehouse(self):
        """Same instance as opp_v5_1_mono/v5_2_split stress 06."""
        self.assert_stress_pipeline(realistic_crew_scenario(14))
