# Repo scripts

Run from the repository root with `python -m scripts.<name>`.

| Script | What it does |
| --- | --- |
| `check_repo` | Consistency checks in seconds: every module imports, test files are `test_case_<NN\|slug>.py`, the shared cases are numbered continuously, no leftover directories or removed module paths, `results/` has the expected shape. `--skip-imports` skips the (slower) import sweep. Exit code 1 on any failure. |
| `run_all` | Runs the suites of the four models and compares them with `baseline_counts.json` (test counts per suite). `--collect-only` only counts tests (seconds); `--profile fast` (default) = the OPP-HC/OPP-ACO functional suites, `--profile full` = every model (the exact ones use SCIP/zimpl and are slow); `--tier stress` runs stress suites with a per-test cap (`--stress-timeout-minutes`, timeouts are reported, not failures). `--json` writes a machine-readable report. |
| `make_stress_smoke` | Rebuilds `stress_smoke.json`: the stress tests that finished OK in <= 15 s in the latest recorded runs (matched by method name, like `analysis/`). `run_all --tier stress --smoke` runs only those. |

Typical uses:

```bash
python -m scripts.check_repo                        # after moving/renaming anything
python -m scripts.run_all --collect-only --profile full --tier all   # nothing lost or duplicated?
python -m scripts.run_all                           # fast functional suites (OPP-HC, OPP-ACO)
python -m scripts.run_all --tier stress --models opp_hc --stress-timeout-minutes 1
```

## CI

`.github/workflows/ci.yml` runs on every pull request (a few minutes):

- `check_repo`, and `run_all --collect-only --profile full --tier all` (every suite has the test count of `baseline_counts.json`; Python 3.12 and 3.13).
- the functional suites of OPP-HC and OPP-ACO, retrying a failing suite once (ACO tests without a `Seed` are stochastic; a suite that needs the retry is flagged as flaky).
- the fast stress subset (`--smoke`), with a 60 s cap per test.

`.github/workflows/nightly.yml` (daily, or by hand from the Actions tab): every stress test of OPP-HC and OPP-ACO with a per-test cap (a test that reaches it is reported as a timeout, not a failure), and the functional suites of OPP-Mono and OPP-Split in its `exact-zimpl` job, which installs `zimpl` from conda-forge. Their stress suites never run in CI (most tests hit the cap). `ci.yml` has no `zimpl`, so there the exact models are only collected (test counts).

`run_all` never writes result CSVs (it sets `WRITE_RESULTS_CSV=0` for the runs); use
`python -m tests.run_suite <model> <tier>` with `WRITE_RESULTS_CSV=1` to produce data for `analysis/`.

If tests are added or removed on purpose, refresh the baseline with
`python -m scripts.run_all --update-baseline` and commit `baseline_counts.json`.
