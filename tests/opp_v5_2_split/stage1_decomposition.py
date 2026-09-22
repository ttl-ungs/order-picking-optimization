"""
Per-batch decomposition of opp_v5_2_split's Stage 1 (stage1_routing.zpl).

stage1_routing.zpl's own header says batches never interact (every
constraint is `forall <b> in B: ...`, and the objective is a plain sum of
independent R_b_time[b] terms) -- solving all of them together in one MIP
wastes work a MIP branch-and-bound tree doesn't give back. Measured
empirically (2026-09-10/11 audit): the joint solve is ~3x SLOWER than the
sum of solving each batch alone at just 10 batches, and doesn't even
finish within 14 minutes at 20 batches (where the decomposed sum takes a
few seconds) -- MIP solve time grows highly non-linearly with the number
of integer variables (z_ijb/f_ijb, one full set per batch), so keeping
every batch's variables in one model multiplies that cost for nothing:
nothing in the objective or constraints ever links two different batches'
variables.

No change to stage1_routing.zpl itself was needed: it only ever reads
whatever data_B.dat/Bn.dat a caller has written, so calling the exact
same file once per batch (with just those two narrowed to that one
batch) is enough. data_N.dat/a_ni.dat are deliberately left UNTOUCHED
(not just restored after -- never rewritten at all): the model only ever
uses N to sum `A_ni[n,i] * Bn[n,b]` (a plain parameter computation, not a
decision variable), so narrowing N buys nothing and isn't worth the risk
-- an earlier version of this file did narrow it, and a batch with zero
orders assigned (Bn[n,b] == 0 for every n -- a real scenario in this
test suite) turned a_ni.dat into a genuinely empty file, which ZIMPL
rejects at compile time ("Symbol A_ni not initialised"), not the harmless
"parameter with zero rows" it looks like. Keeping data_N.dat/a_ni.dat at
their original (always non-empty, whole-scenario) size sidesteps that
entirely, and costs nothing that matters: the actual combinatorial
complexity driver is z_ijb/f_ijb (indexed by E * B), not the N-indexed
sums, so narrowing B alone already captures the decomposition's benefit.
"""

import os

from tests.infra.zimpl.dat_files_builder import write_set_dat, write_indexed_dat
from tests.opp_v5_2_split.config import STAGE1_ZPL_PATH
from tests.infra.zimpl.zpl_utils import solve_zpl


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


def solve_stage1_decomposed(dat_dir):
    """
    Call AFTER the full scenario's .dat files have already been written
    to `dat_dir` (however the caller normally does that -- build_dat_files(),
    or a migrated v4 fixture's own scenario construction). Decomposes
    Stage 1 into one solve per batch instead of one joint solve for every
    batch together, by temporarily narrowing ONLY data_B.dat/Bn.dat to
    each batch's own column in turn (see module docstring for why
    data_N.dat/a_ni.dat are left untouched), then restoring the ORIGINAL
    (full) contents of those two files before returning -- guaranteed
    even if a solve raises, via `finally` -- so a caller that goes on to
    invoke Stage 2 (which also reads data_B.dat/Bn.dat) sees the correct
    full scenario, not whichever batch was solved last.

    Returns (status, merged_values): status is "optimal"/"feasible" iff
    EVERY batch solved to one of those (the first non-"optimal"/"feasible"
    status found is returned instead, matching what a single joint solve's
    one status would have stood for); merged_values is the union of every
    batch's solved variable dict -- safe to merge as-is, since every
    variable name embeds its own batch id (e.g. "z_ijb$i$j$b"), so
    different batches' entries never collide.
    """
    data_B_path = os.path.join(dat_dir, "data_B.dat")
    bn_path = os.path.join(dat_dir, "Bn.dat")

    # Snapshot the exact original file contents (byte-for-byte) so they
    # can be restored verbatim -- avoids any parse/reserialize mismatch.
    original_data_B = _read_file(data_B_path)
    original_bn = _read_file(bn_path)

    batches = _read_set_dat(data_B_path)
    bn = _read_indexed_dat_pairs(bn_path)

    merged_values = {}
    try:
        for batch in sorted(batches):
            write_set_dat(data_B_path, {batch})
            write_indexed_dat(bn_path, {k: v for k, v in bn.items() if k[1] == batch})

            status, values = solve_zpl(STAGE1_ZPL_PATH, dat_dir=dat_dir)
            if status not in ("optimal", "feasible"):
                return status, merged_values
            merged_values.update(values)
    finally:
        _write_file(data_B_path, original_data_B)
        _write_file(bn_path, original_bn)

    return "optimal", merged_values
