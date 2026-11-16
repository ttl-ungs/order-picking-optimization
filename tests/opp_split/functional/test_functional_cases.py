"""The functional cases of the thesis, solved with the Split model."""

from tests.functional_cases import bind_cases
from tests.opp_split.opp_split_test_case import OPPTestCaseSplit

bind_cases(OPPTestCaseSplit, globals())
