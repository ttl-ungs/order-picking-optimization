"""
Export opp_v5_2_split's functional-test instances for the heuristic
equivalence suite (see tests/infra/factories/v5_equivalence.py).

Runs every test of tests/opp_v5_2_split/functional (needs zimpl and SCIP,
e.g. the optimizacion conda env) with two spies installed:

- build_dat_files: every scenario dict a test writes to the .dat files is
  captured (deep copy) as one instance, tagged with the test method name;
- the v5 solve entry points (OPPTestCaseSplit.run_pipeline for v5's own
  tests, migrated_case.solve_split_from_v4_data for the ones migrated from
  opp_v4, solve_stage1_decomposed for tests that stop at Stage 1): their
  final status, and the objective when solved, are attached to the last
  captured instance.

Tests are otherwise run unchanged (their assertions still execute; a
failing assertion doesn't affect the export). Tests in
KNOWN_SOLVER_TIMEOUTS have their instance captured and are then stopped
before solving, exported with v5_status "timeout" -- a Python alarm can't
interrupt SCIP while it's inside its C solve loop, so they'd otherwise
hang the export just as they time out in the regular suite.

Writes tests/shared_scenarios/functional/v5_equivalence_scenarios.json:
{"instances": [...], "excluded": {test: reason}, "not_captured": [...]}.
Re-run it whenever a v5 functional test or scenario changes:

    python -m tests.shared_scenarios.functional.export_v5_equivalence_scenarios
"""

import copy
import json
import sys
import unittest

import tests.infra.zimpl.dat_files_builder as dat_files_builder
from models.utils.solve_registry import get_last
from tests.infra.factories.v5_equivalence import FIXTURE_PATH, comparability, encode, v5_waiting_batches

# v5 functional tests deliberately left out, with the reason. Everything
# else that reaches the solver is exported.
EXCLUDED = {
    "test_batch_is_delayed_while_early_orders_outweigh_completion_weight": (
        "el test verifica justamente que v5 espere voluntariamente (c_pb > T_exec_pb), algo que las "
        "heurísticas no modelan a propósito (ver W_c en stress_scenarios_v5_designed.py)"
    ),
}


# Tests whose v5 solve doesn't finish (they time out in tests/run_suite.py
# too): captured, then stopped before solving.
KNOWN_SOLVER_TIMEOUTS = {
    "test_fractional_and_zero_capacities_feasible",
}


class _StopBeforeSolve(BaseException):
    """BaseException, so a test's own `except Exception` can't swallow it."""


def _iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
        else:
            yield item


def main():
    suite = unittest.TestLoader().discover("tests/opp_v5_2_split/functional", top_level_dir=".")
    state = {"test": None, "current": None, "capture": True}
    instances = []

    original_build = dat_files_builder.build_dat_files

    def capturing_build(tmpdir, scenario):
        if not state["capture"]:
            return original_build(tmpdir, scenario)
        entry = {
            "v5_test": state["test"],
            "scenario": copy.deepcopy(scenario),
            "v5_status": None,
            "v5_obj": None,
            "fixed_assignment": "X_pb" in scenario,
        }
        instances.append(entry)
        state["current"] = entry
        if state["test"] in KNOWN_SOLVER_TIMEOUTS:
            raise _StopBeforeSolve()
        return original_build(tmpdir, scenario)

    # Tests import build_dat_files by name: patch every loaded module that holds it.
    for module in list(sys.modules.values()):
        if getattr(module, "build_dat_files", None) is original_build:
            module.build_dat_files = capturing_build

    def record(status, values=None, route_times=None):
        entry = state["current"]
        if entry is None:
            return
        entry["v5_status"] = status
        last = get_last()
        entry["v5_obj"] = last.params.get("obj_val") if status in ("optimal", "feasible") and last else None
        if status in ("optimal", "feasible") and values:
            if route_times is None:
                route_times = {
                    name.split("$")[-1]: value for name, value in values.items()
                    if name.lower().startswith("r_b$")
                }
            entry["v5_waiting_batches"] = v5_waiting_batches(entry["scenario"], values, route_times)

    import tests.infra.factories.migrated_case as migrated_case
    from tests.opp_v5_2_split.opp_test_case_v5_2_split import OPPTestCaseSplit

    original_v4_solve = migrated_case.solve_split_from_v4_data

    def recording_v4_solve(*args, **kwargs):
        status, values = original_v4_solve(*args, **kwargs)
        record(status, values)
        return status, values

    migrated_case.solve_split_from_v4_data = recording_v4_solve

    original_pipeline = OPPTestCaseSplit.run_pipeline

    def recording_pipeline(self, scenario, solve_stage2=True):
        try:
            result = original_pipeline(self, scenario, solve_stage2)
        except AssertionError:
            # run_pipeline asserts Stage 1 solved before going on: when it
            # didn't (e.g. a batch with no simple route), v5's outcome is
            # Stage 1's own status, the last solve registered.
            last = get_last()
            record(last.status if last else None)
            raise
        if solve_stage2:
            record(result[2], result[3], result[1])
        else:
            # The test only needed Stage 1; v5's full outcome for this
            # instance comes from a separate full run, not captured again.
            state["capture"] = False
            try:
                full = original_pipeline(self, scenario, True)
                record(full[2], full[3], full[1])
            except AssertionError:
                last = get_last()
                record(last.status if last else None)
            finally:
                state["capture"] = True
        return result

    OPPTestCaseSplit.run_pipeline = recording_pipeline

    # Some tests call Stage 1 directly (e.g. test_case_38): a Stage 1 with no
    # route is v5's final outcome for that instance. A successful Stage 1 is
    # not recorded -- Stage 2's status, if the test gets there, is the outcome.
    import tests.opp_v5_2_split.stage1_decomposition as stage1_decomposition

    original_stage1 = stage1_decomposition.solve_stage1_decomposed

    def recording_stage1(*args, **kwargs):
        status, values = original_stage1(*args, **kwargs)
        if status not in ("optimal", "feasible"):
            record(status)
        return status, values

    for module in list(sys.modules.values()):
        if getattr(module, "solve_stage1_decomposed", None) is original_stage1:
            module.solve_stage1_decomposed = recording_stage1

    not_captured = []
    for test in _iter_tests(suite):
        name = test.id().split(".")[-1]
        if name in EXCLUDED:
            continue
        state["test"], state["current"] = name, None
        before = len(instances)
        try:
            test.run(unittest.TestResult())
        except _StopBeforeSolve:
            pass
        new = instances[before:]
        for entry in new:
            if entry["v5_status"] is None:
                entry["v5_status"] = "timeout" if name in KNOWN_SOLVER_TIMEOUTS else "not_recorded"
            entry.setdefault("v5_waiting_batches", [])
            (entry["comparable_status"], entry["comparable_objective"],
             entry["not_comparable_reason"]) = comparability(entry)
        if not new:
            not_captured.append(name)
        print(f"{name}: {[(e['v5_status'], e['v5_obj'], e['not_comparable_reason']) for e in new] or 'sin instancia (no llega al solver)'}")

    with open(FIXTURE_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "source": "tests/opp_v5_2_split/functional",
            "instances": [encode(e) for e in instances],
            "excluded": EXCLUDED,
            "not_captured": sorted(not_captured),
        }, f, indent=1, sort_keys=True)
    print(f"\n{len(instances)} instancias en {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
