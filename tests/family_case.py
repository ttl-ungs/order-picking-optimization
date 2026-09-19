"""Factory that adapts a canonical HC/ACO test module to a sibling family
(opp_hc_2 -> opp_hc_3/opp_hc_4, opp_aco_2 -> opp_aco_3/opp_aco_4) without
touching a single assertion.

Same idea as tests.opp_v5.v4_compat.migrated_case(): every test
method resolves its model/DTO/output-handler classes as plain module-level
names at CALL time (e.g. `params = SolveHCModelDTO()`, `model =
OPPHillClimbing(model_dto)`), so replacing what those names are bound to in
the base module's namespace changes which family's classes actually run,
without changing a single line of test source. v4_compat.py's variant swaps
one function (solve_zpl); this one generalizes it to N names, since the
Python-model families reference their model/DTO/output-handler classes
directly rather than through one solve() entry point.

Unlike v4_compat.py (used only by opp_v5's own tests, one base module ever
maps to one target), the SAME opp_hc_2/opp_aco_2 base module is reused by
TWO targets each (hc_3 AND hc_4; aco_3 AND aco_4). Python caches imported
modules by name, so if `unittest discover` ever loads hc_3's and hc_4's
adapted copies of the same base module in one process (it does today, e.g.
via `python -m unittest discover`), a permanent module-level monkeypatch
from one family would silently clobber the other's. To stay safe under
that scenario, the patch is applied in setUp() and reverted in tearDown()
-- scoped to exactly the duration of each test method's execution, not to
however long the module happens to stay imported.
"""

import importlib
import inspect

_MISSING = object()


def family_case(base_module_path, overrides):
    """Return a TestCase subclass that runs base_module_path's test(s)
    against a different model family.

    Args:
        base_module_path (str): dotted path to the canonical test module,
            e.g. 'tests.opp_hc_2.functional.test_opp_hc_2_model_02'.
        overrides (dict): {name_as_referenced_in_base_module: replacement}.
            Keys must match the exact identifier the base module's test
            methods use (e.g. 'OPPHillClimbing', 'SolveHCModelDTO',
            'OutputHandler' for ACO) -- not necessarily the replacement
            class's own __name__.

    Returns:
        type: a unittest.TestCase subclass, ready to be assigned to a
        module-level name in the target family's test file so
        `unittest discover` picks it up.
    """
    base_module = importlib.import_module(base_module_path)
    candidates = [
        value
        for value in base_module.__dict__.values()
        if isinstance(value, type)
        and value.__module__ == base_module_path
        and value.__name__.startswith("Test")
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one Test* class in {base_module_path}, found {len(candidates)}: "
            f"{[c.__name__ for c in candidates]}"
        )
    base_case = candidates[0]

    class FamilyCase(base_case):
        def setUp(self):
            self._family_case_saved = {
                name: base_module.__dict__.get(name, _MISSING) for name in overrides
            }
            base_module.__dict__.update(overrides)
            super().setUp()

        def tearDown(self):
            try:
                super().tearDown()
            finally:
                for name, old_value in self._family_case_saved.items():
                    if old_value is _MISSING:
                        base_module.__dict__.pop(name, None)
                    else:
                        base_module.__dict__[name] = old_value

    # TestRunner/unittest address tests by dotted id (module.Class.method) --
    # give the dynamic subclass a stable public address in the CALLING
    # module (the target family's test file), not tests.family_case where
    # it's actually defined. Same trick as v4_compat.py's migrated_case().
    FamilyCase.__name__ = base_case.__name__
    FamilyCase.__qualname__ = base_case.__qualname__
    FamilyCase.__module__ = inspect.currentframe().f_back.f_globals["__name__"]
    return FamilyCase
