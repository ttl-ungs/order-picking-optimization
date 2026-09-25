"""
Seed-stability study: for each of the 6 Hill Climbing/ACO models
(hc_2/3/4, aco_2/3/4), runs a small set of shared representative
instances (tests/shared_scenarios/instances.py) N_SEEDS times each,
varying ONLY params.Seed, to measure how much a heuristic's own
randomness moves its objective value around for the EXACT SAME problem --
distinct from the optimality gap vs opp_v4/opp_v5_2_split (analysis.metrics.
quality_gap_table), which measures accuracy against a ground truth, not
repeatability. A good algorithm should have low dispersion across seeds;
Hill Climbing (steepest-descent from a single random-ish initial
solution) is expected to show a wider best-vs-worst gap than ACO
(pheromone reinforcement converges the swarm towards similar answers
across runs), per the brief this study was requested from.

NOT a unittest test -- no pass/fail assertion, and deliberately outside
tests/test_runner.py's one-shot-per-instance harness (that harness times
out/registers a single result per test id; this needs many repeated
solves of the SAME instance instead). Run directly:

    python -m analysis.run_stability_study

6 models x 3 instances x 30 seeds = 540 solves. Hill Climbing instances
are near-instant; ACO's are a few seconds each, so budget several minutes
total for a full run -- safe to run in the background.

Writes results/<model>/stability/output_<model>_stability_<timestamp>.csv,
one row per (instance, seed) run, for analysis.metrics.stability_table to
aggregate (mean/std/best/worst/gap_best_worst_pct per model x instance).
"""

import csv
import os
import time
from datetime import datetime

from analysis.config import OUTPUTS_ROOT, STABILITY_MODELS
from dtos.aco.solve_aco_3_model_dto import SolveAco3ModelDTO
from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from dtos.hc.solve_hc_3_model_dto import SolveHC3ModelDTO
from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO
from dtos.hc.solve_hc_model_dto import SolveHCModelDTO
from models.opp_aco_2 import OPPAntColonyOptimization as OPPAntColonyOptimization2
from models.opp_aco_3 import OPPAntColonyOptimization as OPPAntColonyOptimization3
from models.opp_aco_4 import OPPAntColonyOptimization as OPPAntColonyOptimization4
from models.opp_hc_2 import OPPHillClimbing as OPPHillClimbing2
from models.opp_hc_3 import OPPHillClimbing as OPPHillClimbing3
from models.opp_hc_4 import OPPHillClimbing as OPPHillClimbing4
from tests.shared_scenarios.adapters import build_model_dto, build_params
from tests.shared_scenarios.instances import ALL_INSTANCES

N_SEEDS = 30

# label -> (model class, params DTO class, extra DTO fields beyond the
# common ones build_params already sets -- empty means "just use that
# DTO's own defaults", which for hc_4/aco_4 already means V_p unset/
# T_frio_max=+inf (cold chain disabled) and for hc_3/aco_3 Min_dwell=0.0
# (no synthetic congestion floor) -- this study compares search behavior
# on the SAME underlying problem across the family, not the cold-chain/
# congestion features themselves.
MODEL_REGISTRY = {
    "opp_hc_2": (OPPHillClimbing2, SolveHCModelDTO, {}),
    "opp_hc_3": (OPPHillClimbing3, SolveHC3ModelDTO, {}),
    "opp_hc_4": (OPPHillClimbing4, SolveHC4ModelDTO, {}),
    "opp_aco_2": (OPPAntColonyOptimization2, SolveAcoModelDTO, {}),
    "opp_aco_3": (OPPAntColonyOptimization3, SolveAco3ModelDTO, {}),
    "opp_aco_4": (OPPAntColonyOptimization4, SolveAco4ModelDTO, {}),
}

assert set(MODEL_REGISTRY) == set(STABILITY_MODELS), (
    "MODEL_REGISTRY (needs actual classes, defined here) and "
    "analysis.config.STABILITY_MODELS (the single source of truth for which "
    "models the stability study covers) drifted apart -- update both."
)


def _solve_once(model_cls, dto_cls, extra_fields, instance, seed):
    """
    Returns (status, obj_val, elapsed). model.solve() has two different
    return shapes depending on the outcome (see e.g. models/opp_hc_4/
    opp_hc_4.py::solve -- a bare ("infeasible", None) tuple on early
    rejection, or a SolveResult object -- itself iterable as (status,
    output) -- on success), so branch on the raw return instead of
    unpacking blindly (unpacking alone would lose access to
    SolveResult.params, which is where obj_val actually lives).
    """
    model_dto = build_model_dto(instance)
    params = build_params(instance, dto_cls, **extra_fields)
    params.Seed = seed

    model = model_cls(model_dto)

    t0 = time.time()
    raw = model.solve(params)
    elapsed = time.time() - t0

    if isinstance(raw, tuple):
        status, _output = raw
        obj_val = None
    else:
        status = raw.status
        obj_val = raw.params.get("obj_val")

    return status, obj_val, elapsed


def main():
    for model_label, (model_cls, dto_cls, extra_fields) in MODEL_REGISTRY.items():
        rows = []

        for instance_fn in ALL_INSTANCES:
            instance = instance_fn()

            for seed in range(N_SEEDS):
                status, obj_val, elapsed = _solve_once(model_cls, dto_cls, extra_fields, instance, seed)
                rows.append({
                    "model": model_label,
                    "instance": instance["name"],
                    "seed": seed,
                    "status": status,
                    "obj_val": obj_val,
                    "elapsed": elapsed,
                })
                print(f"{model_label} | {instance['name']} | seed={seed} | status={status} | obj_val={obj_val}")

        out_dir = os.path.join(OUTPUTS_ROOT, model_label, "stability")
        os.makedirs(out_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(out_dir, f"output_{model_label}_stability_{timestamp}.csv")

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["model", "instance", "seed", "status", "obj_val", "elapsed"])
            writer.writeheader()
            writer.writerows(rows)

        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
