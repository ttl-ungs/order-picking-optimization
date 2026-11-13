"""
Per-batch decomposition of opp_split's Stage 1 (opp_split_stage1_routing.zpl).

opp_split_stage1_routing.zpl's own header says batches never interact (every
constraint is `forall <b> in B: ...`, and the objective is a plain sum of
independent r_b[b] terms) -- solving all of them together in one MIP
wastes work a MIP branch-and-bound tree doesn't give back. Measured
empirically (2026-09-10/11 audit): the joint solve is ~3x SLOWER than the
sum of solving each batch alone at just 10 batches, and doesn't even
finish within 14 minutes at 20 batches (where the decomposed sum takes a
few seconds) -- MIP solve time grows highly non-linearly with the number
of integer variables (z_ijb/q_ijb, one full set per batch), so keeping
every batch's variables in one model multiplies that cost for nothing:
nothing in the objective or constraints ever links two different batches'
variables.

No change to opp_split_stage1_routing.zpl itself was needed: it only ever reads
whatever data_B.dat/B_nb.dat a caller has written, so calling the exact
same file once per batch (with just those two narrowed to that one
batch) is enough. data_N.dat/a_ni.dat are deliberately left UNTOUCHED
(not just restored after -- never rewritten at all): the model only ever
uses N to sum `A_ni[n,i] * B_nb[n,b]` (a plain parameter computation, not a
decision variable), so narrowing N buys nothing and isn't worth the risk
-- an earlier version of this file did narrow it, and a batch with zero
orders assigned (B_nb[n,b] == 0 for every n -- a real scenario in this
test suite) turned a_ni.dat into a genuinely empty file, which ZIMPL
rejects at compile time ("Symbol A_ni not initialised"), not the harmless
"parameter with zero rows" it looks like. Keeping data_N.dat/a_ni.dat at
their original (always non-empty, whole-scenario) size sidesteps that
entirely, and costs nothing that matters: the actual combinatorial
complexity driver is z_ijb/q_ijb (indexed by E * B), not the N-indexed
sums, so narrowing B alone already captures the decomposition's benefit.

Parallel mode is OPT-IN, via OPP_STAGE1_WORKERS=<n> (default: sequential).
Each batch is then solved in its own temporary directory by a separate OS
process via ProcessPoolExecutor. Each worker gets a copy of the dat_files/
directory with data_B.dat/B_nb.dat narrowed to its batch, plus a copy of the
ZPL file so that ZIMPL's relative-path reads (../dat_files/...) resolve
into the worker's own directory regardless of whether ZIMPL resolves paths
relative to CWD or to the ZPL file's location.

It defaults to off because wall-clock timings are what this repo measures
to compare models: with parallel batch solves those timings depend on how
much CPU and RAM happened to be free at the time, which makes runs
non-reproducible and not comparable against opp_mono (which cannot
decompose, so it never gets the same treatment).
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
    Call AFTER the full scenario's .dat files have already been written
    to `dat_dir` (however the caller normally does that -- build_dat_files(),
    or a test's own scenario construction). Decomposes
    Stage 1 into one solve per batch instead of one joint solve for every
    batch together, by temporarily narrowing ONLY data_B.dat/B_nb.dat to
    each batch's own column in turn (see module docstring for why
    data_N.dat/a_ni.dat are left untouched), then restoring the ORIGINAL
    (full) contents of those two files before returning -- guaranteed
    even if a solve raises, via `finally` -- so a caller that goes on to
    invoke Stage 2 (which also reads data_B.dat/B_nb.dat) sees the correct
    full scenario, not whichever batch was solved last.

    Sequential by default. Set OPP_STAGE1_WORKERS=<n> (or pass max_workers)
    to solve batches in parallel instead, using separate OS processes, up
    to <n> at a time; each works on its own copy of the dat files in a temp
    directory, so the original dat_dir is never modified. Parallel needs
    more than 4 batches to be worth its process-spawn overhead.

    Returns (status, merged_values): status is "optimal"/"feasible" iff
    EVERY batch solved to one of those (the first non-"optimal"/"feasible"
    status found is returned instead, matching what a single joint solve's
    one status would have stood for); merged_values is the union of every
    batch's solved variable dict -- safe to merge as-is, since every
    variable name embeds its own batch id (e.g. "z_ijb$i$j$b"), so
    different batches' entries never collide.

    time_budget_seconds (optional, sequential only): a total wall-clock
    budget for Stage 1, split evenly over the batches still to solve
    (each batch's SCIP limits/time = remaining budget / batches left), for
    analysis/run_equal_time_study.py. A batch cut by its limit still counts
    if SCIP had an incumbent route for it; the overall status is then
    "timelimit" instead of "optimal". A batch with no route at all within
    its share ends Stage 1 with that status and no complete solution.
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
