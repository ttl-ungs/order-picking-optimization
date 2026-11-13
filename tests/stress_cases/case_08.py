from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress08(OPPTestCase):
    def test_realistic_crew_16x16_warehouse(self):
        """Realistic crew on a 256-location warehouse: the ceiling probe.

        15x15 solved in about 28 minutes with routing taking most of it; this
        size is expected to exhaust the runner's 40 minutes, marking where the
        exact approach stops reaching with a realistic profile.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(16))
