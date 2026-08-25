"""Adapter that re-runs every normal OPP v4 assertion against OPP v5."""

import os
import inspect
from importlib import import_module

from models.utils.dat_files_builder import write_indexed_dat, write_scalar_dat
from tests.opp_v5.config import DAT_DIR, STAGE1_ZPL_PATH, STAGE2_ZPL_PATH
from tests.utils.zpl_utils import solve_zpl


def _route_times(values, batches):
    return {
        name.split("$")[-1]: value
        for name, value in values.items()
        if name.lower().startswith("r_b_time$") and name.split("$")[-1] in batches
    }


def solve_v5_from_v4_data(_zpl_path, dat_dir=None, params=None):
    """Solve the v5 pipeline after a v4 fixture has written its .dat files.

    The v4 normal tests retain their original scenario construction and
    assertions.  This adapter replaces only their single-model solve with the
    v5 routing solve followed by the v5 scheduling solve.
    """
    dat_dir = dat_dir or DAT_DIR
    stage1_status, stage1_values = solve_zpl(STAGE1_ZPL_PATH, dat_dir=dat_dir, params=params)
    if stage1_status not in ("optimal", "feasible"):
        return stage1_status, stage1_values

    with open(os.path.join(dat_dir, "data_B.dat"), encoding="utf-8") as batches_file:
        batches = {line.strip().strip('"') for line in batches_file if line.strip()}
    with open(os.path.join(dat_dir, "data_P.dat"), encoding="utf-8") as pickers_file:
        pickers = {line.strip().strip('"') for line in pickers_file if line.strip()}

    write_indexed_dat(os.path.join(dat_dir, "route_time_b.dat"), _route_times(stage1_values, batches))
    write_indexed_dat(os.path.join(dat_dir, "velocities.dat"), {picker: 1.0 for picker in pickers})
    # v4 had no cold-chain restriction; disable it for the migrated baseline.
    write_scalar_dat(os.path.join(dat_dir, "frio.dat"), 1_000_000_000.0)

    stage2_status, stage2_values = solve_zpl(STAGE2_ZPL_PATH, dat_dir=dat_dir, params=params)
    return stage2_status, {**stage1_values, **stage2_values}


def make_v5_compat_case(v4_module, v4_case):
    """Create an isolated subclass whose inherited test methods exercise v5."""

    class V5CompatibilityCase(v4_case):
        def setUp(self):
            super().setUp()
            self._original_solve = v4_module.solve_zpl
            v4_module.solve_zpl = solve_v5_from_v4_data

        def tearDown(self):
            v4_module.solve_zpl = self._original_solve
            parent_tear_down = getattr(super(), "tearDown", None)
            if parent_tear_down:
                parent_tear_down()

    return V5CompatibilityCase


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
    case = make_v5_compat_case(module, candidates[0])
    # TestRunner launches each unittest from its dotted id.  Give the dynamic
    # subclass a stable public address in the calling v5 test module.
    case.__name__ = "TestMigrated"
    case.__qualname__ = "TestMigrated"
    case.__module__ = inspect.currentframe().f_back.f_globals["__name__"]
    return case
