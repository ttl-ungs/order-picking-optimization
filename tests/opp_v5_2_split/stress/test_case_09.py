from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase


class TestOPPSplitStress09(OPPSplitStressTestCase):
    def test_realistic_crew_rectangular_warehouse(self):
        """Realistic crew on a long rectangular warehouse: 8 rows by 21 columns.

        168 locations, one fewer than stress 05's 13x13, but laid out with long
        runs the way real aisles are. Compared against stress 05 it shows
        whether the warehouse's shape matters, not just its size.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(8, 21))
