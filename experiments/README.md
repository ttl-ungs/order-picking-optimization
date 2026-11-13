# Experiments

Everything that is not a test and reads or produces `results/`: the studies, the comparisons between
models and the reports. It is organized by **who it is for**, so you can tell at a glance whether
something applies to every model, to a pair of them or to a single one.

| Directory | For | What it holds |
| --- | --- | --- |
| [`common/`](#common) | All four models | Which result files count and how they are loaded. |
| [`comparison/`](comparison/README.md) | Models against each other | Which results can be compared, and the equal-time study. |
| [`exact/`](exact/README.md) | OPP-Split and OPP-Mono | Explorations of where each exact model stops solving, and the reports generated from them. |
| [`heuristics/`](heuristics/README.md) | OPP-HC and OPP-ACO | Studies of the heuristics (`hc/` for OPP-HC, `aco/` for OPP-ACO). |

## How it works

Nothing here runs the test suites. The tests write `results/<model>/<tier>/*.csv`
(`python -m tests.run_suite <model> <tier>` with `WRITE_RESULTS_CSV=1`); the experiments read those
files, or run the models themselves on a fixed set of scenarios and write their own CSV under
`results/` (`results/<model>/<study>/`, `results/equal_time/`) or next to the study
(`exact/studies/`). Instances are always identified by the unittest **method name**, which is the
same in the four models, so results of different models join on it.

All scripts run from the repository root with `python -m experiments.<directory>.<script>`.

## common

- `config.py` — the model labels and their directories under `results/` (`MODEL_DIRS`), the two heuristics (`HEURISTIC_MODELS`), and `LATEST_FILE_OVERRIDES`: which CSV counts for each `(model, scenario)` when several runs exist (the consolidated runs are files with a fixed name, without a timestamp).
- `load.py` — discovers those CSVs and concatenates them into one DataFrame (one row per test execution, with `model`, `scenario`, `instance` = method name and `source_file`). A missing `(model, scenario)` is reported on the console, never silently ignored.
