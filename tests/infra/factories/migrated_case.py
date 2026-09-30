"""Adapter that re-runs every normal OPP v4 assertion against OPP v5.2 (two-stage split)."""

import os
import inspect
from importlib import import_module

from tests.infra.zimpl.dat_files_builder import write_indexed_dat, write_scalar_dat
from tests.opp_v5_2_split.config import DAT_DIR, STAGE1_ZPL_PATH, STAGE2_ZPL_PATH
from tests.opp_v5_2_split.stage1_decomposition import solve_stage1_decomposed
from tests.infra.zimpl.zpl_utils import solve_zpl
from models.utils.solve_registry import get_last


def _route_times(values, batches):
    return {
        name.split("$")[-1]: value
        for name, value in values.items()
        if name.lower().startswith("r_b$") and name.split("$")[-1] in batches
    }


# Populated by the most recent solve_split_from_v4_data() call, read right back
# by SplitCompatibilityCase.assert_no_time_overlap() in the same test method
# (each unittest test runs in its own subprocess -- see tests/test_runner.py
# -- so this module-level cache never crosses between tests; same pattern as
# models/utils/solve_registry.py's "last solve" cache).
_last_call_context = {"route_times": {}, "params": {}}


def solve_split_from_v4_data(_zpl_path, dat_dir=None, params=None):
    """Solve the opp_v5_2_split pipeline after a v4 fixture has written its .dat files.

    The v4 normal tests retain their original scenario construction and
    assertions.  This adapter replaces only their single-model solve with the
    opp_v5_2_split routing solve followed by the opp_v5_2_split scheduling solve.
    """
    dat_dir = dat_dir or DAT_DIR
    # Decomposed into one solve per batch instead of one joint solve for
    # every batch (see stage1_decomposition.py's module docstring for the
    # measured speedup) -- STAGE1_ZPL_PATH itself is unchanged. `params`
    # (capacity/duplicate-assignment pre-checks, CSV metadata) isn't
    # threaded into the per-batch solves; it's still applied at the Stage
    # 2 call below with the untouched full scenario, so a genuinely
    # invalid input is still caught -- just there instead of here.
    stage1_status, stage1_values = solve_stage1_decomposed(dat_dir)
    if stage1_status not in ("optimal", "feasible"):
        return stage1_status, stage1_values

    with open(os.path.join(dat_dir, "data_B.dat"), encoding="utf-8") as batches_file:
        batches = {line.strip().strip('"') for line in batches_file if line.strip()}
    with open(os.path.join(dat_dir, "data_P.dat"), encoding="utf-8") as pickers_file:
        pickers = {line.strip().strip('"') for line in pickers_file if line.strip()}

    route_times = _route_times(stage1_values, batches)
    write_indexed_dat(os.path.join(dat_dir, "route_time_b.dat"), route_times)
    write_indexed_dat(os.path.join(dat_dir, "velocities.dat"), {picker: 1.0 for picker in pickers})
    # v4 had no cold-chain restriction; disable it for the migrated baseline.
    write_scalar_dat(os.path.join(dat_dir, "cold.dat"), 1_000_000_000.0)

    # Stash what assert_no_time_overlap needs to recompute each task's
    # duration itself (see that method's docstring for why: opp_v5_2_split has no u_pb).
    _last_call_context["route_times"] = route_times
    _last_call_context["params"] = params or {}

    stage2_status, stage2_values = solve_zpl(STAGE2_ZPL_PATH, dat_dir=dat_dir, params=params)
    # The saved solution (WRITE_SOLUTIONS) needs Stage 1 too: Stage 2 only
    # sees the routes' times, not the routes themselves.
    record = getattr(get_last(), "solution_record", None)
    if record is not None:
        record.add_stage1_values(stage1_values)
    return stage2_status, {**stage1_values, **stage2_values}


def make_split_compat_case(v4_module, v4_case):
    """Create an isolated subclass whose inherited test methods exercise opp_v5_2_split."""

    class SplitCompatibilityCase(v4_case):
        def setUp(self):
            super().setUp()
            self._original_solve = v4_module.solve_zpl
            v4_module.solve_zpl = solve_split_from_v4_data

        def tearDown(self):
            v4_module.solve_zpl = self._original_solve
            parent_tear_down = getattr(super(), "tearDown", None)
            if parent_tear_down:
                parent_tear_down()

        def assert_no_time_overlap(self, var_values, P, B):
            """
            Overrides opp_v4's OPPTestCaseV4.assert_no_time_overlap (which
            reconstructs a task's duration as c_pb - u_pb): opp_model_v5_2_split_stage2_scheduling.zpl
            has no u_pb variable at all (opp_v5_2_split replaced it with the fixed
            parameter T_exec_pb, see that file's header) -- var_values never
            contains a "u_pb$..." key, so u_pb.get(...) always returned 0
            there, silently turning the whole overlap check into a tautology
            (duration always came out as 0, so "start" == "end" == c_pb, and
            the sorted-by-c_pb comparison could never fail regardless of
            whether batches actually overlapped). Found 2026-09-09 auditing
            opp_v5_2_split -- this let the migrated test_case_13/11 report
            "ok" without ever checking the very thing they're named for.

            Recomputes duration the same way OPPTestCaseSplit.assert_no_overlap
            already does correctly for opp_v5_2_split's own (non-migrated) stress tests:
            fixed_time(b) + route_time(b) / V_p[picker]. V_p is fixed to 1.0
            for every picker in this migrated baseline (see
            solve_split_from_v4_data), so this reduces to fixed_time(b) +
            route_time(b) -- the same d_b formula opp_v4 itself uses,
            just computed independently instead of trusting a variable that
            no longer exists.
            """
            route_times = _last_call_context.get("route_times", {})
            params = _last_call_context.get("params") or {}
            T_setup = params.get("T_setup", 0.0)
            T_pick = params.get("T_pick", 0.0)
            C_n = params.get("C_n", {}) or {}
            B_nb = params.get("B_nb", {}) or {}

            def duration(batch):
                orders_in_batch = [n for (n, b), assigned in B_nb.items() if b == batch and assigned]
                fixed_time = T_setup + T_pick * sum(C_n.get(n, 0.0) for n in orders_in_batch)
                return fixed_time + route_times.get(batch, 0.0)

            x_pb, c_pb = {}, {}
            for key, val in var_values.items():
                k = key.lower()
                p_match = [p for p in P if p in key]
                b_match = [b for b in B if b in key]
                if p_match and b_match:
                    p, b = p_match[0], b_match[0]
                    if k.startswith("x_pb"):
                        x_pb[(p, b)] = val
                    elif k.startswith("c_pb"):
                        c_pb[(p, b)] = val

            for p in P:
                tasks = sorted(
                    (c_pb.get((p, b), 0) - duration(b), c_pb.get((p, b), 0), b)
                    for b in B if x_pb.get((p, b), 0) > 0.5
                )
                for i in range(len(tasks) - 1):
                    self.assertGreaterEqual(
                        tasks[i + 1][0], tasks[i][1] - 1e-4, f"Solapamiento temporal en {p}"
                    )

    return SplitCompatibilityCase


def migrated_case(v4_module_path):
    """Return the single normal-test class exported by a v4 test module."""
    module = import_module(v4_module_path)
    candidates = [
        value for value in module.__dict__.values()
        if isinstance(value, type) and value.__module__ == v4_module_path
        and value.__name__.startswith("Test")
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one test case in {v4_module_path}, found {candidates}")
    case = make_split_compat_case(module, candidates[0])
    # TestRunner launches each unittest from its dotted id.  Give the dynamic
    # subclass a stable public address in the calling opp_v5_2_split test module.
    case.__name__ = "TestMigrated"
    case.__qualname__ = "TestMigrated"
    case.__module__ = inspect.currentframe().f_back.f_globals["__name__"]
    return case
