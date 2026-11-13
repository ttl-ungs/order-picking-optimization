"""
Seed study for opp_aco: how much does a different Seed change the
result on the Split stress scenarios? Each (scenario, seed) runs once with
the DTO defaults (the same parameters as the stress suite); the spread is
the difference between the best and worst objective of a scenario across
seeds, and the gap is against opp_split's objective (None where the Split
timed out).

Scenario 01 (100x100, ~35 min per run) is excluded by default, as in
run_hc_budget_study.py.

Results depend on Seed alone since stitch_route iterates its candidates in
sorted order (models/utils/route_construction.py, 2026-10-19).

Runs are spread over --workers processes. Running in parallel makes the
runs compete for CPU, so elapsed_s is NOT comparable with the stress suite's
times; only the objective is meant to be read. A run that hits Max_time
(1800 s by default) would depend on that, but no stress run except 01 gets
close (max ~550 s in the 2026-09-29 stress CSV).

NOT a unittest test. Keep the machine awake:

    caffeinate -dims python -m experiments.heuristics.aco.run_aco_seed_study
    python -m experiments.heuristics.aco.run_aco_seed_study --id 04 06 --seeds 1 2 --workers 2

~45 min per seed for ids 02-19 sequentially (2026-09-29 stress CSV), so
~1.5 h for 5 seeds with 3 workers.

Writes results/opp_aco/seeds/output_opp_aco_seeds_<timestamp>.csv
(one row per run, in completion order).
"""

import argparse
import contextlib
import csv
import io
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

from experiments.heuristics.aco.aco_study_common import gap_pct, output_path, scenario_ids, solve_aco, split_reference_objectives
from experiments.comparison.run_equal_time_study import SCENARIOS

FIELDNAMES = [
    "id", "scenario", "seed", "status", "obj_val", "split_obj", "gap_pct",
    "route_time_sum", "elapsed_s", "iterations_run", "error",
]

# Rough sequential run time per id (s, 2026-09-29 stress CSV), to start the
# longest runs first and balance the workers.
APPROX_SECONDS = {
    "19": 551, "03": 307, "18": 274, "09": 204, "17": 169, "07": 156, "16": 131, "12": 128,
    "13": 120, "08": 119, "06": 116, "02": 94, "05": 84, "11": 84, "14": 76, "15": 53,
    "10": 15, "04": 13, "01": 2095,
}


def run_one(test_id, seed):
    name, build = SCENARIOS[test_id]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = solve_aco(build(), seed)
        return {"id": test_id, "scenario": name, "seed": seed, "error": None, **result}
    except Exception:
        return {"id": test_id, "scenario": name, "seed": seed, "status": "error",
                "error": traceback.format_exc(limit=3).replace("\n", " | ")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--id", nargs="+", default=[i for i in SCENARIOS if i != "01"], metavar="NN")
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args(argv)

    ids = scenario_ids(args.id)
    reference = split_reference_objectives()
    path = output_path("seeds")
    tasks = sorted(((i, s) for i in ids for s in args.seeds), key=lambda t: -APPROX_SECONDS.get(t[0], 0))

    with open(path, "w", newline="", encoding="utf-8") as f, ProcessPoolExecutor(args.workers) as pool:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        f.flush()
        futures = [pool.submit(run_one, i, s) for i, s in tasks]
        for n, future in enumerate(as_completed(futures), 1):
            row = future.result()
            row["split_obj"] = reference.get(row["scenario"])
            row["gap_pct"] = gap_pct(row.get("obj_val"), row["split_obj"])
            writer.writerow(row)
            f.flush()
            gap_text = f"{row['gap_pct']:+.3f}%" if row["gap_pct"] is not None else "-"
            print(f"[{n}/{len(tasks)}] {row['id']} seed {row['seed']}: {row['status']} obj {row.get('obj_val')} "
                  f"({gap_text}), {row.get('elapsed_s')}s", flush=True)

    print(f"\nResultados en {path}")


if __name__ == "__main__":
    main()
