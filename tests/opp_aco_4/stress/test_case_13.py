from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_aco_4.stress.v5_stress_test_case import OPPAco4StressTestCase


class TestOPPAco4StressLargerCrew10batches5pickers(OPPAco4StressTestCase):
    def test_larger_crew_10_batches_5_pickers(self):
        """Same instance as opp_v5_1_mono/v5_2_split stress 13."""
        self.assert_stress_pipeline(realistic_crew_scenario(7, batches=10, pickers=5))
