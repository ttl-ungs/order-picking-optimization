"""The stress cases, solved with the Mono model."""

from tests.stress_cases import bind_cases
from tests.opp_mono.stress.stress_test_case import OPPMonoStressTestCase

bind_cases(OPPMonoStressTestCase, globals())
