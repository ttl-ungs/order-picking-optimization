"""The functional cases of the thesis, solved with the Split model."""

from tests.functional_cases import bind_cases
from tests.opp_v5_2_split.opp_test_case_v5_2_split import OPPTestCaseSplit

bind_cases(OPPTestCaseSplit, globals())
