"""The functional cases of the thesis, solved with OPP-ACO."""

from tests.functional_cases import bind_cases
from tests.opp_aco.opp_aco_test_case import OPPTestCaseACO

bind_cases(OPPTestCaseACO, globals())
