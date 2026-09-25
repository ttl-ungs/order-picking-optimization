from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase


class TestOPPSplitStress19(OPPSplitStressTestCase):
    def test_large_crew_two_batches_each(self):
        """Large crew, 24 batches over 12 pickers, 624 orders: everyone takes two.

        The two-batches-per-picker ratio of the base profile, at four times its
        crew. Expected to exhaust the runner's 40 minutes, marking where the
        exact approach stops reaching a realistic crew size.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=24, pickers=12))
