"""The functional cases of the thesis, solved with OPP-HC."""

from tests.functional_cases import bind_cases
from tests.opp_hc.opp_hc_test_case import OPPTestCaseHC

bind_cases(OPPTestCaseHC, globals())
