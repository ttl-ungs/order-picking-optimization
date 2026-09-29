from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.opp_aco_4.stress.v5_stress_test_case import OPPAco4StressTestCase


class TestOPPAco4StressOverstaffedWave6batches9pickers(OPPAco4StressTestCase):
    def test_over_staffed_wave_6_batches_9_pickers(self):
        """Same instance as opp_v5_1_mono/v5_2_split stress 15."""
        self.assert_stress_pipeline(realistic_crew_scenario(10, batches=6, pickers=9))
