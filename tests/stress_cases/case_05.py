from tests.shared_scenarios.stress.stress_scenarios_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress05(OPPTestCase):
    def test_realistic_crew_13x13_warehouse(self):
        """Realistic crew on a mid-size warehouse: 169 locations.

        Same crew and orders as stress 04. The routing load is what grows,
        which is the stage the split decomposes batch by batch.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(13))
