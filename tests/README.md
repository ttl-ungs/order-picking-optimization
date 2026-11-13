# Tests

The four models (OPP-Split, OPP-Mono, OPP-HC, OPP-ACO) run the same cases: the 38 functional cases
and the 19 stress scenarios of the thesis.

## Structure

- `tests/functional_cases/` — `case_NN.py`, each functional case written once. A case builds an instance and solves it with `self.solve(...)` or `self.run_pipeline(...)`; it does not know which model runs it. Each test method carries its label in the docstring ("Case 24a"; letters follow the alphabetical order of the case's methods).
- `tests/stress_cases/` — `case_NN.py`, each stress scenario written once; it calls `self.assert_stress_pipeline(scenario)`.
- `tests/<model>/functional/` and `tests/<model>/stress/` — bind the model to the shared cases (`test_functional_cases.py`, `test_stress_cases.py`, using `bind_cases` and the model's adapter) and hold the tests of its own.
- OPP-Split and OPP-Mono run the functional cases with their exact assertions (objective and routes). OPP-HC and OPP-ACO run the same instances through `test_functional_cases.py` (one test per instance of the functional cases, captured from OPP-Split's runs, with the same case class and test name as in the Split) and check the status against the Split's.
- Tests of their own, beyond the shared cases: OPP-Split (`test_case_24b.py`, the pre-flight check that no picker can run a batch within the cold-chain limit, and `test_case_38.py`), OPP-Mono (`test_case_38.py`), OPP-HC (`test_case_invalid_speed_rejected.py`, case 36c) and OPP-ACO (case 36c and `test_case_unreachable_required_location.py`).
- `tests/shared_scenarios/` — graphs and scenarios shared by every model (`common/`, `functional/`, `stress/`).
- `tests/infra/` — `execution/` (runner, config), `cases/` (`OPPTestCase`, `ExactModelTestCase`, `binding.py`, `route_assertions`), `factories/` (functional instances, scenario adapter, graphs) and `zimpl/` (helpers of the ZIMPL-based tests).
- `tests/run_suite.py` — single entry point to run a model's suite. Repo-wide checks and runs (`check_repo`, `run_all`) live in `scripts/`.

## Conventions for a case

- Isolate the term under test with the objective weights (for example `W_c = 0`, `W_pen = 1`, `W_e = 0`, `W_t = 1` for tardiness).
- Validate that routes visit every required location (`assert_route_covers_orders`, `assert_batch_routes_cover_locations`).
- For infeasible cases force one cause (duplicated location in a batch, vehicle capacity too low, disconnected graph) and assert the status `"infeasible"`.
- Use the helpers `OPPTestCase.normalize_due_dates`, `apply_weight_overrides` and `sum_vars_with_prefix`.
- Assertions are never relaxed to make a test pass.

## Execution

From the repository root:

```bash
python -m tests.run_suite opp_hc functional
python -m tests.run_suite opp_split functional --id 24
python -m unittest tests.opp_hc.functional.test_case_invalid_speed_rejected
```

Settings (per-test timeouts, whether to write result CSVs) come from a local `.env`; copy
`.env.example` to `.env` to change them. `.env` itself is not versioned.
