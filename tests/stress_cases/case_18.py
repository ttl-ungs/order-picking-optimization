from tests.shared_scenarios.stress.stress_scenarios_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress18(OPPTestCase):
    def test_large_crew_half_second_batches(self):
        """Large crew, 18 batches over 12 pickers: half the crew takes a second batch."""
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=18, pickers=12))
