from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario
from tests.infra.cases.opp_test_case import OPPTestCase


class Stress11(OPPTestCase):
    def test_realistic_crew_cold_chain(self):
        """Cold-chain limit active: only the fast speed band may carry any batch.

        Same batches and orders as stress 05 (13x13), four pickers in two bands.
        Every other stress scenario leaves the limit off. With these route
        times a batch takes 249-259 for a fast picker and 308-324 for a slow
        one, so T_cold = 280 excludes the slow band from every batch and
        the schedule must fit on the two fast pickers. The threshold depends on
        those route times: if the generator changes, re-derive it.
        """
        self.assert_stress_pipeline(realistic_crew_scenario(13, pickers=4, t_cold=280))
