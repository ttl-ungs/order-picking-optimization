from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase


class TestOPPSplitStress15(OPPSplitStressTestCase):
    def test_over_staffed_wave_6_batches_9_pickers(self):
        """Over-staffed wave: 6 batches over 9 pickers, 156 orders on 10x10.

        More pickers than batches, as when a large crew works a small wave.
        Each batch goes to one picker, so Stage 2 chooses who stays idle; with
        five slow and four fast pickers that choice matters -- two batches
        either take a slow picker or wait for a fast one. Replaces the migrated
        10-batch/25-picker case, where every picker had the same speed and
        every order was late, so which pickers stayed idle made no difference.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=6, pickers=9))
