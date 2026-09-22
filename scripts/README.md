# Repo scripts

Run from the repository root with `python -m scripts.<name>`.

| Script | What it does |
| --- | --- |
| `check_repo` | Consistency checks in seconds: every module imports, `family_case`/`migrated_case` targets exist, test files are `test_case_<NN\|slug>.py` with continuous numbering, no leftover directories or removed module paths. `--skip-imports` skips the (slower) import sweep. Exit code 1 on any failure. |
| `run_all` | Runs the suites of every model and compares them with `baseline_counts.json` (test counts on `main` before the 2026-09 reorganization, plus known failures). `--collect-only` only counts tests (seconds); `--profile fast` (default) = HC/ACO functional suites, `--profile full` = every model (`opp_v1`..`opp_v5` use SCIP/zimpl and are slow); `--tier stress` runs stress suites with a per-test cap (`--stress-timeout-minutes`, timeouts are reported, not failures). `--json` writes a machine-readable report. |
| `make_stress_smoke` | Rebuilds `stress_smoke.json`: the stress tests that finished OK in <= 15 s in the latest recorded runs (matched by method name, like `analysis/`). `run_all --tier stress --smoke` runs only those. |
| `new_family_tests` | Writes the one-line `family_case` test files of a new model family from an existing base family (e.g. `opp_hc_5` on top of `opp_hc_2`). See its docstring for the command. |

Typical uses:

```bash
python -m scripts.check_repo                        # after moving/renaming anything
python -m scripts.run_all --collect-only --profile full --tier all   # nothing lost or duplicated?
python -m scripts.run_all                           # fast functional suites (HC/ACO)
python -m scripts.run_all --tier stress --models opp_hc_2 --stress-timeout-minutes 1
```

## CI

`.github/workflows/ci.yml` runs on every pull request (a few minutes):

- `check_repo`, and `run_all --collect-only --profile full --tier all` (every suite still has the test count it had on `main` before the reorganization; Python 3.12 and 3.13).
- the functional suites of the HC/ACO models (`opp_hc_1..4`, `opp_aco_1..4`), retrying a failing suite once (ACO tests without a `Seed` are stochastic; a suite that needs the retry is flagged as flaky).
- the fast stress subset (`--smoke`), with a 60 s cap per test.

`.github/workflows/nightly.yml` (daily, or by hand from the Actions tab): every stress test of the HC/ACO models with a per-test cap (a test that reaches it is reported as a timeout, not a failure) and the functional suites of `opp_v1..v3` (SCIP only). `opp_v4`/`opp_v5` are never executed in CI: they need the `zimpl` binary, which the runner does not have (their test counts are still checked).

`run_all` never writes result CSVs (it sets `WRITE_RESULTS_CSV=0` for the runs); use
`python -m tests.run_suite <model> <tier>` with `WRITE_RESULTS_CSV=1` to produce data for `analysis/`.

If tests are added or removed on purpose, refresh the baseline with
`python -m scripts.run_all --update-baseline` and commit `baseline_counts.json`.
