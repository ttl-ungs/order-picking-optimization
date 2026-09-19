# OPP Hill Climbing V3 Tests

Test suite for the Hill Climbing heuristic solver for OPP V3.

## Structure

```
tests/opp_hc_1/
├── functional/
│   ├── test_case_01.py   # HC Test 1: Basic 2 orders, 2 batches
│   ├── test_case_02.py   # HC Test 2: Medium 2 orders, 2 aisles
│   ├── test_case_03.py   # HC Test 3: Single picking point per order
│   ├── test_case_04.py   # HC Test 4: Same aisle, different batches
│   └── test_case_05.py   # HC Test 5: Different weights variant
└── stress/
```

Only the first five cases are listed; the suite has more (see `functional/`).

## Tests Overview

Each test is equivalent to a corresponding OPP V3 test but uses `OPPHillClimbingV3` instead of `OPPModelV3`.

| Test | Name | Scenario | Orders | Batches | Purpose |
|------|------|----------|--------|---------|---------|
| HC1 | Basic | scenario_1 | 2 | 2 | Test basic functionality |
| HC2 | Two Aisles | scenario_2 | 2 | 2 | Test multi-location routing |
| HC3 | Single Point | scenario_2 | 2 | 2 | Test single location per order |
| HC4 | One Aisle | scenario_2 | 2 | 2 | Test same aisle different batches |
| HC5 | Weight Variant | scenario_1 | 2 | 2 | Test different objective weights |

## Running Tests

### Run all tests:
```bash
python -m tests.run_suite opp_hc_1 functional
```

### Run individual test:
```bash
python -m unittest tests.opp_hc_1.functional.test_case_01
```

### Run specific test method:
```bash
python -m unittest tests.opp_hc_1.functional.test_case_01.TestOPPHillClimbingModel1.test_basic_two_orders_capacity_limit
```

## Test Expectations

Each test:
- ✅ Verifies Hill Climbing produces a feasible solution
- ✅ Validates output graph structure matches expected
- ✅ Checks all constraints are satisfied
- ✅ Ensures same interface as OPP V3

**Note:** Objective values may differ from exact solver (heuristic vs exact), but:
- Graph topology must match expected
- All constraints must be satisfied
- Solution status must be "optimal" or "feasible"

## Reused Scenarios

Tests reuse scenario definitions from `tests/shared_scenarios/functional/`
(centralized 2026-09-17; previously `tests/opp_v3/scenarios/normal/`):
- `scenario_01`: Basic 2-order setup
- `scenario_02`: 2-aisle warehouse setup

This ensures test inputs are identical between exact and heuristic solvers.
