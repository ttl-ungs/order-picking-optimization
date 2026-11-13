from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress07(OPPTestCase):
    def test_realistic_crew_15x15_warehouse(self):
        """Realistic crew on a 225-location warehouse: the largest size seen to solve.

        Same crew and orders as stress 04-06. Solved in about 28 minutes with
        routing taking most of it -- a steep jump from 14x14's 7.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(15))
