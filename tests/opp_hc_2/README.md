# OPP Hill Climbing V4 Tests (opp_hc_2)

Test suite for the Hill Climbing heuristic solver `models.opp_hc_2` - the
picker-parallelization equivalent of `opp_model_v4.zpl`. Batches are still
routed the same way as in `opp_hc` (v3), but batches can now be assigned to
different pickers (X_pb) so work is parallelized.

## Structure

```
tests/opp_hc_2/
├── execute_tests.py            # Main test runner (normal suite)
├── execute_stress_tests.py     # Stress suite runner
├── tests/
│   ├── normal/
│   │   └── test_opp_hc_2_model_NN.py   # One file per test case
│   └── stress/
│       └── test_opp_hc_2_model_NN.py
└── scenarios/                  # (Mostly reuses opp_v3/opp_hc scenario fixtures)
```

## Running Tests

### Run all normal tests:
```bash
python tests/opp_hc_2/execute_tests.py
```

### Run all stress tests (or a single numbered one):
```bash
python tests/opp_hc_2/execute_stress_tests.py
python tests/opp_hc_2/execute_stress_tests.py 05   # only test_opp_hc_2_model_05.py
```

### Run individual test:
```bash
python -m unittest tests.opp_hc_2.tests.normal.test_opp_hc_2_model_01
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
shared across the `opp`, `opp_v2`, `opp_v3`, `opp_hc` and `opp_hc_2` suites so
inputs stay comparable across solvers. A few multi-picker scenario fixtures
(e.g. `six_missions_three_pickers_grid_graph`, `three_missions_two_pickers_grid_graph`)
live under `tests/opp_hc_2/scenarios/` and are used by the picker-aware tests.
