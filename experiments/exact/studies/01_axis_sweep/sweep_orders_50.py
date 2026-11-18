"""Push the orders-per-batch axis past where the main sweep stopped.

Phase 1 of sweep.py ran out of values at 26 rather than hitting a wall, so the
edge of that axis is still unknown. Stage 1 was still climbing there (3.7s at
10 orders, 12.9s at 26) while Stage 2 had flattened around 7-8s.

Expect the routing complexity to saturate: a 7x7 grid has 47 pickable
locations, so past roughly 30 orders per batch the distinct locations a batch
must reach stop growing and only the picking term rises. The
`batch_locations_*` columns show whether that saturation has set in, and they
are the reason a slow point here does not necessarily mean the same thing as a
slow point below 26.

Writes its own CSV so it cannot collide with the main sweep running alongside.

Kept as it was run on 2026-09-22 (translated to English on 2026-09-24, same
logic; column names match sweep_orders_extended_20260922.csv). It ran with the
Stage 1 metric closure on, which has since been removed: rerunning it solves on
the full graph, with the same objectives and different Stage 1 times.
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
from tests.opp_split.config import STAGE2_ZPL_PATH
from tests.opp_split.stage1_decomposition import solve_stage1_decomposed

# tests/opp_split/config.py gives every process its own tempfile.mkdtemp
# workspace, so this script and the main sweep never write the same .dat.
from tests.opp_split.config import DAT_DIR

CAP = 300
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sweep_orders_extended.csv")
FIELDS = [
    "orders_per_batch", "orders", "batch_locations_min", "batch_locations_max",
    "stage1_s", "stage2_s", "status", "obj", "bb_nodes", "sla_pct",
    "route_min", "route_max",
]

with open(OUT, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=FIELDS)
    writer.writeheader()
    handle.flush()

    for orders_per_batch in (32, 40, 50):
        orders = 6 * orders_per_batch
        scenario = designed_stress_scenario(6, 2, orders, 7, 7)
        build_dat_files(DAT_DIR, scenario)

        row = {"orders_per_batch": orders_per_batch, "orders": orders}
        per_batch = [
            len({v for v in scenario["V"]
                 if any(scenario["A_ni"][(n, v)] * scenario["B_nb"][(n, b)] for n in scenario["N"])})
            for b in sorted(scenario["B"])
        ]
        row["batch_locations_min"], row["batch_locations_max"] = min(per_batch), max(per_batch)

        t0 = time.time()
        status, values = solve_stage1_decomposed(DAT_DIR)
        row["stage1_s"] = round(time.time() - t0, 2)

        if status not in ("optimal", "feasible"):
            row["status"] = f"stage1:{status}"
            writer.writerow(row)
            handle.flush()
            print(f"  {orders_per_batch:>3} o/B | stage 1 {row['stage1_s']:>8}s | {row['status']}")
            break

        routes = {
            k.split("$")[-1]: v for k, v in values.items()
            if k.lower().startswith("r_b$")
        }
        row["route_min"] = round(min(routes.values()), 1)
        row["route_max"] = round(max(routes.values()), 1)

        write_indexed_dat(os.path.join(DAT_DIR, "route_time_b.dat"), routes)
        write_indexed_dat(os.path.join(DAT_DIR, "velocities.dat"), scenario["V_p"])
        write_scalar_dat(os.path.join(DAT_DIR, "cold.dat"), scenario["T_cold"])

        base = os.path.join(DAT_DIR, "orders50_stage2")
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
            tardiness = [model.getVal(v) for v in model.getVars() if v.name.lower().startswith("ta_n$")]
            if tardiness:
                row["sla_pct"] = round(sum(1 for t in tardiness if t <= 1e-6) / len(tardiness) * 100, 1)

        writer.writerow(row)
        handle.flush()
        print(f"  {orders_per_batch:>3} o/B ({orders:>3} orders) | locations/batch "
              f"{row['batch_locations_min']}-{row['batch_locations_max']:<3}"
              f"| s1 {row['stage1_s']:>8}s s2 {row['stage2_s']:>8}s | {row['status']:<12} sla={row.get('sla_pct','-')}")
        sys.stdout.flush()

print(f"\nresults in {OUT}")
