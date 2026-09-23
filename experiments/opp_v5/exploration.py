"""Map where each instance dimension stops being solvable, and calibrate candidate scenarios.

    python -m experiments.opp_v5.exploration --estudio 08_x                        # sweep every axis
    python -m experiments.opp_v5.exploration --estudio 08_x --axes ordenes lotes   # only those two
    python -m experiments.opp_v5.exploration --estudio 08_x --base 6,2,26,7        # lotes,pickers,ord_lote,lado
    python -m experiments.opp_v5.exploration --estudio 08_x --pesos 4,5 --velocidades 0.2 --niveles 2
    python -m experiments.opp_v5.exploration --estudio 08_x --puntos experiments/opp_v5/estudios/08_x/puntos.json --paralelo 3

Why this exists rather than more stress tests: a test answers "does this one
instance solve", while a sweep gives the curve -- where an axis bends, where it
breaks, and how the search tree behaves on the way. The 2026-09-22/23 runs are
what showed that batches is the tightest axis for Stage 2, that warehouse size
is what breaks Stage 1, and that realistic (tiered) picker speeds shrink the
solvable region far below what uniform speeds suggest.

Every configuration is solved in its OWN process and killed from outside when
its wall-clock budget (`tope_duro`) runs out. That is not optional: SCIP's
`limits/time` is only checked between operations, and a single huge LP ran a
300s limit out to 3079s on 2026-09-23; Stage 1 has no limit at all. The kill
covers the whole process tree, so a zimpl compile or SCIP solve in flight goes
with it. The row still gets written, with the stage the point died in.

Each row is flushed as it is measured, so an interrupted run keeps everything
up to the points in flight. Results go to experiments/opp_v5/estudios/<estudio>/,
next to the points file that produced them (see experiments/opp_v5/README.md),
and deliberately NOT to results/<model>/<tier>/, because analysis/load.py globs
that pattern and would pick these files up as if they were test runs.

Columns worth reading together:
    nodos_bb   branch-and-bound nodes -- structural; unlike wall time it does
               not move with machine load. The same instance always gives the
               same count (SCIP is deterministic), so it is the fair way to
               compare across runs made under different load.
    sla_pct    share of orders on time. Near 0% or near 100% means the
               objective is flat and the solver churns.
    ubic_lote  distinct locations a batch must reach -- what Stage 1 pays for,
               together with the grid size itself.

Points file (--puntos) is a JSON list of objects:
    {"etiqueta": "A1", "modelo": "split", "lotes": 6, "pickers": 3,
     "ord_lote": 26, "lado": 12, "pesos": [4, 5], "vel_spread": 0.2,
     "vel_niveles": 2, "tope_duro": 1500}
`modelo` is "split" (default) or "mono". Missing `tope_duro` takes --tope-duro.
`"solo_etapa1": true` stops after Stage 1 -- for questions that are purely
about routing. (A `"clausura"` key in older points files is ignored: the
Stage 1 metric closure was removed on 2026-09-23.)
`"relajar_le1": true` (split only) removes Stage 1's `<= 1` per-vertex limits
from that process's temp copy of the model -- a trial, never applied to models/.
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
    "etiqueta", "modelo", "variante", "lotes", "pickers", "ord_lote", "grilla", "nodos",
    "pesos", "vel_spread", "vel_niveles", "velocidades",
    "ubic_lote_min", "ubic_lote_max",
    "etapa1_s", "etapa2_s", "zimpl_s", "mono_s", "total_s", "tope_duro",
    "status", "obj", "gap_pct", "nodos_bb", "sla_pct",
    "ruta_min", "ruta_max", "fin_estimado",
]

# Ranges walk outward from the base. Geometric-ish steps cover ground without
# spending the budget repeatedly near the edge, which is where points are slowest.
AXES = {
    "ordenes": (10, 14, 18, 22, 26, 32, 40, 50),
    "lotes": (6, 8, 10, 12, 14),
    "pickers": (2, 3, 4, 5, 6),
    "deposito": (7, 10, 15, 20),
}


def _point_row(point):
    """The columns that come straight from the configuration, before any solve."""
    weights = point.get("pesos", [4, 4])
    return {
        "etiqueta": point.get("etiqueta", ""),
        "modelo": point.get("modelo", "split"),
        "lotes": point["lotes"],
        "pickers": point["pickers"],
        "ord_lote": point["ord_lote"],
        "grilla": f"{point['lado']}x{point['lado']}",
        "pesos": f"{weights[0]}/{weights[1]}",
        "vel_spread": point.get("vel_spread", 0.0),
        "vel_niveles": point.get("vel_niveles") or ("todas" if point.get("vel_spread") else "-"),
        "tope_duro": point["tope_duro"],
        "variante": ("sin_le1 " if point.get("relajar_le1") else "") + "grafo",
    }


def _scenario(point):
    from tests.shared_scenarios.stress.stress_scenarios_v5_designed import designed_stress_scenario

    weights = point.get("pesos", [4, 4])
    return designed_stress_scenario(
        point["lotes"], point["pickers"], point["lotes"] * point["ord_lote"],
        point["lado"], point["lado"],
        speed_spread=point.get("vel_spread", 0.0),
        speed_tiers=point.get("vel_niveles"),
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
    row["nodos"] = len(scenario["V"])
    row["ubic_lote_min"], row["ubic_lote_max"] = min(per_batch), max(per_batch)
    row["velocidades"] = "|".join(f"{s:.2f}" for s in sorted(set(scenario["V_p"].values())))
    return row


def _solve_lp(lp_path, soft_limit):
    """Solve a compiled .lp with SCIP. `soft_limit` lets SCIP stop cleanly on its
    own in the common case; the hard kill in `bounded` is the backstop."""
    import pyscipopt

    model = pyscipopt.Model()
    model.hideOutput()
    model.readProblem(lp_path)
    model.setParam("limits/time", max(10.0, soft_limit))
    start = time.time()
    model.optimize()
    out = {
        "solve_s": round(time.time() - start, 2),
        "status": model.getStatus(),
        "nodos_bb": model.getNNodes(),
    }
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
    """Drop Stage 1's `<= 1` per-vertex degree limits, in place.

    Only ever applied to the per-process temp workspace copy that
    tests/opp_v5_2_split/config.py makes -- never to models/. Subtours stay
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

    if point.get("relajar_le1"):
        _relax_simple_path(STAGE1_ZPL_PATH)

    start = time.time()
    scenario = _scenario(point)
    build_dat_files(DAT_DIR, scenario)
    row = _describe(point, scenario)
    row["status"] = "en_etapa1"
    q.put(("parcial", dict(row)))

    t0 = time.time()
    status, values = solve_stage1_decomposed(DAT_DIR)
    row["etapa1_s"] = round(time.time() - t0, 2)
    if status not in ("optimal", "feasible"):
        row["status"] = f"etapa1:{status}"
        row["total_s"] = round(time.time() - start, 1)
        q.put(("final", row))
        return

    routes = {
        key.split("$")[-1]: val for key, val in values.items()
        if key.lower().startswith("r_b_time$")
    }
    row["ruta_min"] = round(min(routes.values()), 1)
    row["ruta_max"] = round(max(routes.values()), 1)
    fixed = scenario["B_setup"] + scenario["B_picking"] * point["ord_lote"] * next(
        iter(scenario["C_n"].values())
    )
    depth = -(-point["lotes"] // point["pickers"])
    durations = sorted((fixed + r for r in routes.values()), reverse=True)
    row["fin_estimado"] = round(sum(durations[:depth]), 1)

    if point.get("solo_etapa1"):
        row["status"] = "etapa1_ok"
        row["total_s"] = round(time.time() - start, 1)
        q.put(("final", row))
        return

    row["status"] = "en_etapa2"
    q.put(("parcial", dict(row)))

    write_indexed_dat(os.path.join(DAT_DIR, "route_time_b.dat"), routes)
    write_indexed_dat(os.path.join(DAT_DIR, "velocities.dat"), scenario["V_p"])
    write_scalar_dat(os.path.join(DAT_DIR, "frio.dat"), scenario["T_frio_max"])
    base = os.path.join(DAT_DIR, "exploration_stage2")
    subprocess.run(
        ["zimpl", "-t", "lp", "-l", "8192", "-o", base, STAGE2_ZPL_PATH],
        cwd=DAT_DIR, capture_output=True, text=True, check=True,
    )

    remaining = point["tope_duro"] - (time.time() - start) - 30
    result = _solve_lp(f"{base}.lp", remaining)
    row["etapa2_s"] = result.pop("solve_s")
    row.update(result)
    row["total_s"] = round(time.time() - start, 1)
    q.put(("final", row))


def _mono_child(point, q):
    from tests.infra.zimpl.dat_files_builder import build_dat_files
    from tests.opp_v5_1_mono.config import DAT_DIR, ZPL_PATH

    start = time.time()
    scenario = _scenario(point)
    build_dat_files(DAT_DIR, scenario)
    row = _describe(point, scenario)
    row["status"] = "compilando"
    q.put(("parcial", dict(row)))

    base = os.path.join(DAT_DIR, "exploration_mono")
    t0 = time.time()
    compiled = subprocess.run(
        ["zimpl", "-t", "lp", "-l", "8192", "-o", base, ZPL_PATH],
        cwd=DAT_DIR, capture_output=True, text=True,
    )
    row["zimpl_s"] = round(time.time() - t0, 2)
    if compiled.returncode != 0:
        tail = (compiled.stderr or compiled.stdout).strip().splitlines()[-1:] or ["?"]
        row["status"] = f"zimpl_fallo:{tail[0][:60]}"
        row["total_s"] = round(time.time() - start, 1)
        q.put(("final", row))
        return
    row["status"] = "resolviendo"
    q.put(("parcial", dict(row)))

    remaining = point["tope_duro"] - (time.time() - start) - 30
    result = _solve_lp(f"{base}.lp", remaining)
    row["mono_s"] = result.pop("solve_s")
    row.update(result)
    row["total_s"] = round(time.time() - start, 1)
    q.put(("final", row))


def bounded(point):
    """Measure one point in a child process, killing its whole tree at `tope_duro`."""
    target = _mono_child if point.get("modelo") == "mono" else _split_child
    q = multiprocessing.Queue()
    proc = multiprocessing.Process(target=target, args=(point, q))
    start = time.time()
    deadline = start + point["tope_duro"]
    proc.start()

    last, final = None, False
    while not final:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        try:
            kind, row = q.get(timeout=min(remaining, 5.0))
        except queue_lib.Empty:
            if not proc.is_alive():
                break
            continue
        last, final = row, kind == "final"

    # Catch a message that landed between the last poll and the process exiting.
    while not final:
        try:
            kind, row = q.get_nowait()
        except queue_lib.Empty:
            break
        last, final = row, kind == "final"

    if final:
        proc.join(30)
        if proc.is_alive():
            _kill_process_tree(proc.pid)
            proc.terminate()
        return last

    reason = "kill_duro" if proc.is_alive() else "murio"
    if proc.is_alive():
        _kill_process_tree(proc.pid)
        proc.terminate()
    proc.join(10)
    row = dict(last) if last else _point_row(point)
    row["status"] = f"{reason}:{row.get('status', 'inicio')}"
    row["total_s"] = round(time.time() - start, 1)
    return row


def report(row):
    print(
        f"  {row.get('etiqueta') or '':<6}{row.get('modelo', ''):<6}"
        f"{row['lotes']:>2}L/{row['pickers']}P {row['ord_lote']:>3}o/L {row['grilla']:>7} "
        f"p{row.get('pesos', '')} v{row.get('vel_niveles', '')} | "
        f"e1 {row.get('etapa1_s', '-')} e2 {row.get('etapa2_s', '-')} mono {row.get('mono_s', '-')} "
        f"tot {row.get('total_s', '-')} | {row['status']} "
        f"nodos={row.get('nodos_bb', '-')} gap={row.get('gap_pct', '-')} sla={row.get('sla_pct', '-')}"
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
        row = bounded(point)
        with lock:
            writer.writerow(row)
            handle.flush()
            report(row)

    try:
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            list(pool.map(work, points))
    finally:
        handle.close()


def run_sweep(args, out_path):
    """Walk one axis at a time, each starting where the previous one settled."""
    batches, pickers, orders_per_batch, side = (int(x) for x in args.base.split(","))
    weights = [int(x) for x in args.pesos.split(",")]
    handle, writer = _open_csv(out_path)
    try:
        for axis in args.axes:
            for value in AXES[axis]:
                config = {
                    "ordenes": (batches, pickers, value, side),
                    "lotes": (value, pickers, orders_per_batch, side),
                    "pickers": (batches, value, orders_per_batch, side),
                    "deposito": (batches, pickers, orders_per_batch, value),
                }[axis]
                point = {
                    "etiqueta": axis, "modelo": "split",
                    "lotes": config[0], "pickers": config[1],
                    "ord_lote": config[2], "lado": config[3],
                    "pesos": weights, "vel_spread": args.velocidades,
                    "vel_niveles": args.niveles,
                    "tope_duro": args.tope_duro,
                }
                row = bounded(point)
                writer.writerow(row)
                handle.flush()
                report(row)
                if row["status"] != "optimal":
                    break
                # Keep the largest value that still solved for the next axis.
                if axis == "ordenes":
                    orders_per_batch = value
                elif axis == "lotes":
                    batches = value
                elif axis == "pickers":
                    pickers = value
                else:
                    side = value
    finally:
        handle.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--puntos", default=None,
                        help="JSON file of explicit configurations to calibrate "
                             "(skips the axis sweep)")
    parser.add_argument("--paralelo", type=int, default=1,
                        help="points measured at once in --puntos mode (default 1). "
                             "Each is single-threaded; wall times gain a few percent "
                             "of contention, node counts do not change.")
    parser.add_argument("--tope-duro", type=int, default=600,
                        help="wall-clock seconds per point, stages included, after "
                             "which the process tree is killed (default 600)")
    parser.add_argument("--axes", nargs="+", default=list(AXES), choices=list(AXES),
                        help="which axes to sweep, in order")
    parser.add_argument("--base", default="6,2,26,7",
                        help="sweep starting point as lotes,pickers,ord_lote,lado")
    parser.add_argument("--pesos", default="4,4",
                        help="grid edge costs as vertical,horizontal (default 4,4)")
    parser.add_argument("--velocidades", type=float, default=0.0,
                        help="picker speed spread (default 0.0 = all 1.0); "
                             "0.2 spans [0.8, 1.2]")
    parser.add_argument("--niveles", type=int, default=None,
                        help="distinct speed bands (default: one per picker). A real "
                             "crew has two or three; pickers inside a band stay "
                             "interchangeable.")
    parser.add_argument("--estudio", required=True,
                        help="study directory under experiments/opp_v5/estudios/, "
                             "e.g. 08_pesos_W_full (created if missing)")
    parser.add_argument("--out", default=None,
                        help="CSV name inside the study directory (default: timestamped)")
    args = parser.parse_args()

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estudios", args.estudio)
    os.makedirs(out_dir, exist_ok=True)
    prefix = "calibracion" if args.puntos else "exploration"
    name = args.out or f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    out_path = os.path.join(out_dir, name)
    print(f"salida: {out_path}\n")

    if args.puntos:
        with open(args.puntos, encoding="utf-8") as fh:
            points = json.load(fh)
        for point in points:
            point.setdefault("tope_duro", args.tope_duro)
        run_points(points, out_path, args.paralelo)
    else:
        run_sweep(args, out_path)

    print(f"\nlisto: {out_path}")


if __name__ == "__main__":
    main()
