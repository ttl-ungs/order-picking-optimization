from tests.shared_scenarios.stress.stress_scenarios_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress17(OPPTestCase):
    def test_large_crew_three_second_batches(self):
        """Large crew, 15 batches over 12 pickers: three pickers take a second batch.

        Sequencing starts to bind, but only for a quarter of the crew.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=15, pickers=12))
