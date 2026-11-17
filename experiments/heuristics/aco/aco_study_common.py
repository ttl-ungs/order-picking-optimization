"""
Shared helpers for the opp_aco studies (run_aco_ablation_study.py,
run_aco_pheromone_study.py): run opp_aco once on a stress scenario
with given pheromone parameters / hybrid components, and look up the Split's
objective on that scenario to report the gap.

Scenarios are the same 19 stress scenarios as run_equal_time_study.py
(SCENARIOS, keyed by stress test id).
"""

import csv
import glob
import os
import time

from experiments.common.config import OUTPUTS_ROOT
from experiments.comparison.run_equal_time_study import SCENARIOS
from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.opp_aco import OPPAntColonyOptimization
from models.opp_aco.utils import exec_time
from models.utils.solve_registry import get_last
from tests.infra.factories.scenario_adapter import build_model_dto_and_params

# Hybrid components of opp_aco (class attributes, see its header), in the
# order the ablation adds them.
COMPONENT_FLAGS = (
    "_IMPROVE_ANT_ROUTES",
    "_POLISH_ELITE_ROUTES",
    "_RECOMBINE_SHORTEST_ROUTES",
    "_SCHEDULE_LOCAL_SEARCH",
)


def split_reference_objectives():
    """
    {test method name: opp_split obj_val or None}, from the newest opp_split
    stress CSV that has the test, even if that row is a timeout (None then).
    An older CSV is never used as a fallback: it may hold the objective of a
    different objective function (another W_c).
    """
    paths = sorted(
        glob.glob(os.path.join(OUTPUTS_ROOT, "opp_split", "stress", "*.csv")),
        key=os.path.getmtime, reverse=True,
    )
    reference = {}
    for path in paths:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row["test"].split(".")[-1]
                if name in reference:
                    continue
                reference[name] = float(row["obj_val"]) if row["status"] == "ok" else None
    return reference


def solve_aco(scenario, seed, alpha=None, beta=None, rho=None, components=None):
    """
    One opp_aco run. `alpha`/`beta`/`rho` override the DTO defaults
    (Alpha 1.0, Beta 2.5, E 0.15) when given; `components` maps flag name
    (COMPONENT_FLAGS) -> bool, overriding opp_aco's defaults (all on) on
    this model instance only. Returns a dict with status, obj_val,
    elapsed_s, route_time_sum (sum over batches of T_travel * route distance
    of the reported solution) and iterations_run.
    """
    model_dto, params = build_model_dto_and_params(scenario, SolveAcoModelDTO, seed=seed)
    if alpha is not None:
        params.Alpha = alpha
    if beta is not None:
        params.Beta = beta
    if rho is not None:
        params.E = rho

    model = OPPAntColonyOptimization(model_dto)
    for flag, enabled in (components or {}).items():
        if flag not in COMPONENT_FLAGS:
            raise ValueError(f"unknown opp_aco component flag {flag!r}")
        setattr(model, flag, enabled)

    start = time.time()
    raw = model.solve(params)
    elapsed = time.time() - start

    status = raw[0] if isinstance(raw, tuple) else raw.status
    last = get_last()
    info = getattr(model, "last_solution_info", None) or {}
    route_time_sum = None
    if status != "infeasible" and info.get("routes"):
        route_time_sum = sum(
            scenario["T_travel"] * exec_time.calculate_route_distance(model_dto.location_graph, route)
            for route in info["routes"].values()
        )
    return {
        "status": status,
        "obj_val": last.params.get("obj_val") if status != "infeasible" and last else None,
        "elapsed_s": round(elapsed, 3),
        "route_time_sum": route_time_sum,
        "iterations_run": last.params.get("iterations_run") if last else None,
    }


def gap_pct(obj, reference):
    """(obj - reference) / reference * 100, or None if either is missing."""
    if obj is None or reference is None:
        return None
    return (obj - reference) / reference * 100


def warn_if_hash_seed_unset():
    # The iteration order of sets of str varies per process unless
    # PYTHONHASHSEED is fixed, so two runs with the same Seed can differ
    # slightly (149,217.67 vs 149,219.75 on 7x7).
    if os.environ.get("PYTHONHASHSEED") is None:
        print("AVISO: PYTHONHASHSEED no está fijado; los resultados pueden variar levemente entre corridas. "
              "Para reproducibilidad exacta: PYTHONHASHSEED=0 python -m ...")


def output_path(kind):
    from datetime import datetime

    out_dir = os.path.join(OUTPUTS_ROOT, "opp_aco", kind)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"output_opp_aco_{kind}_{datetime.now():%Y%m%d_%H%M%S}.csv")


def scenario_ids(ids):
    unknown = [i for i in ids if i not in SCENARIOS]
    if unknown:
        raise SystemExit(f"Ids desconocidos: {unknown}. Válidos: {sorted(SCENARIOS)}")
    return ids
