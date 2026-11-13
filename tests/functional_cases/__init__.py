"""Functional cases shared by the exact models (monolithic and Split).

Each module `case_NN.py` holds case NN of the thesis' functional tests, written
once: it builds an instance, solves it with `self.solve(...)` or
`self.run_pipeline(...)` and asserts on the solution. A case does not know
which model solves it: `bind_cases` creates, for a model's adapter, one test
class per case class that solves with that model.

Each model's test folder binds the cases in a module of its own:

    from tests.functional_cases import bind_cases
    from tests.opp_v5_2_split.opp_test_case_v5_2_split import OPPTestCaseSplit

    bind_cases(OPPTestCaseSplit, globals())

The test methods carry the case number and letter of the thesis in their
docstring ("Case 24a"). The letters follow the alphabetical order of the
methods of the case.
"""

import importlib
import inspect
import pkgutil
import unittest


def bind_cases(adapter, namespace):
    """Define in `namespace` a copy of every case that solves with `adapter`.

    `adapter` is the test class of an exact model (OPPTestCaseMono,
    OPPTestCaseSplit). The copies are added to `namespace` under the name of the
    case class, so that the runner can find each test by its dotted name.
    """
    for module_info in sorted(pkgutil.iter_modules(__path__), key=lambda info: info.name):
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        for name, case in vars(module).items():
            if inspect.isclass(case) and issubclass(case, unittest.TestCase) and case.__module__ == module.__name__:
                namespace[name] = type(
                    name, (adapter, case), {"__module__": namespace["__name__"], "__doc__": case.__doc__}
                )
