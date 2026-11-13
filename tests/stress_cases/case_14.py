from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress14(OPPTestCase):
    def test_larger_crew_12_batches_6_pickers(self):
        """Crew ladder, third rung: 12 batches over 6 pickers, 312 orders on 7x7.

        Nearly seven orders per pickable location. Expected to exhaust the
        runner's 40 minutes, marking the ceiling of the crew-size axis.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(7, batches=12, pickers=6))
