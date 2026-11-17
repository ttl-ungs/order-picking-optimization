"""Functional cases shared by the four models.

Each module `case_NN.py` holds case NN of the thesis' functional tests, written
once: it builds an instance, solves it with `self.solve(...)` or
`self.run_pipeline(...)` and asserts on the solution. A case does not know
which model solves it: `bind_cases` creates, for a model's adapter, one test
class per case class that solves with that model.

Each model's test folder binds the cases in a module of its own:

    from tests.functional_cases import bind_cases
    from tests.opp_split.opp_split_test_case import OPPTestCaseSplit

    bind_cases(OPPTestCaseSplit, globals())

The test methods carry the case number and letter of the thesis in their
docstring ("Case 24a"). The letters follow the alphabetical order of the
methods of the case.
"""

from tests.infra.cases.binding import bind_package_cases


def bind_cases(adapter, namespace):
    """Define in `namespace` a copy of every case that solves with `adapter`.

    `adapter` is the test class of an exact model (OPPTestCaseMono,
    OPPTestCaseSplit). The copies are added to `namespace` under the name of the
    case class, so that the runner can find each test by its dotted name.
    """
    bind_package_cases(__name__, __path__, adapter, namespace)
