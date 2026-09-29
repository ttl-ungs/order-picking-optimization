from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_hc_4.stress.v5_stress_test_case import OPPHc4StressTestCase


class TestOPPHc4StressRealisticCrewRectangular(OPPHc4StressTestCase):
    def test_realistic_crew_rectangular_warehouse(self):
        """Same instance as opp_v5_1_mono/v5_2_split stress 09."""
        self.assert_stress_pipeline(realistic_crew_scenario(8, 21))
