# Tests

The four models (OPP-Split, OPP-Mono, OPP-HC, OPP-ACO) run the same cases: the 38 functional cases
and the 19 stress scenarios of the thesis.

## Structure

- `tests/functional_cases/` — `case_NN.py`, each functional case written once. A case builds an instance and solves it with `self.solve(...)` or `self.run_pipeline(...)`; it does not know which model runs it. Each test method carries its label in the docstring ("Case 24a"; letters follow the alphabetical order of the case's methods).
- `tests/stress_cases/` — `case_NN.py`, each stress scenario written once; it calls `self.assert_stress_pipeline(scenario)`.
- `tests/<model>/functional/` and `tests/<model>/stress/` — bind the model to the shared cases (`test_functional_cases.py`, `test_stress_cases.py`, using `bind_cases` and the model's adapter) and hold the tests of its own.
- The four models run the functional cases with the same scenarios and the same assertions; only the model changes. See [The heuristics on the functional cases](#the-heuristics-on-the-functional-cases).
- Tests of their own, beyond the shared cases: OPP-Split (`test_case_24b.py`, the pre-flight check that no picker can run a batch within the cold-chain limit, and `test_case_38.py`), OPP-Mono (`test_case_38.py`), OPP-HC (`test_case_invalid_speed_rejected.py`, case 36c) and OPP-ACO (`test_case_invalid_speed_rejected.py`, case 36c, and `test_case_unreachable_required_location.py`).
- `tests/shared_scenarios/` — graphs and scenarios shared by every model (`common/`, `functional/`, `stress/`).
- `tests/infra/` — `execution/` (runner, config), `cases/` (`OPPTestCase`, `ExactModelTestCase`, `HeuristicModelTestCase`, `binding.py`, `route_assertions`), `factories/` (the Split's functional instances, scenario adapter, graphs) and `zimpl/` (helpers of the ZIMPL-based tests).
- `tests/run_suite.py` — single entry point to run a model's suite. Repo-wide checks and runs (`check_repo`, `run_all`) live in `scripts/`.

## The heuristics on the functional cases

The cases read the solution as the exact models' variables (`x_pb`, `c_pb`, `u_pb`, `c_b`, `r_b`,
`z_ijb`, `ta_n`, `ea_n`). The heuristics' adapters (`OPPTestCaseHC`, `OPPTestCaseACO`, on
`tests/infra/cases/heuristic_model_case.py`) solve the case's instance with the heuristic and return
its solution under those names, so the case runs unchanged.

- `solve()` takes the instance the case just wrote with `build_dat_files()`; `run_pipeline()` takes the scenario.
- Cases 06a, 06b and 37a check the completion time and the objective only on the exact models (`waits_voluntarily`): those values need the batch to wait until its due date, and the heuristics do not wait. The comment in each case says so.

`tests/shared_scenarios/functional/functional_instances.json` (exported from OPP-Split's runs with
`python -m tests.shared_scenarios.functional.export_functional_instances`, needs `zimpl` and SCIP) is
the Split's reference for the comparability registry, not a test input.

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
