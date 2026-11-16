# Studies of the heuristics

Studies of the search parameters of the heuristics. They are not tests: each one runs the model on the
stress scenarios (`--id NN` is the number of `tests/stress_cases/case_NN.py`) and writes a CSV under
`results/<model>/<study>/`. Scenario 01 (100x100, about 35 minutes per run) is excluded by default.

| Directory | Model | Script | Question |
| --- | --- | --- | --- |
| `hc/` | OPP-HC | `run_hc_budget_study.py` | Does the stress budget (`Max_it = 200`, `Max_imp = 60`) cut the search short? Also gives the seed-to-seed spread of the objective. |
| `aco/` | OPP-ACO | `run_aco_ablation_study.py` | How much of the result comes from the ant colony itself and how much from each local-search component. |
| `aco/` | OPP-ACO | `run_aco_pheromone_study.py` | How far does tuning the colony alone (`alpha`, `beta`, `rho`) move the result? |
| `aco/` | OPP-ACO | `run_aco_seed_study.py` | How much does a different `Seed` change the result? |
| `aco/` | OPP-ACO | `aco_study_common.py` | Helpers of the three ACO studies (not a study). |

```bash
python -m experiments.heuristics.hc.run_hc_budget_study --id 03 17 18 --seeds 1 2
PYTHONHASHSEED=0 python -m experiments.heuristics.aco.run_aco_ablation_study --id 04 --seeds 1 2 3
PYTHONHASHSEED=0 python -m experiments.heuristics.aco.run_aco_pheromone_study --id 06
python -m experiments.heuristics.aco.run_aco_seed_study --id 04 06 --seeds 1 2 --workers 2
```

The ACO studies need `PYTHONHASHSEED=0` for a reproducible run. Gaps are against the Split's objective
from its newest stress CSV (`None` where the Split timed out). Results go to `results/opp_hc/budget/`,
`results/opp_aco/ablation/`, `results/opp_aco/pheromone/` and `results/opp_aco/seeds/`.
