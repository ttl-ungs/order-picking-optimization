"""Map where each instance dimension stops being solvable, and calibrate candidate scenarios.

    python -m experiments.opp_v5.exploration --study 08_x                          # sweep every axis (split)
    python -m experiments.opp_v5.exploration --study 08_x --axes orders batches    # only those two
    python -m experiments.opp_v5.exploration --study 08_x --base 6,2,26,7          # batches,pickers,orders_per_batch,side
    python -m experiments.opp_v5.exploration --study 08_x --weights 4,5 --speed-spread 0.2 --speed-tiers 2
    python -m experiments.opp_v5.exploration --study 08_x --points experiments/opp_v5/studies/08_x/points.json
    python -m experiments.opp_v5.exploration --study 08_x --frontier --frontier-batches 1,2,3,4,6 --frontier-sides 3,4,5,6,7

Why this exists rather than more stress tests: a test answers "does this one
instance solve", while a sweep gives the curve -- where an axis bends, where it
breaks, and how the search tree behaves on the way. The 2026-09-22/23 runs are
what showed that batches is the tightest axis for Stage 2, that warehouse size
is what breaks Stage 1, and that realistic (tiered) picker speeds shrink the
solvable region far below what uniform speeds suggest.

Every configuration is solved in its OWN process and killed from outside when
its wall-clock budget (`hard_cap_s`) runs out. That is not optional: SCIP's
`limits/time` is only checked between operations, and a single huge LP ran a
300s limit out to 3079s on 2026-09-23; Stage 1 has no limit at all. The kill
covers the whole process tree, so a zimpl compile or SCIP solve in flight goes
with it. The row still gets written, with the stage the point died in, the
solutions found so far and the peak memory reported so far.

Each row is flushed as it is measured, so an interrupted run keeps everything
up to the points in flight. Results go to experiments/opp_v5/studies/<study>/,
next to the points file that produced them (see experiments/opp_v5/README.md),
and deliberately NOT to results/<model>/<tier>/, because analysis/load.py globs
that pattern and would pick these files up as if they were test runs.

Columns worth reading together:
    bb_nodes             branch-and-bound nodes -- structural; unlike wall time
                         it does not move with machine load. The same instance
                         always gives the same count (SCIP is deterministic), so
                         it is the fair way to compare across runs made under
                         different load.
    sla_pct              share of orders on time. Near 0% or near 100% means
                         the objective is flat and the solver churns.
    batch_locations_*    distinct locations a batch must reach -- what Stage 1
                         pays for, together with the grid size itself.
    first_sol_s          when SCIP found its first feasible solution.
    root_dual, dual      the dual bound after the root node and at the end.
    ref_obj ...          only for `pair` points: the split's proven optimum is
                         the reference the monolithic run is measured against
                         (the two models share their optimum). It separates
                         FINDING a good solution (time_to_1pct_s, time_to_opt_s,
                         best_gap_to_opt_pct) from PROVING it (dual_ratio_pct,
                         root_dual_ratio_pct: dual bound as a share of the true
                         optimum).
    incumbents           every improving solution as seconds:objective.

Points file (--points) is a JSON list of objects:
    {"label": "A1", "model": "split", "batches": 6, "pickers": 3,
     "orders_per_batch": 26, "side": 12, "weights": [4, 5], "speed_spread": 0.2,
     "speed_tiers": 2, "hard_cap_s": 1500}
`model` is "split" (default), "mono", or "pair" (the same instance solved by
both, split first; writes two rows). Missing `hard_cap_s` takes --hard-cap.
`"stage1_only": true` stops the split after Stage 1 -- for questions that are
purely about routing. (A `"closure"` key in older points files is ignored: the
Stage 1 metric closure was removed on 2026-09-23.)
`"stage1_workers": n` (split only) sets OPP_STAGE1_WORKERS for that point, so
sequential and parallel Stage 1 can be compared within one points file.
`"relax_le1": true` removes the `<= 1` per-vertex limits (Stage 1's in the
split, the routing part's in the monolithic model; same constraint names) from
that process's temp copy of the model -- a trial, never applied to models/.

--frontier walks a grid of batches x grid side for `pair` points, pickers set
by --batches-per-picker. Batches go up row by row and sides left to right; once
the monolithic model fails to prove an optimum the split did prove at some
side, that side and every larger one are skipped for all remaining rows (a
larger instance of the same profile is assumed no easier). Instances both
models find infeasible do not count as failures. Skipped points are still
written, with status `skipped`, so the grid stays visible.
"""

import argparse
import csv
import json
import multiprocessing
import os
import queue as queue_lib
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.infra.execution.runner import _kill_process_tree

FIELDS = [
    "label", "model", "variant", "batches", "pickers", "orders_per_batch", "grid", "vertices",
    "weights", "speed_spread", "speed_tiers", "speeds",
    "batch_locations_min", "batch_locations_max",
    "stage1_s", "stage2_s", "zimpl_s", "mono_s", "total_s", "hard_cap_s",
    "status", "obj", "gap_pct", "bb_nodes", "sla_pct",
    "route_min", "route_max", "estimated_finish",
    "n_vars", "n_conss", "lp_mb", "peak_rss_mb",
    "first_sol_s", "first_sol_obj", "n_incumbents", "root_dual", "dual",
    "ref_obj", "first_gap_to_opt_pct", "best_gap_to_opt_pct",
    "time_to_1pct_s", "time_to_opt_s", "dual_ratio_pct", "root_dual_ratio_pct",
    "incumbents",
]

# Ranges walk outward from the base. Geometric-ish steps cover ground without
# spending the budget repeatedly near the edge, which is where points are slowest.
AXES = {
    "orders": (10, 14, 18, 22, 26, 32, 40, 50),
    "batches": (6, 8, 10, 12, 14),
    "pickers": (2, 3, 4, 5, 6),
    "warehouse": (7, 10, 15, 20),
}


def _point_row(point):
    """The columns that come straight from the configuration, before any solve."""
    weights = point.get("weights", [4, 4])
    return {
        "label": point.get("label", ""),
        "model": point.get("model", "split"),
        "batches": point["batches"],
        "pickers": point["pickers"],
        "orders_per_batch": point["orders_per_batch"],
        "grid": f"{point['side']}x{point['side']}",
        "weights": f"{weights[0]}/{weights[1]}",
        "speed_spread": point.get("speed_spread", 0.0),
        "speed_tiers": point.get("speed_tiers") or ("all" if point.get("speed_spread") else "-"),
        "hard_cap_s": point["hard_cap_s"],
        "variant": ("no_le1 " if point.get("relax_le1") else "") + "full_graph"
                   + (f" workers={point['stage1_workers']}" if "stage1_workers" in point else ""),
    }


def _scenario(point):
    from tests.shared_scenarios.stress.stress_scenarios_v5_designed import designed_stress_scenario

    weights = point.get("weights", [4, 4])
    return designed_stress_scenario(
        point["batches"], point["pickers"], point["batches"] * point["orders_per_batch"],
        point["side"], point["side"],
        speed_spread=point.get("speed_spread", 0.0),
        speed_tiers=point.get("speed_tiers"),
        vertical_weight=weights[0],
        horizontal_weight=weights[1],
    )


def _describe(point, scenario):
    row = _point_row(point)
    per_batch = [
        len({v for v in scenario["V"]
             if any(scenario["A_ni"][(n, v)] * scenario["Bn"][(n, b)] for n in scenario["N"])})
        for b in sorted(scenario["B"])
    ]
    row["vertices"] = len(scenario["V"])
    row["batch_locations_min"], row["batch_locations_max"] = min(per_batch), max(per_batch)
    row["speeds"] = "|".join(f"{s:.2f}" for s in sorted(set(scenario["V_p"].values())))
    return row


def _report_memory(q, stop):
    """Send this process's peak RSS every few seconds, so it survives a hard kill."""
    from tests.infra.execution.runner import _peak_rss_mb

    while not stop.wait(5.0):
        q.put(("mem", _peak_rss_mb()))


def _solve_lp(lp_path, soft_limit, q):
    """Solve a compiled .lp with SCIP. `soft_limit` lets SCIP stop cleanly on its
    own in the common case; the hard kill in `bounded` is the backstop. Every
    improving solution is streamed to the parent as it is found."""
    import pyscipopt
    from pyscipopt import Eventhdlr, SCIP_EVENTTYPE

    class _Incumbents(Eventhdlr):
        def eventinit(self):
            self.model.catchEvent(SCIP_EVENTTYPE.BESTSOLFOUND, self)

        def eventexec(self, event):
            m = self.model
            q.put(("incumbent", (round(m.getSolvingTime(), 2), m.getSolObjVal(m.getBestSol()))))

    model = pyscipopt.Model()
    model.hideOutput()
    model.readProblem(lp_path)
    model.includeEventhdlr(_Incumbents(), "incumbents", "streams every improving solution")
    model.setParam("limits/time", max(10.0, soft_limit))
    out = {
        "n_vars": model.getNVars(),
        "n_conss": model.getNConss(),
        "lp_mb": round(os.path.getsize(lp_path) / 2**20, 2),
    }
    start = time.time()
    model.optimize()
    out.update({
        "solve_s": round(time.time() - start, 2),
        "status": model.getStatus(),
        "bb_nodes": model.getNNodes(),
        "dual": round(model.getDualbound(), 2),
    })
    # SCIP reports an infinite root bound when presolve solves the problem
    # before any node is processed; there is no root relaxation to measure.
    root = model.getDualboundRoot()
    if abs(root) < 1e19:
        out["root_dual"] = round(root, 2)
    if model.getNSols() > 0:
        out["obj"] = round(model.getObjVal(), 2)
        gap = model.getGap()
        out["gap_pct"] = round(gap * 100, 2) if gap < 1e19 else ""
        tardiness = [
            model.getVal(v) for v in model.getVars() if v.name.lower().startswith("ta_n$")
        ]
        if tardiness:
            on_time = sum(1 for t in tardiness if t <= 1e-6)
            out["sla_pct"] = round(on_time / len(tardiness) * 100, 1)
    return out


def _relax_simple_path(zpl_path):
    """Drop the `<= 1` per-vertex degree limits, in place.

    Only ever applied to the per-process temp workspace copy that
    tests/opp_v5_2_split/config.py or tests/opp_v5_1_mono/config.py makes --
    never to models/. Subtours stay
    excluded: connectivity comes from the Gavish-Graves flow `f_ijb`, not from
    these two constraints, and depot/final keep their own equality constraints.
    What it permits is a route that passes through an intermediate vertex more
    than once.
    """
    import re

    with open(zpl_path, encoding="utf-8") as fh:
        text = fh.read()
    for name in ("one_input_arc_per_node", "one_output_arc_per_node"):
        text, count = re.subn(rf"subto {name}:.*?;\s*", "", text, flags=re.S)
        if count != 1:
            raise RuntimeError(f"expected one {name} in {zpl_path}, found {count}")
    with open(zpl_path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _split_child(point, q):
    from tests.infra.zimpl.dat_files_builder import (
        build_dat_files, write_indexed_dat, write_scalar_dat,
    )
    from tests.opp_v5_2_split.config import DAT_DIR, STAGE1_ZPL_PATH, STAGE2_ZPL_PATH
    from tests.opp_v5_2_split.stage1_decomposition import solve_stage1_decomposed

    if point.get("relax_le1"):
        _relax_simple_path(STAGE1_ZPL_PATH)
    if "stage1_workers" in point:
        # Read by solve_stage1_decomposed at call time; this is the child's own env.
        os.environ["OPP_STAGE1_WORKERS"] = str(point["stage1_workers"])

    start = time.time()
    scenario = _scenario(point)
    build_dat_files(DAT_DIR, scenario)
    row = _describe(point, scenario)
    row["status"] = "in_stage1"
    q.put(("partial", dict(row)))

    t0 = time.time()
    status, values = solve_stage1_decomposed(DAT_DIR)
    row["stage1_s"] = round(time.time() - t0, 2)
    if status not in ("optimal", "feasible"):
        row["status"] = f"stage1:{status}"
        row["total_s"] = round(time.time() - start, 1)
        q.put(("final", row))
        return

    routes = {
        key.split("$")[-1]: val for key, val in values.items()
        if key.lower().startswith("r_b_time$")
    }
    row["route_min"] = round(min(routes.values()), 1)
    row["route_max"] = round(max(routes.values()), 1)
    fixed = scenario["B_setup"] + scenario["B_picking"] * point["orders_per_batch"] * next(
        iter(scenario["C_n"].values())
    )
    depth = -(-point["batches"] // point["pickers"])
    durations = sorted((fixed + r for r in routes.values()), reverse=True)
    row["estimated_finish"] = round(sum(durations[:depth]), 1)

    if point.get("stage1_only"):
        row["status"] = "stage1_ok"
        row["total_s"] = round(time.time() - start, 1)
        q.put(("final", row))
        return

    row["status"] = "in_stage2"
    q.put(("partial", dict(row)))

    write_indexed_dat(os.path.join(DAT_DIR, "route_time_b.dat"), routes)
    write_indexed_dat(os.path.join(DAT_DIR, "velocities.dat"), scenario["V_p"])
    write_scalar_dat(os.path.join(DAT_DIR, "frio.dat"), scenario["T_frio_max"])
    base = os.path.join(DAT_DIR, "exploration_stage2")
    subprocess.run(
        ["zimpl", "-t", "lp", "-l", "8192", "-o", base, STAGE2_ZPL_PATH],
        cwd=DAT_DIR, capture_output=True, text=True, check=True,
    )

    remaining = point["hard_cap_s"] - (time.time() - start) - 30
    result = _solve_lp(f"{base}.lp", remaining, q)
    row["stage2_s"] = result.pop("solve_s")
    row.update(result)
    row["total_s"] = round(time.time() - start, 1)
    q.put(("final", row))


def _mono_child(point, q):
    from tests.infra.zimpl.dat_files_builder import build_dat_files
    from tests.opp_v5_1_mono.config import DAT_DIR, ZPL_PATH

    if point.get("relax_le1"):
        _relax_simple_path(ZPL_PATH)

    start = time.time()
    scenario = _scenario(point)
    build_dat_files(DAT_DIR, scenario)
    row = _describe(point, scenario)
    row["status"] = "compiling"
    q.put(("partial", dict(row)))

    base = os.path.join(DAT_DIR, "exploration_mono")
    t0 = time.time()
    compiled = subprocess.run(
        ["zimpl", "-t", "lp", "-l", "8192", "-o", base, ZPL_PATH],
        cwd=DAT_DIR, capture_output=True, text=True,
    )
    row["zimpl_s"] = round(time.time() - t0, 2)
    if compiled.returncode != 0:
        tail = (compiled.stderr or compiled.stdout).strip().splitlines()[-1:] or ["?"]
        row["status"] = f"zimpl_failed:{tail[0][:60]}"
        row["total_s"] = round(time.time() - start, 1)
        q.put(("final", row))
        return
    row["status"] = "solving"
    q.put(("partial", dict(row)))

    remaining = point["hard_cap_s"] - (time.time() - start) - 30
    result = _solve_lp(f"{base}.lp", remaining, q)
    row["mono_s"] = result.pop("solve_s")
    row.update(result)
    row["total_s"] = round(time.time() - start, 1)
    q.put(("final", row))


def _child(point, q):
    stop = threading.Event()
    threading.Thread(target=_report_memory, args=(q, stop), daemon=True).start()
    try:
        (_mono_child if point.get("model") == "mono" else _split_child)(point, q)
    finally:
        from tests.infra.execution.runner import _peak_rss_mb

        stop.set()
        q.put(("mem", _peak_rss_mb()))


def bounded(point):
    """Measure one point in a child process, killing its whole tree at `hard_cap_s`."""
    q = multiprocessing.Queue()
    proc = multiprocessing.Process(target=_child, args=(point, q))
    start = time.time()
    deadline = start + point["hard_cap_s"]
    proc.start()

    last, final, incumbents, peak = None, False, [], None

    def take(kind, payload):
        nonlocal last, final, peak
        if kind == "incumbent":
            incumbents.append(payload)
        elif kind == "mem":
            if payload is not None:
                peak = max(peak or 0.0, payload)
        else:
            last, final = payload, kind == "final"

    while not final:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        try:
            take(*q.get(timeout=min(remaining, 5.0)))
        except queue_lib.Empty:
            if not proc.is_alive():
                break

    # Catch messages that landed between the last poll and the process exiting.
    while True:
        try:
            take(*q.get(timeout=0.5 if final else 0.1))
        except queue_lib.Empty:
            break

    if final:
        proc.join(30)
        if proc.is_alive():
            _kill_process_tree(proc.pid)
            proc.terminate()
        row = last
    else:
        reason = "hard_kill" if proc.is_alive() else "died"
        if proc.is_alive():
            _kill_process_tree(proc.pid)
            proc.terminate()
        proc.join(10)
        row = dict(last) if last else _point_row(point)
        row["status"] = f"{reason}:{row.get('status', 'start')}"
        row["total_s"] = round(time.time() - start, 1)

    row["peak_rss_mb"] = round(peak, 1) if peak else ""
    if incumbents:
        row["first_sol_s"], row["first_sol_obj"] = incumbents[0][0], round(incumbents[0][1], 2)
        row["n_incumbents"] = len(incumbents)
        row["incumbents"] = ";".join(f"{t}:{obj:.2f}" for t, obj in incumbents)
    row["_incumbents"] = incumbents
    return row


def _compare_to_reference(row, ref):
    """Measure a run against the true optimum `ref` (the split's, in a pair)."""
    if not ref:
        return
    row["ref_obj"] = ref
    incumbents = row.get("_incumbents") or []
    if incumbents:
        row["first_gap_to_opt_pct"] = round((incumbents[0][1] - ref) / ref * 100, 2) + 0.0
        row["best_gap_to_opt_pct"] = round((incumbents[-1][1] - ref) / ref * 100, 2) + 0.0
        within = [t for t, obj in incumbents if obj <= ref * 1.01]
        row["time_to_1pct_s"] = within[0] if within else ""
        exact = [t for t, obj in incumbents if obj <= ref * (1 + 1e-6) + 1e-6]
        row["time_to_opt_s"] = exact[0] if exact else ""
    for key, target in (("dual", "dual_ratio_pct"), ("root_dual", "root_dual_ratio_pct")):
        if row.get(key) not in (None, ""):
            row[target] = round(float(row[key]) / ref * 100, 1)


def run_pair(point):
    """The same instance through the split and then the monolithic model."""
    split_row = bounded({**point, "model": "split"})
    mono_row = bounded({**point, "model": "mono"})
    ref = split_row.get("obj") if split_row.get("status") == "optimal" else None
    _compare_to_reference(mono_row, ref)
    return [split_row, mono_row]


def measure(point):
    return run_pair(point) if point.get("model") == "pair" else [bounded(point)]


def report(row):
    print(
        f"  {row.get('label') or '':<8}{row.get('model', ''):<6}"
        f"{row['batches']:>2}B/{row['pickers']}P {row['orders_per_batch']:>3}o/B {row['grid']:>7} "
        f"w{row.get('weights', '')} t{row.get('speed_tiers', '')} | "
        f"s1 {row.get('stage1_s', '-')} s2 {row.get('stage2_s', '-')} mono {row.get('mono_s', '-')} "
        f"tot {row.get('total_s', '-')} | {row['status']} "
        f"nodes={row.get('bb_nodes', '-')} gap={row.get('gap_pct', '-')} "
        f"to_opt={row.get('time_to_opt_s', '-')} dual%={row.get('dual_ratio_pct', '-')}"
    )
    sys.stdout.flush()


def _open_csv(out_path):
    handle = open(out_path, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    handle.flush()
    return handle, writer


def run_points(points, out_path, parallel):
    """Measure an explicit list of configurations, `parallel` at a time."""
    handle, writer = _open_csv(out_path)
    lock = threading.Lock()

    def work(point):
        rows = measure(point)
        with lock:
            for row in rows:
                writer.writerow(row)
                report(row)
            handle.flush()

    try:
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            list(pool.map(work, points))
    finally:
        handle.close()


def run_sweep(args, out_path):
    """Walk one axis at a time, each starting where the previous one settled."""
    batches, pickers, orders_per_batch, side = (int(x) for x in args.base.split(","))
    weights = [int(x) for x in args.weights.split(",")]
    handle, writer = _open_csv(out_path)
    try:
        for axis in args.axes:
            for value in AXES[axis]:
                config = {
                    "orders": (batches, pickers, value, side),
                    "batches": (value, pickers, orders_per_batch, side),
                    "pickers": (batches, value, orders_per_batch, side),
                    "warehouse": (batches, pickers, orders_per_batch, value),
                }[axis]
                point = {
                    "label": axis, "model": "split",
                    "batches": config[0], "pickers": config[1],
                    "orders_per_batch": config[2], "side": config[3],
                    "weights": weights, "speed_spread": args.speed_spread,
                    "speed_tiers": args.speed_tiers,
                    "hard_cap_s": args.hard_cap,
                }
                row = bounded(point)
                writer.writerow(row)
                handle.flush()
                report(row)
                if row["status"] != "optimal":
                    break
                # Keep the largest value that still solved for the next axis.
                if axis == "orders":
                    orders_per_batch = value
                elif axis == "batches":
                    batches = value
                elif axis == "pickers":
                    pickers = value
                else:
                    side = value
    finally:
        handle.close()


def run_frontier(args, out_path):
    """Pair points over batches x side, skipping sides at or past the first failure."""
    weights = [int(x) for x in args.weights.split(",")]
    failed_at = None
    handle, writer = _open_csv(out_path)
    try:
        for batches in (int(x) for x in args.frontier_batches.split(",")):
            pickers = max(1, -(-batches // args.batches_per_picker))
            for side in (int(x) for x in args.frontier_sides.split(",")):
                point = {
                    "label": f"B{batches}S{side}", "model": "pair",
                    "batches": batches, "pickers": pickers,
                    "orders_per_batch": args.orders_per_batch, "side": side,
                    "weights": weights, "speed_spread": args.speed_spread,
                    "speed_tiers": args.speed_tiers, "hard_cap_s": args.hard_cap,
                }
                if failed_at is not None and side >= failed_at:
                    row = {**_point_row({**point, "model": "mono"}), "status": "skipped"}
                    writer.writerow(row)
                    handle.flush()
                    report(row)
                    continue
                split_row, mono_row = run_pair(point)
                for row in (split_row, mono_row):
                    writer.writerow(row)
                    report(row)
                handle.flush()
                # Only a monolithic failure on an instance the split did solve
                # moves the frontier. An instance both find infeasible (a batch
                # covering nearly all of a small grid, which the `<= 1` limit
                # can make impossible) says nothing about solver reach.
                if split_row.get("status") == "optimal" and mono_row.get("status") != "optimal":
                    failed_at = side if failed_at is None else min(failed_at, side)
    finally:
        handle.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--study", required=True,
                        help="study directory under experiments/opp_v5/studies/, "
                             "e.g. 08_w_full_weight (created if missing)")
    parser.add_argument("--points", default=None,
                        help="JSON file of explicit configurations to calibrate "
                             "(skips the axis sweep)")
    parser.add_argument("--parallel", type=int, default=1,
                        help="points measured at once in --points mode (default 1). "
                             "Each is single-threaded; wall times gain a few percent "
                             "of contention, node counts do not change.")
    parser.add_argument("--frontier", action="store_true",
                        help="walk batches x side with pair points (see module docstring)")
    parser.add_argument("--frontier-batches", default="1,2,3,4,6")
    parser.add_argument("--frontier-sides", default="3,4,5,6,7")
    parser.add_argument("--batches-per-picker", type=int, default=2,
                        help="frontier crew: pickers = ceil(batches / this) (default 2)")
    parser.add_argument("--orders-per-batch", type=int, default=26,
                        help="frontier orders per batch (default 26, the realistic profile)")
    parser.add_argument("--hard-cap", type=int, default=600,
                        help="wall-clock seconds per point, stages included, after "
                             "which the process tree is killed (default 600)")
    parser.add_argument("--axes", nargs="+", default=list(AXES), choices=list(AXES),
                        help="which axes to sweep, in order")
    parser.add_argument("--base", default="6,2,26,7",
                        help="sweep starting point as batches,pickers,orders_per_batch,side")
    parser.add_argument("--weights", default="4,4",
                        help="grid edge costs as vertical,horizontal (default 4,4)")
    parser.add_argument("--speed-spread", type=float, default=0.0,
                        help="picker speed spread (default 0.0 = all 1.0); "
                             "0.2 spans [0.8, 1.2]")
    parser.add_argument("--speed-tiers", type=int, default=None,
                        help="distinct speed bands (default: one per picker). A real "
                             "crew has two or three; pickers inside a band stay "
                             "interchangeable.")
    parser.add_argument("--out", default=None,
                        help="CSV name inside the study directory (default: timestamped)")
    args = parser.parse_args()

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studies", args.study)
    os.makedirs(out_dir, exist_ok=True)
    prefix = "points" if args.points else "frontier" if args.frontier else "sweep"
    name = args.out or f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    out_path = os.path.join(out_dir, name)
    print(f"output: {out_path}\n")

    if args.points:
        with open(args.points, encoding="utf-8") as fh:
            points = json.load(fh)
        for point in points:
            point.setdefault("hard_cap_s", args.hard_cap)
        run_points(points, out_path, args.parallel)
    elif args.frontier:
        run_frontier(args, out_path)
    else:
        run_sweep(args, out_path)

    print(f"\ndone: {out_path}")


if __name__ == "__main__":
    main()
