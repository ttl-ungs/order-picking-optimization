"""The stress cases, solved with the ACO model."""

from tests.stress_cases import bind_cases
from tests.opp_aco.stress.stress_test_case import OPPAcoStressTestCase

bind_cases(OPPAcoStressTestCase, globals())
