"""Stress cases shared by the four models.

Each module `case_NN.py` holds stress scenario NN, written once: it builds the
instance and hands it to `self.assert_stress_pipeline(scenario)`. A case does
not know which model solves it: each model's adapter implements
`assert_stress_pipeline` (solve, check that every batch has a picker, that the
routes cover the required locations and that no picker has overlapping
batches), and `bind_cases` creates, for that adapter, one test class per case.

Each model's stress folder binds the cases in a module of its own:

    from tests.stress_cases import bind_cases
    from tests.opp_v5_2_split.stress.stress_test_case import OPPSplitStressTestCase

    bind_cases(OPPSplitStressTestCase, globals())
"""

from tests.infra.cases.binding import bind_package_cases


def bind_cases(adapter, namespace):
    """Define in `namespace` a copy of every stress case that solves with `adapter`."""
    bind_package_cases(__name__, __path__, adapter, namespace)
