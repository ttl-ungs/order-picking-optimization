from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress04(OPPTestCase):
    def test_realistic_crew_7x7_warehouse(self):
        """Realistic crew on a small warehouse: the comfortable end of the ladder.

        Two batches per picker, two speed bands and uneven aisles on 49
        locations with 156 orders. Here the split reaches the optimum quickly
        while the monolithic model, on this same instance, does not.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(7))
