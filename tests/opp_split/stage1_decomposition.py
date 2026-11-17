"""
Per-batch decomposition of OPP-Split's Stage 1 (opp_split_stage1_routing.zpl).

Batches never interact in Stage 1 (every constraint is per batch and the
objective is a sum of independent r_b), but a joint MIP does not exploit
that: solve time grows much faster than linearly with the integer variables
(z_ijb, q_ijb: one full set per batch). Measured: with 10 batches the joint
solve takes about three times the sum of the per-batch solves, and with 20 it
does not finish in 14 minutes while the per-batch solves take seconds.

The .zpl is used as it is, once per batch, with data_B.dat and B_nb.dat
narrowed to that batch. data_N.dat and a_ni.dat are left whole: the model
only uses N inside sums of parameters, so narrowing it gains nothing, and a
batch without orders would leave a_ni.dat empty, which ZIMPL rejects when it
compiles.

Parallel mode is opt-in (OPP_STAGE1_WORKERS=<n>; sequential by default). Each
batch is then solved by a separate process in its own temporary directory: a
copy of dat_files/ narrowed to the batch, next to a copy of the .zpl, so that
its relative reads (../dat_files/...) resolve inside that directory. It is
off by default because the repository compares models by wall-clock time,
and parallel solves make it depend on the free CPU and RAM and not comparable
with OPP-Mono, which cannot be decomposed.
"""

import os
import shutil
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from tests.infra.zimpl.dat_files_builder import write_set_dat, write_indexed_dat
from tests.opp_split.config import STAGE1_ZPL_PATH
from tests.infra.zimpl.zpl_utils import solve_zpl

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def _default_workers(batch_count):
    """Worker count from OPP_STAGE1_WORKERS; 1 (sequential) when unset or unparseable."""
    raw = os.environ.get("OPP_STAGE1_WORKERS", "").strip()
    if not raw:
        return 1
    try:
        return max(1, min(int(raw), batch_count))
    except ValueError:
        return 1


def _solve_one_batch(zpl_path, worker_dat_dir):
    """Solve a single batch in an isolated temp directory (child process)."""
    from tests.infra.zimpl.zpl_utils import solve_zpl as _solve
    return _solve(zpl_path, dat_dir=worker_dat_dir)


def _read_set_dat(path):
    with open(path, encoding="utf-8") as f:
        return {line.strip().strip('"') for line in f if line.strip()}


def _read_indexed_dat_pairs(path):
    """Reads a 2-key indexed .dat file ('"k1" "k2" value' per line) into {(k1, k2): value}."""
    result = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            k1_raw, k2_raw, value_raw = line.split()
            result[(k1_raw.strip('"'), k2_raw.strip('"'))] = float(value_raw)
    return result


def _read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def solve_stage1_decomposed(dat_dir, max_workers=None, time_budget_seconds=None):
    """
    Solve Stage 1 one batch at a time. The scenario's .dat files must already
    be in `dat_dir`.

    Sequentially, data_B.dat and B_nb.dat are narrowed to each batch in turn
    and restored before returning (in a `finally`), so that Stage 2 reads the
    full scenario. With OPP_STAGE1_WORKERS=<n> (or max_workers) and more than
    4 batches, up to <n> processes solve the batches in parallel, each on its
    own copy of the files.

    Returns (status, merged_values). The status is "optimal"/"feasible" iff
    every batch reached one of those; otherwise it is the first other status
    found. merged_values is the union of the batches' variable values (every
    name carries its batch id, so they never collide).

    time_budget_seconds (optional, sequential only): a total wall-clock
    budget, split evenly over the batches still to solve, for
    experiments/comparison/run_equal_time_study.py. A batch cut by its limit
    counts if SCIP had a route for it, and the status is then "timelimit"; a
    batch with no route within its share ends Stage 1 with that status.
    """
    data_B_path = os.path.join(dat_dir, "data_B.dat")
    bn_path = os.path.join(dat_dir, "B_nb.dat")

    batches = _read_set_dat(data_B_path)
    bn = _read_indexed_dat_pairs(bn_path)

    if time_budget_seconds is not None:
        return _solve_sequential(dat_dir, batches, bn, data_B_path, bn_path, time_budget_seconds)

    if max_workers is None:
        max_workers = _default_workers(len(batches))

    # Parallel overhead (spawning processes, copying dat files) only pays off
    # with enough batches; for small instances the sequential path is faster.
    if len(batches) <= 4 or max_workers <= 1:
        return _solve_sequential(dat_dir, batches, bn, data_B_path, bn_path)

    return _solve_parallel(dat_dir, batches, bn, max_workers)


def _solve_sequential(dat_dir, batches, bn, data_B_path, bn_path, time_budget_seconds=None):
    original_data_B = _read_file(data_B_path)
    original_bn = _read_file(bn_path)
    merged_values = {}
    overall = "optimal"
    deadline = time.time() + time_budget_seconds if time_budget_seconds is not None else None
    try:
        ordered = sorted(batches)
        for index, batch in enumerate(ordered):
            limit = None
            if deadline is not None:
                limit = max(deadline - time.time(), 0.0) / (len(ordered) - index)
                if limit <= 0.0:
                    return "timelimit", merged_values
            write_set_dat(data_B_path, {batch})
            write_indexed_dat(bn_path, {k: v for k, v in bn.items() if k[1] == batch})
            status, values = solve_zpl(STAGE1_ZPL_PATH, dat_dir=dat_dir, time_limit_seconds=limit)
            if status == "timelimit" and values:
                overall = "timelimit"
            elif status not in ("optimal", "feasible"):
                return status, merged_values
            merged_values.update(values)
    finally:
        _write_file(data_B_path, original_data_B)
        _write_file(bn_path, original_bn)
    return overall, merged_values


def _solve_parallel(dat_dir, batches, bn, max_workers):
    zpl_basename = os.path.basename(STAGE1_ZPL_PATH)
    zpl_parent_name = os.path.basename(os.path.dirname(STAGE1_ZPL_PATH))

    old_pythonpath = os.environ.get("PYTHONPATH", "")
    if _PROJECT_ROOT not in old_pythonpath.split(os.pathsep):
        os.environ["PYTHONPATH"] = _PROJECT_ROOT + (os.pathsep + old_pythonpath if old_pythonpath else "")

    tmp_base = tempfile.mkdtemp(prefix="opp_stage1_")
    try:
        worker_args = []
        for batch in sorted(batches):
            worker_root = os.path.join(tmp_base, batch)
            worker_dat = os.path.join(worker_root, "dat_files")
            worker_zpl_dir = os.path.join(worker_root, zpl_parent_name)

            shutil.copytree(dat_dir, worker_dat)
            os.makedirs(worker_zpl_dir, exist_ok=True)
            shutil.copy2(STAGE1_ZPL_PATH, worker_zpl_dir)

            write_set_dat(os.path.join(worker_dat, "data_B.dat"), {batch})
            write_indexed_dat(
                os.path.join(worker_dat, "B_nb.dat"),
                {k: v for k, v in bn.items() if k[1] == batch},
            )

            worker_zpl = os.path.join(worker_zpl_dir, zpl_basename)
            worker_args.append((batch, worker_zpl, worker_dat))

        merged_values = {}
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch = {
                executor.submit(_solve_one_batch, zpl, dat): batch
                for batch, zpl, dat in worker_args
            }
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                status, values = future.result()
                if status not in ("optimal", "feasible"):
                    for f in future_to_batch:
                        f.cancel()
                    return status, merged_values
                merged_values.update(values)

        return "optimal", merged_values
    finally:
        shutil.rmtree(tmp_base, ignore_errors=True)
        os.environ["PYTHONPATH"] = old_pythonpath
