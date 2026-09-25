from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase


class TestOPPSplitStress05(OPPSplitStressTestCase):
    def test_realistic_crew_13x13_warehouse(self):
        """Realistic crew on a mid-size warehouse: 169 locations.

        Same crew and orders as stress 04. The routing load is what grows,
        which is the stage the split decomposes batch by batch.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(13))
