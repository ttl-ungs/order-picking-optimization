"""How much of the cost of heterogeneous speeds is an artifact of making them ALL distinct?

An earlier sweep fanned V_p continuously across the crew, one value per picker,
and Stage 2 blew up at 3+ pickers. Real crews do not look like that: people are
hired from a similar pool and push the same carts, so speeds fall into two or
three bands. Pickers inside a band stay interchangeable, so only part of the
assignment symmetry is broken.

Holds the instance fixed and varies only how many distinct speeds exist, at the
picker counts where the all-distinct case was measured to hurt.

Kept as it was run on 2026-09-23 (translated to English on 2026-09-24, same
logic; column names and labels match speed_tiers_20260923_003241.csv). It ran
with the Stage 1 metric closure on, which has since been removed; Stage 2,
which is what this measures, does not depend on it.
"""
import csv
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

import pyscipopt

from tests.shared_scenarios.stress.stress_scenarios_v5_designed import designed_stress_scenario
from tests.infra.zimpl.dat_files_builder import (
    build_dat_files, write_indexed_dat, write_scalar_dat,
)
from tests.opp_v5_2_split.config import DAT_DIR, STAGE2_ZPL_PATH
from tests.opp_v5_2_split.stage1_decomposition import solve_stage1_decomposed

CAP = 300
BATCHES, ORDERS_PER_BATCH, SIDE = 6, 26, 7
OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    f"speed_tiers_{time.strftime('%Y%m%d_%H%M%S')}.csv",
)
FIELDS = ["pickers", "tiers", "distinct_speeds", "speeds",
          "stage1_s", "stage2_s", "status", "obj", "bb_nodes", "sla_pct"]

CASES = []
for pickers in (3, 4, 6):
    CASES.append((pickers, 0.0, None, "uniform"))
    for tiers in (2, 3):
        if tiers <= pickers:
            CASES.append((pickers, 0.3, tiers, f"{tiers} tiers"))
    CASES.append((pickers, 0.3, None, "all distinct"))

with open(OUT, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=FIELDS)
    writer.writeheader()
    handle.flush()
    print(f"{BATCHES} batches, {ORDERS_PER_BATCH} orders/batch, grid {SIDE}x{SIDE}, cap {CAP}s\n")
    print(f"{'pickers':>8}{'config':>18}{'spd':>5}{'stage1':>9}{'stage2':>9}{'nodes':>10}{'sla':>7}  status")
    print("-" * 78)

    for pickers, spread, tiers, label in CASES:
        scenario = designed_stress_scenario(
            BATCHES, pickers, BATCHES * ORDERS_PER_BATCH, SIDE, SIDE,
            speed_spread=spread, speed_tiers=tiers,
        )
        build_dat_files(DAT_DIR, scenario)

        distinct = sorted(set(scenario["V_p"].values()))
        row = {
            "pickers": pickers, "tiers": label, "distinct_speeds": len(distinct),
            "speeds": "|".join(f"{v:.2f}" for v in distinct),
        }

        start = time.time()
        status, values = solve_stage1_decomposed(DAT_DIR)
        row["stage1_s"] = round(time.time() - start, 2)
        if status not in ("optimal", "feasible"):
            row["status"] = f"stage1:{status}"
            writer.writerow(row)
            handle.flush()
            continue

        routes = {
            k.split("$")[-1]: v for k, v in values.items()
            if k.lower().startswith("r_b$")
        }
        write_indexed_dat(os.path.join(DAT_DIR, "route_time_b.dat"), routes)
        write_indexed_dat(os.path.join(DAT_DIR, "velocities.dat"), scenario["V_p"])
        write_scalar_dat(os.path.join(DAT_DIR, "cold.dat"), scenario["T_cold"])

        base = os.path.join(DAT_DIR, "tiers_stage2")
        subprocess.run(
            ["zimpl", "-t", "lp", "-l", "8192", "-o", base, STAGE2_ZPL_PATH],
            cwd=DAT_DIR, capture_output=True, text=True, check=True,
        )
        model = pyscipopt.Model()
        model.hideOutput()
        model.readProblem(f"{base}.lp")
        model.setParam("limits/time", CAP)
        start = time.time()
        model.optimize()
        row["stage2_s"] = round(time.time() - start, 2)
        row["status"] = model.getStatus()
        row["bb_nodes"] = model.getNNodes()
        if model.getStatus() in ("optimal", "feasible"):
            row["obj"] = round(model.getObjVal(), 2)
            tard = [model.getVal(v) for v in model.getVars() if v.name.lower().startswith("ta_n$")]
            if tard:
                row["sla_pct"] = round(sum(1 for t in tard if t <= 1e-6) / len(tard) * 100, 1)

        writer.writerow(row)
        handle.flush()
        print(f"{pickers:>8}{label:>18}{len(distinct):>5}{row['stage1_s']:>9}"
              f"{row['stage2_s']:>9}{row['bb_nodes']:>10}{row.get('sla_pct', '-'):>7}  {row['status']}")
        sys.stdout.flush()

print(f"\n{OUT}")
