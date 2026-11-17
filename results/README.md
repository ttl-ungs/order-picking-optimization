# Results

Data produced by the runs; nothing here is code. `experiments/` and `verification/` read it.

```
results/
├── <model>/<tier>/             opp_split, opp_mono, opp_hc, opp_aco; tier = functional | stress
│   ├── output_<model>_<tier>_tests.csv      the consolidated run that counts (fixed name, no timestamp; opp_split stress: ..._tests_parallel.csv, Stage 1 on 6 workers)
│   └── solutions/<run>/*.json               solutions saved with WRITE_SOLUTIONS=1
├── <model>/<study>/            studies of a model: ablation, pheromone, seeds (opp_aco), budget (opp_hc)
├── compliance/<model>/<tier>/  verification of the heuristics' saved solutions against opp_mono
├── comparability/              which results can be compared (registry), the cross with the heuristics, Split vs Mono
└── equal_time/                 equal-time study: exact models given the time a heuristic needed
```

- One row per test. The `test` column is the dotted unittest id; models are joined by the last segment, the method name.
- A run writes `output_<model>_<tier>_tests_<timestamp>.csv`; `experiments/common/config.py` (`LATEST_FILE_OVERRIDES`) declares which file counts when several exist.
- Columns: status (`ok`, `failed`, `timeout`), `total_time`, `model_time`, `obj_val`, `peak_rss_mb`, the instance parameters and, for the heuristics, `solution_file`.
- Runs are produced with `python -m tests.run_suite <model> <tier>` and `WRITE_RESULTS_CSV=1`; the layout is checked by `python -m scripts.check_repo`.
