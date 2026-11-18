from tests.shared_scenarios.stress.stress_scenarios_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress16(OPPTestCase):
    def test_large_crew_single_wave(self):
        """Large crew, one wave: 12 batches over 12 pickers, 312 orders on 10x10.

        Six slow and six fast pickers, each taking exactly one batch -- how a
        real wave with a big crew often runs. No batch waits for another, so
        Stage 2 is an assignment of batches to speeds rather than a sequencing
        problem. First rung of the large-crew ladder (stress 16-19), which keeps
        the crew at 12 and grows the wave.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=12, pickers=12))
