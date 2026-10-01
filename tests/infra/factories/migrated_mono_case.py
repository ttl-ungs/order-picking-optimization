"""Adapter that re-runs every functional OPP v4 test against OPP v5.1 (monolithic)."""

import inspect
from importlib import import_module

from tests.opp_v5_1_mono.config import ZPL_PATH


def make_mono_compat_case(v4_module, v4_case):
    """Create an isolated subclass whose inherited test methods exercise opp_v5_1_mono.

    The v4 tests keep their scenario construction and assertions untouched;
    only the .zpl they solve changes. Every v4 test module binds the model
    path as the module-level name ZPL_PATH, so pointing that name at the
    monolithic model for the duration of a test is enough. opp_v5_1_mono keeps
    u_pb, so OPPTestCaseV4.assert_no_time_overlap (duration = c_pb - u_pb)
    keeps working as is.
    """

    class MonoCompatibilityCase(v4_case):
        def setUp(self):
            super().setUp()
            self._original_zpl_path = v4_module.ZPL_PATH
            v4_module.ZPL_PATH = ZPL_PATH

        def tearDown(self):
            v4_module.ZPL_PATH = self._original_zpl_path
            parent_tear_down = getattr(super(), "tearDown", None)
            if parent_tear_down:
                parent_tear_down()

    return MonoCompatibilityCase


def migrated_mono_case(v4_module_path):
    """Return the single functional-test class exported by a v4 test module."""
    module = import_module(v4_module_path)
    candidates = [
        value for value in module.__dict__.values()
        if isinstance(value, type) and value.__module__ == v4_module_path
        and value.__name__.startswith("Test")
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one test case in {v4_module_path}, found {candidates}")
    case = make_mono_compat_case(module, candidates[0])
    # TestRunner launches each unittest from its dotted id.  Give the dynamic
    # subclass a stable public address in the calling test module.
    case.__name__ = "TestMigrated"
    case.__qualname__ = "TestMigrated"
    case.__module__ = inspect.currentframe().f_back.f_globals["__name__"]
    return case
