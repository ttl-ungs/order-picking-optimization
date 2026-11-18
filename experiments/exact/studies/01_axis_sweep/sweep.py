"""Walk one axis at a time from stress 09's shape until each one hurts.

Exploration, not tests: it finds the edges so that only three or four landmark
scenarios have to become test files. Order of axes follows the warehouse's own
logic -- how much a picker carries, then how many batches, then how many
pickers, then how big the warehouse is.

Every row is flushed to CSV as it is measured, so a kill loses nothing but the
point in flight. It also records the real per-batch route times, which is what
the due dates need to be placed against: stress 09 put them on an ESTIMATE and
came out at 96.67% on time, nearly as degenerate as the 0% it replaced.

Kept as it was run on 2026-09-22 (translated to English on 2026-09-24, same
logic; column names match sweep_axes_20260922.csv). "Stress 09" is the old
numbering. It ran with the Stage 1 metric closure on, which has since been
removed: rerunning it solves on the full graph, with the same objectives and
different Stage 1 times.
"""
import csv
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

import pyscipopt

from tests.shared_scenarios.stress.stress_scenarios_designed import designed_stress_scenario
from tests.infra.zimpl.dat_files_builder import (
    build_dat_files, write_indexed_dat, write_scalar_dat,
)
from tests.opp_split.config import DAT_DIR, STAGE2_ZPL_PATH
from tests.opp_split.stage1_decomposition import solve_stage1_decomposed

CAP = 300  # 5 minutes per solve
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sweep_axes.csv")
FIELDS = [
    "phase", "batches", "pickers", "orders_per_batch", "grid", "vertices",
    "batch_locations_min", "batch_locations_max", "stage1_s", "stage2_s", "status",
    "obj", "bb_nodes", "sla_pct", "route_min", "route_max", "estimated_finish",
]


def measure(batches, pickers, orders_per_batch, side, phase):
    orders = batches * orders_per_batch
    scenario = designed_stress_scenario(batches, pickers, orders, side, side)
    build_dat_files(DAT_DIR, scenario)

    t0 = time.time()
    status, values = solve_stage1_decomposed(DAT_DIR)
    stage1 = time.time() - t0

    row = {
        "phase": phase, "batches": batches, "pickers": pickers,
        "orders_per_batch": orders_per_batch, "grid": f"{side}x{side}",
        "vertices": len(scenario["V"]), "stage1_s": round(stage1, 2),
    }
    per_batch = [
        len({v for v in scenario["V"]
             if any(scenario["A_ni"][(n, v)] * scenario["B_nb"][(n, b)] for n in scenario["N"])})
        for b in sorted(scenario["B"])
    ]
    row["batch_locations_min"], row["batch_locations_max"] = min(per_batch), max(per_batch)

    if status not in ("optimal", "feasible"):
        row["status"] = f"stage1:{status}"
        return row, scenario, None

    routes = {
        k.split("$")[-1]: v for k, v in values.items()
        if k.lower().startswith("r_b$")
    }
    row["route_min"], row["route_max"] = round(min(routes.values()), 1), round(max(routes.values()), 1)
    fixed = scenario["T_setup"] + scenario["T_pick"] * orders_per_batch * scenario["C_n"][
        next(iter(scenario["N"]))
    ]
    depth = -(-batches // pickers)
    durations = sorted((fixed + r for r in routes.values()), reverse=True)
    row["estimated_finish"] = round(sum(durations[:depth]), 1)

    if stage1 > CAP:
        row["status"] = "stage1_slow"
        return row, scenario, routes

    write_indexed_dat(os.path.join(DAT_DIR, "route_time_b.dat"), routes)
    write_indexed_dat(os.path.join(DAT_DIR, "velocities.dat"), scenario["V_p"])
    write_scalar_dat(os.path.join(DAT_DIR, "cold.dat"), scenario["T_cold"])

    base = os.path.join(DAT_DIR, "sweep_stage2")
    subprocess.run(
        ["zimpl", "-t", "lp", "-l", "8192", "-o", base, STAGE2_ZPL_PATH],
        cwd=DAT_DIR, capture_output=True, text=True, check=True,
    )
    model = pyscipopt.Model()
    model.hideOutput()
    model.readProblem(f"{base}.lp")
    model.setParam("limits/time", CAP)
    t0 = time.time()
    model.optimize()
    row["stage2_s"] = round(time.time() - t0, 2)
    row["status"] = model.getStatus()
    row["bb_nodes"] = model.getNNodes()
    if model.getStatus() in ("optimal", "feasible"):
        row["obj"] = round(model.getObjVal(), 2)
        finished = [model.getVal(v) for v in model.getVars() if v.name.lower().startswith("ta_n$")]
        if finished:
            row["sla_pct"] = round(sum(1 for t in finished if t <= 1e-6) / len(finished) * 100, 1)
    return row, scenario, routes


def run():
    fresh = not os.path.exists(OUT)
    with open(OUT, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if fresh:
            writer.writeheader()
            handle.flush()

        def record(row):
            writer.writerow(row)
            handle.flush()
            print(f"  {row['phase']:<12} {row['batches']:>2}B/{row['pickers']}P "
                  f"{row['orders_per_batch']:>3}o/B {row['grid']:>7} | "
                  f"s1 {row.get('stage1_s','-'):>7} s2 {row.get('stage2_s','-'):>7} | "
                  f"{row['status']:<12} sla={row.get('sla_pct','-')}")
            sys.stdout.flush()

        # Phase 1 -- how much each batch carries. 7x7 has only 47 pickable
        # locations, so past ~25 orders per batch the distinct locations stop
        # growing and only the picking time rises.
        best_orders = 10
        for orders_per_batch in (10, 14, 18, 22, 26):
            row, _s, _r = measure(6, 2, orders_per_batch, 7, "1-orders")
            record(row)
            if row["status"] != "optimal":
                break
            best_orders = orders_per_batch

        # Phase 2 -- how many batches, with the load per batch fixed.
        best_batches = 6
        for batches in (8, 10, 12, 14):
            row, _s, _r = measure(batches, 2, best_orders, 7, "2-batches")
            record(row)
            if row["status"] != "optimal":
                break
            best_batches = batches

        # Phase 3 -- how many pickers, with batches and load fixed.
        for pickers in (3, 4, 5):
            row, _s, _r = measure(best_batches, pickers, best_orders, 7, "3-pickers")
            record(row)
            if row["status"] != "optimal":
                break

        # Phase 4 -- warehouse size. With the metric closure this was expected
        # to come almost free: it reduces each batch to a TSP over its locations.
        for side in (10, 15, 20):
            row, _s, _r = measure(best_batches, 2, best_orders, side, "4-warehouse")
            record(row)
            if row["status"] != "optimal":
                break

    print(f"\nresults in {OUT}")


if __name__ == "__main__":
    run()
