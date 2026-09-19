# OPP Hill Climbing V4 Tests (opp_hc_2)

Test suite for the Hill Climbing heuristic solver `models.opp_hc_2` - the
picker-parallelization equivalent of `opp_model_v4.zpl`. Batches are still
routed the same way as in `opp_hc_1` (v3), but batches can now be assigned to
different pickers (X_pb) so work is parallelized.

## Structure

```
tests/opp_hc_2/
├── tests/
│   ├── normal/
│   │   └── test_opp_hc_2_model_NN.py   # One file per test case
│   └── stress/
│       └── test_opp_hc_2_model_NN.py
```

Scenario fixtures live in `tests/shared_scenarios/` (shared across models, see
its module docstrings), not under `tests/opp_hc_2/` -- this model has no
scenario files of its own.

## Running Tests

Run via the shared entry point, `tests/run_suite.py` (replaces every model's
own `execute_tests.py`/`execute_stress_tests.py`):

### Run all normal tests:
```bash
python -m tests.run_suite opp_hc_2 normal
```

### Run all stress tests (or a single numbered one):
```bash
python -m tests.run_suite opp_hc_2 stress
python -m tests.run_suite opp_hc_2 stress --id 05   # only test_opp_hc_2_model_05.py
```

### Run individual test:
```bash
python -m unittest tests.opp_hc_2.functional.test_opp_hc_2_model_01
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

Most tests reuse scenario fixtures from `tests/opp_v3/scenarios/`, which are
shared across the `opp_v1`, `opp_v2`, `opp_v3`, `opp_hc_1` and `opp_hc_2` suites so
inputs stay comparable across solvers. A few multi-picker scenario fixtures
(e.g. `six_missions_three_pickers_grid_graph`, `three_missions_two_pickers_grid_graph`)
live under `tests/opp_hc_2/scenarios/` and are used by the picker-aware tests.
