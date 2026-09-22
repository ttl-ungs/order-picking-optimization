# OPP Hill Climbing V4 Tests (opp_hc_2)

Test suite for the Hill Climbing heuristic solver `models.opp_hc_2` - the
picker-parallelization equivalent of `opp_model_v4.zpl`. Batches are still
routed the same way as in `opp_hc_1` (v3), but batches can now be assigned to
different pickers (X_pb) so work is parallelized.

## Structure

```
tests/opp_hc_2/
├── functional/
│   └── test_case_NN.py      # One file per test case
├── stress/
│   └── test_case_NN.py
└── opp_hc_2_test_case.py    # Base assertions for this model
```

Scenario fixtures live in `tests/shared_scenarios/` (shared across models, see
its module docstrings), not under `tests/opp_hc_2/` -- this model has no
scenario files of its own.

## Running Tests

Run via the shared entry point, `tests/run_suite.py` (replaces every model's
own `execute_tests.py`/`execute_stress_tests.py`):

### Run all normal tests:
```bash
python -m tests.run_suite opp_hc_2 functional
```

### Run all stress tests (or a single numbered one):
```bash
python -m tests.run_suite opp_hc_2 stress
python -m tests.run_suite opp_hc_2 stress --id 05   # only test_case_05.py
```

### Run individual test:
```bash
python -m unittest tests.opp_hc_2.functional.test_case_01
```

## Test Expectations

Each test:
- Verifies Hill Climbing produces a feasible solution
- Validates output graph structure (routes) matches expectations
- Checks all routing constraints are satisfied
- Where a scenario names multiple pickers, verifies batches are distributed
  across pickers (X_pb) and that batches on the same picker never overlap in
  time (mirrors the ZPL model's non-overlap and unique-assignment constraints)

**Note:** Objective values may differ from the exact solver (heuristic vs.
exact), but graph topology, constraint satisfaction, and solution status
("optimal"/"feasible") must hold.

## Reused Scenarios

All scenario fixtures live in `tests/shared_scenarios/` and are shared across the `opp_v3`,
`opp_hc_1`, `opp_hc_2`, `opp_aco_*` suites so inputs stay comparable across solvers
(fixtures with a `_vN` suffix belong to one specific model).
