from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase


class TestOPPSplitStress13(OPPSplitStressTestCase):
    def test_larger_crew_10_batches_5_pickers(self):
        """Crew ladder, second rung: 10 batches over 5 pickers, 260 orders on 7x7."""
        self.assert_stress_pipeline(realistic_crew_scenario(7, batches=10, pickers=5))
