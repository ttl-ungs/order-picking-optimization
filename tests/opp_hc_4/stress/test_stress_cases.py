"""The stress cases, solved with the HC model."""

from tests.stress_cases import bind_cases
from tests.opp_hc_4.stress.v5_stress_test_case import OPPHc4StressTestCase

bind_cases(OPPHc4StressTestCase, globals())
