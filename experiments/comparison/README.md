# Comparison between models

For comparisons that involve more than one model. The scope: OPP-Split (reference), OPP-Mono and the
two heuristics.

| Script | What it does |
| --- | --- |
| `comparability.py` | The registry of **which results of the Split and of the heuristics can be compared** (status and/or objective, and the reason when not), and the cross with the latest results of OPP-HC and OPP-ACO. |
| `run_equal_time_study.py` | Equal-time study: the exact models get, per stress scenario, the same wall-clock time a heuristic needed, and their best incumbent, dual bound and gap are recorded next to the heuristic's objective. |

```bash
python -m experiments.comparison.comparability
python -m experiments.comparison.run_equal_time_study --budget-from opp_hc --id 04 05
```

`comparability` writes `results/comparability/comparability_split_vs_heuristics.csv` (the registry: one
row per functional instance or stress scenario, with `comparable_status`, `comparable_objective` and
`not_comparable_reason`) and `results/comparability/results_split_vs_heuristics.csv` (the registry
crossed with the heuristics' results: objective, time, `gap_pct`, `speedup`, `status_matches`). Any table
or chart that compares the Split with the heuristics must filter on `comparable_status` /
`comparable_objective`; the rules are in [../../docs/specs/comparabilidad_split_heuristicas.md](../../docs/specs/comparabilidad_split_heuristicas.md).

`run_equal_time_study` writes `results/equal_time/`. `--id` is the number of the stress scenario
(`tests/stress_cases/case_NN.py`). The comparison of OPP-Split with OPP-Mono is in
[`verification/`](../../verification/README.md).
