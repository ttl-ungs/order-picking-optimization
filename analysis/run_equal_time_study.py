"""
Equal-time study: how good is the exact model's best solution when it
gets the SAME wall-clock time a heuristic needed?

The stress suites let opp_v5_2_split / opp_v5_1_mono run until SCIP proves
optimality (or the 40-min runner timeout). That measures the exact model's
quality ceiling, not what it delivers under a heuristic's time budget --
the standard way to compare a metaheuristic against an exact solver is at
equal time. Here each v5 model gets, per stress scenario, exactly the
total_time the heuristic took on that scenario (read from the heuristic's
latest stress CSV, e.g. results/opp_aco_4/stress/), passed to SCIP as
`limits/time`, and we record its best incumbent at that point (if any),
its dual bound and gap, next to the heuristic's objective.

  - opp_v5_2_split: Stage 1 (one routing MIP per batch) shares the budget
    evenly over the batches still to solve; Stage 2 (scheduling) gets what
    is left. No complete solution unless every batch got a route AND Stage
    2 found an incumbent in time.
  - opp_v5_1_mono: one solve with the whole budget.

The budget is wall-clock from the start of the model's pipeline (writing
.dat files, ZIMPL compilation and SCIP), like the heuristic's total_time;
SCIP's limit only covers its own solve, so `elapsed_s` can slightly exceed
`budget_s` by the compilation time -- reported as measured, not hidden.

NOT a unittest test. Run directly (needs `zimpl` on PATH, e.g. the
optimizacion conda env):

    python -m analysis.run_equal_time_study --budget-from opp_aco_4
    python -m analysis.run_equal_time_study --budget-from opp_hc_4 --id 04 05

Writes results/equal_time/output_equal_time_<budget-from>_<timestamp>.csv,
one row per (scenario, v5 model).
"""

import argparse
import csv
import glob
import os
import time
from datetime import datetime

from analysis.config import OUTPUTS_ROOT
from models.opp_v5_2_split.utils.cold_chain_validation import batches_without_eligible_picker
from models.utils.solve_registry import get_last
from tests.infra.zimpl.dat_files_builder import build_dat_files, write_indexed_dat, write_scalar_dat
from tests.infra.zimpl.zpl_utils import solve_zpl
from tests.shared_scenarios.stress.stress_scenarios_v5 import migrated_stress_scenario
from tests.shared_scenarios.stress.stress_scenarios_v5_designed import realistic_crew_scenario

# Stress test id -> (test method name, as it appears in every model's stress
# CSV, and the scenario builder) -- the same calls as
# tests/opp_v5_2_split/stress/test_case_<id>.py.
SCENARIOS = {
    "01": ("test_25_orders_per_batch_30_batches_100x100", lambda: migrated_stress_scenario(30, 30, 750, 100, 100)),
    "02": ("test_10_orders_per_batch", lambda: migrated_stress_scenario(10, 10, 100, 10, 10)),
    "03": ("test_8_orders_per_batch_7x7_320_orders", lambda: migrated_stress_scenario(40, 1, 320, 7, 7)),
    "04": ("test_realistic_crew_7x7_warehouse", lambda: realistic_crew_scenario(7)),
    "05": ("test_realistic_crew_13x13_warehouse", lambda: realistic_crew_scenario(13)),
    "06": ("test_realistic_crew_14x14_warehouse", lambda: realistic_crew_scenario(14)),
    "07": ("test_realistic_crew_15x15_warehouse", lambda: realistic_crew_scenario(15)),
    "08": ("test_realistic_crew_16x16_warehouse", lambda: realistic_crew_scenario(16)),
    "09": ("test_realistic_crew_rectangular_warehouse", lambda: realistic_crew_scenario(8, 21)),
    "10": ("test_realistic_crew_scheduling_heavy", lambda: realistic_crew_scenario(7, pickers=4)),
    "11": ("test_realistic_crew_cold_chain", lambda: realistic_crew_scenario(13, pickers=4, t_cold=280)),
    "12": ("test_larger_crew_8_batches_4_pickers", lambda: realistic_crew_scenario(7, batches=8, pickers=4)),
    "13": ("test_larger_crew_10_batches_5_pickers", lambda: realistic_crew_scenario(7, batches=10, pickers=5)),
    "14": ("test_larger_crew_12_batches_6_pickers", lambda: realistic_crew_scenario(7, batches=12, pickers=6)),
    "15": ("test_over_staffed_wave_6_batches_9_pickers", lambda: realistic_crew_scenario(10, batches=6, pickers=9)),
    "16": ("test_large_crew_single_wave", lambda: realistic_crew_scenario(10, batches=12, pickers=12)),
    "17": ("test_large_crew_three_second_batches", lambda: realistic_crew_scenario(10, batches=15, pickers=12)),
    "18": ("test_large_crew_half_second_batches", lambda: realistic_crew_scenario(10, batches=18, pickers=12)),
    "19": ("test_large_crew_two_batches_each", lambda: realistic_crew_scenario(10, batches=24, pickers=12)),
}

FIELDNAMES = [
    "id", "scenario", "model", "budget_from", "budget_s", "heuristic_obj",
    "status", "obj_val", "dual_bound", "mip_gap_pct", "elapsed_s", "heuristic_vs_model_pct",
]


def latest_heuristic_results(model_label):
    """{test method name: row} from the newest stress CSV of `model_label` that has v5-ported rows."""
    paths = sorted(
        glob.glob(os.path.join(OUTPUTS_ROOT, model_label, "stress", f"output_{model_label}_stress_tests_*.csv")),
        key=os.path.getmtime, reverse=True,
    )
    # Matched by method name, not file name: the v5 ports were test_case_v5_*.py
    # in older CSVs and test_case_NN.py (v5's own numbering) since the legacy
    # stress tests were removed; no legacy method name collides with v5's.
    v5_methods = {name for name, _ in SCENARIOS.values()}
    for path in paths:
        with open(path, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r["test"].split(".")[-1] in v5_methods]
        if rows:
            return path, {r["test"].split(".")[-1]: r for r in rows}
    raise SystemExit(f"No stress CSV with v5-ported rows under results/{model_label}/stress/")


def _last_solve_info():
    last = get_last()
    params = last.params if last is not None else {}
    return params.get("obj_val"), params.get("dual_bound"), params.get("mip_gap")


def run_split(scenario, budget):
    from tests.opp_v5_2_split.config import DAT_DIR, STAGE2_ZPL_PATH
    from tests.opp_v5_2_split.stage1_decomposition import solve_stage1_decomposed

    start = time.time()
    build_dat_files(DAT_DIR, scenario)
    remaining = budget - (time.time() - start)
    if remaining <= 0:
        return "no_time", None, None, None, time.time() - start

    # Stage 1 gets the budget minus a reserve for Stage 2: an even share,
    # as if Stage 2 were one more "batch" to solve.
    stage1_budget = remaining * len(scenario["B"]) / (len(scenario["B"]) + 1)
    stage1_status, stage1_values = solve_stage1_decomposed(DAT_DIR, time_budget_seconds=stage1_budget)
    route_times = {
        name.split("$")[-1]: value
        for name, value in stage1_values.items()
        if name.lower().startswith("r_b$") and name.split("$")[-1] in scenario["B"]
    }
    if set(route_times) != set(scenario["B"]):
        return f"stage1_{stage1_status}", None, None, None, time.time() - start

    write_indexed_dat(os.path.join(DAT_DIR, "route_time_b.dat"), route_times)
    write_indexed_dat(os.path.join(DAT_DIR, "velocities.dat"), scenario["V_p"])
    write_scalar_dat(os.path.join(DAT_DIR, "cold.dat"), scenario["T_cold"])

    stuck = batches_without_eligible_picker(
        scenario["P"], scenario["B"], scenario["N"], scenario["C_n"], scenario["B_nb"],
        scenario["T_setup"], scenario["T_pick"], route_times, scenario["V_p"], scenario["T_cold"],
    )
    if stuck:
        # Stage 1's time-limited routes may be too long for the cold-chain
        # limit even though optimal ones wouldn't be: no solution in time.
        return "stage1_routes_not_cold_chain_eligible", None, None, None, time.time() - start

    remaining = budget - (time.time() - start)
    if remaining <= 0:
        return "no_time_for_stage2", None, None, None, time.time() - start
    status, _ = solve_zpl(STAGE2_ZPL_PATH, dat_dir=DAT_DIR, time_limit_seconds=remaining)
    obj, bound, gap = _last_solve_info()
    if stage1_status != "optimal":
        # Stage 2 may well be "optimal" -- but only for the time-limited,
        # possibly non-optimal Stage 1 routes it was given, so the split as
        # a whole is not: report it as cut by the limit, and its Stage 2
        # dual bound / gap don't bound the true optimum either.
        status = f"timelimit_stage1+{status}_stage2"
        bound, gap = None, None
    return status, obj, bound, gap, time.time() - start


def run_mono(scenario, budget):
    from tests.opp_v5_1_mono.config import DAT_DIR, ZPL_PATH

    start = time.time()
    build_dat_files(DAT_DIR, scenario)
    remaining = budget - (time.time() - start)
    if remaining <= 0:
        return "no_time", None, None, None, time.time() - start
    status, _ = solve_zpl(ZPL_PATH, dat_dir=DAT_DIR, time_limit_seconds=remaining)
    obj, bound, gap = _last_solve_info()
    return status, obj, bound, gap, time.time() - start


RUNNERS = {"opp_v5_2_split": run_split, "opp_v5_1_mono": run_mono}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--budget-from", default="opp_aco_4", choices=["opp_aco_4", "opp_hc_4"],
                        help="Heuristic whose per-scenario total_time is the budget (default: opp_aco_4).")
    parser.add_argument("--models", nargs="+", default=list(RUNNERS), choices=list(RUNNERS))
    parser.add_argument("--id", nargs="+", default=sorted(SCENARIOS), choices=sorted(SCENARIOS), metavar="NN",
                        help="Stress test ids to run (default: all 19).")
    args = parser.parse_args(argv)

    source_path, heuristic = latest_heuristic_results(args.budget_from)
    print(f"Presupuestos tomados de {source_path}")

    out_dir = os.path.join(OUTPUTS_ROOT, "equal_time")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"output_equal_time_{args.budget_from}_{datetime.now():%Y%m%d_%H%M%S}.csv")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for test_id in args.id:
            name, build = SCENARIOS[test_id]
            row = heuristic.get(name)
            if row is None or row["status"] != "ok":
                print(f"[{test_id}] {name}: {args.budget_from} no tiene resultado ok, se saltea")
                continue
            budget = float(row["total_time"])
            heuristic_obj = float(row["obj_val"])
            scenario = build()
            for model in args.models:
                status, obj, bound, gap, elapsed = RUNNERS[model](scenario, budget)
                diff = (heuristic_obj - obj) / obj * 100 if obj else None
                writer.writerow({
                    "id": test_id, "scenario": name, "model": model, "budget_from": args.budget_from,
                    "budget_s": round(budget, 3), "heuristic_obj": heuristic_obj,
                    "status": status, "obj_val": obj, "dual_bound": bound,
                    "mip_gap_pct": gap * 100 if gap is not None and gap < 1e20 else None,
                    "elapsed_s": round(elapsed, 3), "heuristic_vs_model_pct": diff,
                })
                f.flush()
                shown = f"{obj:.2f}" if obj is not None else "sin solucion"
                print(f"[{test_id}] {model}: {status}, obj {shown} (heuristica {heuristic_obj:.2f}), "
                      f"presupuesto {budget:.1f}s, usado {elapsed:.1f}s")

    print(f"\nResultados en {out_path}")


if __name__ == "__main__":
    main()
