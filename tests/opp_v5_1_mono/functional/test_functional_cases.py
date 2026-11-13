"""The functional cases of the thesis, solved with the monolithic model."""

from tests.functional_cases import bind_cases
from tests.opp_v5_1_mono.opp_test_case_v5_1_mono import OPPTestCaseMono

bind_cases(OPPTestCaseMono, globals())
