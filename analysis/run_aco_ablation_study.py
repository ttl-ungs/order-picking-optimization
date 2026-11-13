"""
Ablation study for opp_aco's hybrid (ACO + local search) components:
how much of its result comes from the ant colony itself and how much from
each local-search component added on top (see opp_aco's header and the
COMPONENT_FLAGS in analysis/aco_study_common.py).

Variants, each adding to the previous one:

  sin_busqueda_local  colony only: pick-to-pick construction + MAX-MIN
                      pheromone, no local search of any kind
  busqueda_rutas      + local search on every ant's route (2-opt + segment
                      re-routing), elite-route polishing, and recombining
                      each batch's shortest route into the best solution
  completo            + schedule local search (default opp_aco)

Everything else (Seed, ants, iterations, alpha/beta/rho, Max_time) is the
DTO default, so "completo" reproduces a normal opp_aco run. Each
(scenario, variant) runs once per seed; the gap is against
opp_split's objective from its newest stress CSV (None where v5
timed out).

NOT a unittest test. Run directly, ideally with nothing else competing for
CPU and with a fixed hash seed for exact reproducibility:

    PYTHONHASHSEED=0 python -m analysis.run_aco_ablation_study
    PYTHONHASHSEED=0 python -m analysis.run_aco_ablation_study --id 04 --seeds 1 2 3

Default: ids 04 (7x7), 06 (14x14), 15 (over_staffed), seeds 1 2 3 -- 27
runs, roughly 30 min: ~13-15 s per 7x7 run (measured 2026-09-27, with and
without local search), ~110 s per 14x14 run, ~55 s per over_staffed run
(from the 2026-09-27 stress CSV; ant construction dominates, so the
variants take similar times).

Writes results/opp_aco/ablation/output_opp_aco_ablation_<timestamp>.csv.
"""

import argparse
import csv

from analysis.aco_study_common import (
    SCENARIOS, gap_pct, output_path, scenario_ids, solve_aco, split_reference_objectives, warn_if_hash_seed_unset,
)

VARIANTS = {
    "sin_busqueda_local": {
        "_IMPROVE_ANT_ROUTES": False, "_POLISH_ELITE_ROUTES": False,
        "_RECOMBINE_SHORTEST_ROUTES": False, "_SCHEDULE_LOCAL_SEARCH": False,
    },
    "busqueda_rutas": {
        "_IMPROVE_ANT_ROUTES": True, "_POLISH_ELITE_ROUTES": True,
        "_RECOMBINE_SHORTEST_ROUTES": True, "_SCHEDULE_LOCAL_SEARCH": False,
    },
    "completo": {
        "_IMPROVE_ANT_ROUTES": True, "_POLISH_ELITE_ROUTES": True,
        "_RECOMBINE_SHORTEST_ROUTES": True, "_SCHEDULE_LOCAL_SEARCH": True,
    },
}

FIELDNAMES = [
    "id", "scenario", "variant", "seed", "status", "obj_val", "split_obj", "gap_pct",
    "route_time_sum", "elapsed_s", "iterations_run",
]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--id", nargs="+", default=["04", "06", "15"], metavar="NN")
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=list(VARIANTS))
    args = parser.parse_args(argv)

    warn_if_hash_seed_unset()
    reference = split_reference_objectives()
    path = output_path("ablation")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for test_id in scenario_ids(args.id):
            name, build = SCENARIOS[test_id]
            scenario = build()
            split_obj = reference.get(name)
            for variant in args.variants:
                for seed in args.seeds:
                    result = solve_aco(scenario, seed, components=VARIANTS[variant])
                    gap = gap_pct(result["obj_val"], split_obj)
                    writer.writerow({
                        "id": test_id, "scenario": name, "variant": variant, "seed": seed,
                        "split_obj": split_obj, "gap_pct": gap, **result,
                    })
                    f.flush()
                    gap_text = f"{gap:+.3f}%" if gap is not None else "sin referencia v5"
                    print(f"[{test_id}] {variant} seed {seed}: obj {result['obj_val']} ({gap_text}), "
                          f"{result['elapsed_s']:.1f}s")

    print(f"\nResultados en {path}")


if __name__ == "__main__":
    main()
