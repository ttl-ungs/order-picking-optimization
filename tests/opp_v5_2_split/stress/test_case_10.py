from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase


class TestOPPSplitStress10(OPPSplitStressTestCase):
    def test_realistic_crew_scheduling_heavy(self):
        """Scheduling-dominated: 6 batches over 4 pickers on a small warehouse.

        Routing on 7x7 costs seconds, so nearly all the time goes to Stage 2.
        Four pickers in two speed bands is the intermediate batches/pickers
        ratio where assignment choices multiply -- the hardest spot measured.
        A reference for any attempt to speed up Stage 2.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(7, pickers=4))
