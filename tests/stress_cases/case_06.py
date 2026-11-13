from tests.shared_scenarios.stress.stress_scenarios_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress06(OPPTestCase):
    def test_realistic_crew_14x14_warehouse(self):
        """Realistic crew on a 196-location warehouse, between stress 05 and 07.

        Same crew and orders as the rest of the warehouse-size ladder (stress
        04-08). 13x13 solved in about 6 minutes and 15x15 in about 28, so this
        size was aimed at the 10-20 minute band between them; it came out at
        about 7.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(14))
