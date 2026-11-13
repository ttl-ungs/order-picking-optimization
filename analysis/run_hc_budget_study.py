"""
Search-budget study for opp_hc: does the stress suite's Max_it = 200 /
Max_imp = 60 (tests/opp_hc/stress/stress_test_case.py) cut the
search short? Each (scenario, seed) runs with every (Max_it, Max_imp) pair
in BUDGETS; the delta is against 200/60 on the same scenario and seed.

Why 200/60 is the baseline: the values first appear, uncommented, in the
functional tests of the commit that added opp_hc (66d77a3, 2026-09-09),
and the stress base test copied them (df7a052, 2026-09-26). No tuning
behind them is recorded, so this study measures whether they bind.

The 200/60 rows across seeds also give the seed-to-seed spread of the
objective (how much a different draw changes the result).

Everything else is the stress suite's setting: Max_time 30 s. Scenario 01
(100x100) is excluded by default: its initial construction alone exceeds
Max_time, so the search never iterates and the budget is irrelevant there.

Results depend on Seed alone since stitch_route iterates its candidates in
sorted order (models/utils/route_construction.py, 2026-10-19); before that
fix they also depended on PYTHONHASHSEED.

NOT a unittest test. Keep the machine awake: a suspended run keeps its
wall clock running and gets cut by Max_time (seen 2026-10-15).

    caffeinate -dims python -m analysis.run_hc_budget_study
    python -m analysis.run_hc_budget_study --id 03 17 18 --seeds 1 2

~3-4 min per seed for ids 02-19 (measured 2026-10-14; construction
dominates, ~0.4-5 s per run).

Writes results/opp_hc/budget/output_opp_hc_budget_<timestamp>.csv.
"""

import argparse
import contextlib
import csv
import io
import os
import time
from datetime import datetime

from analysis.config import OUTPUTS_ROOT
from analysis.run_equal_time_study import SCENARIOS
from analysis.aco_study_common import scenario_ids
from dtos.hc.solve_hc_model_dto import SolveHCModelDTO
from models.opp_hc import OPPHillClimbing
from tests.infra.factories.scenario_adapter import build_model_dto_and_params

# (Max_it, Max_imp). The first one is the baseline every delta is against.
BUDGETS = [(200, 60), (200, 120), (500, 60), (500, 120)]

MAX_TIME = 30.0

FIELDNAMES = [
    "id", "scenario", "seed", "Max_it", "Max_imp", "status", "obj_val", "delta_vs_200_60_pct",
    "iterations_run", "best_found_at_iteration", "stopped_by", "elapsed_s",
]


def solve_hc(scenario, seed, max_it, max_imp):
    """One opp_hc run; returns status, obj_val, iterations, stop reason and wall-clock time."""
    model_dto, params = build_model_dto_and_params(scenario, SolveHCModelDTO, seed=seed)
    params.Max_it, params.Max_imp, params.Max_time = max_it, max_imp, MAX_TIME

    log = io.StringIO()
    start = time.time()
    with contextlib.redirect_stdout(log):
        raw = OPPHillClimbing(model_dto).solve(params)
    elapsed = time.time() - start

    if isinstance(raw, tuple):
        return {"status": raw[0], "obj_val": None, "iterations_run": None,
                "best_found_at_iteration": None, "stopped_by": None, "elapsed_s": round(elapsed, 3)}

    iterations = raw.params["iterations_run"]
    if "time budget exceeded" in log.getvalue():
        stopped_by = "Max_time"
    elif iterations >= max_it:
        stopped_by = "Max_it"
    else:
        stopped_by = "Max_imp"
    return {
        "status": raw.status,
        "obj_val": raw.params["obj_val"],
        "iterations_run": iterations,
        "best_found_at_iteration": raw.params["best_found_at_iteration"],
        "stopped_by": stopped_by,
        "elapsed_s": round(elapsed, 3),
    }


def output_path():
    out_dir = os.path.join(OUTPUTS_ROOT, "opp_hc", "budget")
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"output_opp_hc_budget_{datetime.now():%Y%m%d_%H%M%S}.csv")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--id", nargs="+", default=[i for i in SCENARIOS if i != "01"], metavar="NN")
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    args = parser.parse_args(argv)

    path = output_path()

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for test_id in scenario_ids(args.id):
            name, build = SCENARIOS[test_id]
            for seed in args.seeds:
                baseline_obj = None
                for max_it, max_imp in BUDGETS:
                    result = solve_hc(build(), seed, max_it, max_imp)
                    if (max_it, max_imp) == BUDGETS[0]:
                        baseline_obj = result["obj_val"]
                    delta = None
                    if result["obj_val"] is not None and baseline_obj:
                        delta = (result["obj_val"] - baseline_obj) / baseline_obj * 100
                    writer.writerow({
                        "id": test_id, "scenario": name, "seed": seed,
                        "Max_it": max_it, "Max_imp": max_imp, "delta_vs_200_60_pct": delta, **result,
                    })
                    f.flush()
                    delta_text = f"{delta:+.3f}%" if delta is not None else "-"
                    print(f"[{test_id}] seed {seed} {max_it}/{max_imp}: {result['status']} obj {result['obj_val']} "
                          f"({delta_text}), {result['iterations_run']} it, {result['elapsed_s']:.1f}s", flush=True)

    print(f"\nResultados en {path}")


if __name__ == "__main__":
    main()
