"""The stress cases, solved with the Split model."""

from tests.stress_cases import bind_cases
from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase

bind_cases(OPPSplitStressTestCase, globals())
