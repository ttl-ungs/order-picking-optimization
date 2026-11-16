"""The functional cases of the thesis, solved with the monolithic model."""

from tests.functional_cases import bind_cases
from tests.opp_mono.opp_mono_test_case import OPPTestCaseMono

bind_cases(OPPTestCaseMono, globals())
