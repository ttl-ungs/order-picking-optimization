**Overview**
This document contains test cases for the OPP Hill Climbing heuristic model. The tests verify that the hill climbing implementation produces valid solutions for the same input scenarios as the linear model (OPP v3).

## Test Execution Summary (Latest Run)

- **Total Tests**: 46
- **Passed**: 17 ✅
- **Failed**: 14 ❌
- **Errors**: 15 🔴
- **Pass Rate**: 36.96%

---

## Test Results by Status

### ✅ PASSING TESTS (17/46)

#### Basic Tests (1-5)
- `test_opp_hc_model_1`: Basic. Status: **PASS** | Objective: 1510.0
- `test_opp_hc_model_2`: Two orders, two aisles. Status: **PASS** | Objective: 1510.0
- `test_opp_hc_model_5`: Extended complex scenario. Status: **PASS** | Objective: 89.55

#### Extended Scenarios (6-8)
- `test_opp_hc_model_6`: 4 vertex, 2 orders, 1 batch. Status: **PASS** | Objective: 1833.0
  - Route: L1 -> L3 -> L2 -> L4 ✓ Matches expected
- `test_opp_hc_model_7`: Two orders, two locations, two missions. Status: **PASS** | Objective: 3013.5
  - Routes: L1 -> L2 -> L4, L1 -> L3 -> L4 ✓ Matches expected
- `test_opp_hc_model_8`: Four orders, multi-location missions. Status: **PASS** | Objective: 6999.0
  - Routes: L1 -> L3 -> L2 -> L5, L1 -> L3 -> L4 -> L5 ✓ Matches expected

#### Tardiness/Earliness Tests (22-23)
- `test_opp_hc_model_22_23.test_tardiness_when_batch_finishes_after_due_date`: **PASS**
  - Due date: 0, Completion: 14 | Tardiness: 14.0 ✓
- `test_opp_hc_model_22_23.test_earliness_when_batch_finishes_before_due_date`: **PASS**
  - Due date: 10000, Completion: 14 | Earliness: 9986.0 ✓

#### Service Time Tests (29)
- `test_opp_hc_model_29.test_service_time_zero`: **PASS** | Objective: 753.0
- `test_opp_hc_model_29.test_service_time_one`: **PASS** | Objective: 846.0
- `test_opp_hc_model_29.test_service_time_mixed`: **PASS** | Objective: 871.5

---

### ❌ FAILED TESTS (14/46)

- `test_opp_hc_model_3`: Route does not start from depot. Feasibility issue.
- `test_opp_hc_model_4`: Route should start from depot L1. Failed to generate feasible route.
- `test_opp_hc_model_9`: Expected infeasible for 12 orders/6 missions. Returned optimal.
- `test_opp_hc_model_15`: Output graph mismatch. Graph comparison failed.
- `test_opp_hc_model_18`: Route disconnected at L1. Graph connectivity validation failed.
- `test_opp_hc_model_20.test_grid_order_size_bigger_than_cart_infeasible`: Expected infeasible, got optimal. Capacity check failed.
- `test_opp_hc_model_20.test_grid_batch_infeasible_order_size`: Expected infeasible, got optimal.
- `test_opp_hc_model_21.test_bridge_disconnected_required_location`: Expected infeasible, got optimal.
- `test_opp_hc_model_30.test_missing_s_uses_default_zero`: AttributeError on params.Bn = None
- `test_opp_hc_model_30.test_partial_s_dictionary`: AttributeError on params.Bn = None
- `test_opp_hc_model_30.test_non_dict_s_values`: AttributeError on params.Bn = None
- `test_opp_hc_model_30.test_large_and_fractional_s`: AttributeError on params.Bn = None
- `test_opp_hc_model_30.test_negative_s_values_do_not_crash`: AttributeError on params.Bn = None
- `test_opp_hc_model_30.test_depot_and_final_ignored_in_service_time`: AttributeError on params.Bn = None

---

### 🔴 ERROR TESTS (15/46)

**Missing model.model attribute** (Tests expect SCIP solver object):
- `test_opp_hc_model_19`: test_longer_single_mission_penalties
- `test_opp_hc_model_20`: test_grid_multi_location_orders, test_grid_penalties_due_date, test_grid_penalties_order_size_equal_to_cart, test_grid_shared_locations_across_batches
- `test_opp_hc_model_21`: test_bridge_earliness_order_size, test_bridge_shared_locations_across_batches, test_bridge_tardiness_beta_picking

**Missing imports** (OutputHandler or OPPModelV3):
- `test_opp_hc_model_24`: test_due_dates_tight_vs_relaxed (NameError: OPPModelV3)
- `test_opp_hc_model_25`: test_one_empty_batch_allowed (NameError: OutputHandler)
- `test_opp_hc_model_26`: test_fractional_and_zero_capacities_feasible, test_fractional_and_zero_capacities_infeasible
- `test_opp_hc_model_27`: test_order_assigned_to_multiple_batches_infeasible, test_order_assigned_to_single_batch_feasible
- `test_opp_hc_model_28`: test_single_order_exceeds_vehicle

---

## Key Issues Identified

### 🔴 Critical Issues

1. **Service Time Tests (Model 30)**: All crash with `AttributeError: 'NoneType' object has no attribute 'items'`
   - Root cause: params.Bn = None in these tests
   - Fix needed: Add null-safety check in _extract_batch_assignments()

2. **SCIP Model Access**: 8 tests try to access model.model (SCIP object)
   - Root cause: Hill climbing doesn't use SCIP, tests adapted directly from opp_v3
   - Fix needed: Refactor tests to not assume SCIP solver

3. **Missing Imports**: 7 tests have import errors
   - Root cause: Incorrect imports when copying from opp_v3
   - Fix needed: Verify all imports are correct

### 🟡 Medium Issues

4. **Capacity Constraint Detection**: 3 tests expect infeasibility but get optimal
   - Models: 20, 21
   - Issue: Hill climbing doesn't validate capacity constraints as strictly
   - Tests: Order size > vehicle capacity should be infeasible

5. **Route Generation Failures**: Multiple batches sometimes fail
   - Warnings: "Could not generate feasible route for batch X"
   - Affects: Models 3, 4, 9, 21
   - Issue: Nearest neighbor heuristic fails for complex graphs

6. **Graph Validation**: 3 tests have graph comparison mismatches
   - Models: 15, 18
   - Issue: Output route differs from expected

---

## Notes

- Hill climbing successfully solves basic and moderate scenarios (36.96% pass rate)
- OutputHandler properly integrated and displays results
- Main limitation: Heuristic is less strict on infeasibility detection than SCIP solver
- Test suite needs adjustment: Many tests designed specifically for SCIP solver features

