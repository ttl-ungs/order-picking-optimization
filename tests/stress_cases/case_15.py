from tests.shared_scenarios.stress.stress_scenarios_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress15(OPPTestCase):
    def test_over_staffed_wave_6_batches_9_pickers(self):
        """Over-staffed wave: 6 batches over 9 pickers, 156 orders on 10x10.

        More pickers than batches, as when a large crew works a small wave.
        Each batch goes to one picker, so Stage 2 chooses who stays idle; with
        five slow and four fast pickers that choice matters -- two batches
        either take a slow picker or wait for a fast one. With equal speeds
        and every order late, which pickers stay idle would make no difference.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=6, pickers=9))
