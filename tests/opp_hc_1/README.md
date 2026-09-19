# OPP Hill Climbing V3 Tests

Test suite for the Hill Climbing heuristic solver for OPP V3.

## Structure

```
tests/opp_hc_1/
├── tests/
│   └── normal/
│       ├── test_opp_hc_v3_model_1.py   # HC Test 1: Basic 2 orders, 2 batches
│       ├── test_opp_hc_v3_model_2.py   # HC Test 2: Medium 2 orders, 2 aisles
│       ├── test_opp_hc_v3_model_3.py   # HC Test 3: Single picking point per order
│       ├── test_opp_hc_v3_model_4.py   # HC Test 4: Same aisle, different batches
│       └── test_opp_hc_v3_model_5.py   # HC Test 5: Different weights variant
```

Note: this doc predates later renames elsewhere in `tests/opp_hc_1/` (actual
filenames/counts may no longer match the list above exactly) -- left as-is,
out of scope for this pass, which only touched the scenario/runner
references below.

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
python -m tests.run_suite opp_hc_1 normal
```

### Run individual test:
```bash
python -m unittest tests.opp_hill_climbing.functional.test_opp_hc_v3_model_1
```

### Run specific test method:
```bash
python -m unittest tests.opp_hill_climbing.functional.test_opp_hc_v3_model_1.TestOPPHillClimbingV3Model1.test_basic_two_orders_capacity_limit
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

Tests reuse scenario definitions from `tests/shared_scenarios/normal/`
(centralized 2026-09-17; previously `tests/opp_v3/scenarios/normal/`):
- `scenario_01`: Basic 2-order setup
- `scenario_02`: 2-aisle warehouse setup

This ensures test inputs are identical between exact and heuristic solvers.
