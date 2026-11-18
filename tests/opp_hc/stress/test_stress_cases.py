"""The stress cases, solved with the HC model."""

from tests.stress_cases import bind_cases
from tests.opp_hc.stress.stress_test_case import OPPHcStressTestCase

bind_cases(OPPHcStressTestCase, globals())
