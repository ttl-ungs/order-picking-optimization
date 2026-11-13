from tests.shared_scenarios.stress.stress_scenarios_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress12(OPPTestCase):
    def test_larger_crew_8_batches_4_pickers(self):
        """Crew ladder, first rung: 8 batches over 4 pickers, 208 orders on 7x7.

        Keeps two batches per picker and grows the whole operation. On 7x7
        routing costs seconds, so the ladder measures how Stage 2 scales with
        crew size, while the orders saturate a 47-location grid.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(7, batches=8, pickers=4))
