"""
Pheromone-parameter sensitivity study for opp_aco: how far tuning the
colony alone (alpha, beta, rho) moves the result, with the local-search
components OFF by default -- so the effect measured is the colony's, not
the local search's (see run_aco_ablation_study.py for the latter).

Grid (full factorial, 27 combinations by default):

  alpha (pheromone weight)       0.5, 1.0, 2.0    (DTO default 1.0)
  beta  (distance weight)        1.0, 2.5, 4.0    (DTO default 2.5)
  rho   (evaporation, DTO's E)   0.05, 0.15, 0.30 (DTO default 0.15)

Ranges bracket the defaults and the values the thesis papers report:
Alaya & Solnon use alpha = 1, beta = 4-8, rho = 0.01-0.1 (Table 1, p.5);
Lesch et al. (2023) alpha = 1, beta = 2, rho = 0.02 (p.18620). Note rho
also sets opp_aco's MAX-MIN bounds (tau_max = 2 / rho), as in MMAS.
Ants, iterations, Seed and Max_time stay at the DTO defaults. The gap is
against opp_split's objective from its newest stress CSV.

NOT a unittest test. Run directly, ideally with nothing else competing for
CPU and with a fixed hash seed for exact reproducibility:

    PYTHONHASHSEED=0 python -m experiments.heuristics.aco.run_aco_pheromone_study
    PYTHONHASHSEED=0 python -m experiments.heuristics.aco.run_aco_pheromone_study --id 06
    PYTHONHASHSEED=0 python -m experiments.heuristics.aco.run_aco_pheromone_study --with-local-search

Default: id 04 (7x7), seeds 1 2 3 -> 81 runs, roughly 15-20 min (one
7x7 run without local search took 12.5 s, 2026-09-27; alpha/beta/rho can
shift that). id 06 (14x14) is ~8x slower per run: ~2.5 h for the full grid.

Writes results/opp_aco/pheromone/output_opp_aco_pheromone_<timestamp>.csv.
"""

import argparse
import csv
import itertools

from experiments.heuristics.aco.aco_study_common import (
    COMPONENT_FLAGS, SCENARIOS, gap_pct, output_path, scenario_ids, solve_aco, split_reference_objectives,
    warn_if_hash_seed_unset,
)

FIELDNAMES = [
    "id", "scenario", "alpha", "beta", "rho", "local_search", "seed", "status", "obj_val", "split_obj",
    "gap_pct", "route_time_sum", "elapsed_s", "iterations_run",
]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--id", nargs="+", default=["04"], metavar="NN")
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--alpha", nargs="+", type=float, default=[0.5, 1.0, 2.0])
    parser.add_argument("--beta", nargs="+", type=float, default=[1.0, 2.5, 4.0])
    parser.add_argument("--rho", nargs="+", type=float, default=[0.05, 0.15, 0.30])
    parser.add_argument("--with-local-search", action="store_true",
                        help="Keep opp_aco's local-search components on (default: all off).")
    args = parser.parse_args(argv)

    warn_if_hash_seed_unset()
    reference = split_reference_objectives()
    components = {flag: args.with_local_search for flag in COMPONENT_FLAGS}
    path = output_path("pheromone")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for test_id in scenario_ids(args.id):
            name, build = SCENARIOS[test_id]
            scenario = build()
            split_obj = reference.get(name)
            for alpha, beta, rho in itertools.product(args.alpha, args.beta, args.rho):
                for seed in args.seeds:
                    result = solve_aco(scenario, seed, alpha=alpha, beta=beta, rho=rho, components=components)
                    gap = gap_pct(result["obj_val"], split_obj)
                    writer.writerow({
                        "id": test_id, "scenario": name, "alpha": alpha, "beta": beta, "rho": rho,
                        "local_search": args.with_local_search, "seed": seed,
                        "split_obj": split_obj, "gap_pct": gap, **result,
                    })
                    f.flush()
                    gap_text = f"{gap:+.3f}%" if gap is not None else "sin referencia del Split"
                    print(f"[{test_id}] a={alpha} b={beta} rho={rho} seed {seed}: "
                          f"obj {result['obj_val']} ({gap_text}), {result['elapsed_s']:.1f}s")

    print(f"\nResultados en {path}")


if __name__ == "__main__":
    main()
