from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase


class TestOPPSplitStress17(OPPSplitStressTestCase):
    def test_large_crew_three_second_batches(self):
        """Large crew, 15 batches over 12 pickers: three pickers take a second batch.

        Sequencing starts to bind, but only for a quarter of the crew.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=15, pickers=12))
