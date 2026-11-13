"""The stress cases, solved with the ACO model."""

from tests.stress_cases import bind_cases
from tests.opp_aco_4.stress.v5_stress_test_case import OPPAco4StressTestCase

bind_cases(OPPAco4StressTestCase, globals())
