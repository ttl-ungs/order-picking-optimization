# Repo scripts

Run from the repository root with `python -m scripts.<name>`.

| Script | What it does |
| --- | --- |
| `check_repo` | Consistency checks in seconds: every module imports, `family_case`/`migrated_case` targets exist, test files are `test_case_<NN\|slug>.py` with continuous numbering, no leftover directories or removed module paths. `--skip-imports` skips the (slower) import sweep. Exit code 1 on any failure. |
| `run_all` | Runs the suites of every model and compares them with `baseline_counts.json` (test counts on `main` before the 2026-09 reorganization, plus known failures). `--collect-only` only counts tests (seconds); `--profile fast` (default) = HC/ACO functional suites, `--profile full` = every model (`opp_v1`..`opp_v5` use SCIP/zimpl and are slow); `--tier stress` runs stress suites with a per-test cap (`--stress-timeout-minutes`, timeouts are reported, not failures). `--json` writes a machine-readable report. |
| `new_family_tests` | Writes the one-line `family_case` test files of a new model family from an existing base family (e.g. `opp_hc_5` on top of `opp_hc_2`). See its docstring for the command. |

Typical uses:

```bash
python -m scripts.check_repo                        # after moving/renaming anything
python -m scripts.run_all --collect-only --profile full --tier all   # nothing lost or duplicated?
python -m scripts.run_all                           # fast functional suites (HC/ACO)
python -m scripts.run_all --tier stress --models opp_hc_2 --stress-timeout-minutes 1
```

`run_all` never writes result CSVs (it sets `WRITE_RESULTS_CSV=0` for the runs); use
`python -m tests.run_suite <model> <tier>` with `WRITE_RESULTS_CSV=1` to produce data for `analysis/`.

If tests are added or removed on purpose, refresh the baseline with
`python -m scripts.run_all --update-baseline` and commit `baseline_counts.json`.
