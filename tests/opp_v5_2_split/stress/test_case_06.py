from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase


class TestOPPSplitStress06(OPPSplitStressTestCase):
    def test_realistic_crew_14x14_warehouse(self):
        """Realistic crew on a 196-location warehouse, between stress 05 and 07.

        Same crew and orders as the rest of the warehouse-size ladder (stress
        04-08). 13x13 solved in about 6 minutes and 15x15 in about 28, so this
        size was aimed at the 10-20 minute band between them; it came out at
        about 7.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(14))
