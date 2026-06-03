**Overview**
This document contains test cases for the OPP Hill Climbing heuristic model. The tests verify that the hill climbing implementation produces valid solutions for the same input scenarios as the linear model (OPP v3).

**Graph Catalog**

**Test Cases**

### Tests 1-5 (Basic functionality)

- `test_opp_hc_model_1`: Basic. 4 vertex, 5 edges, 2 orders, 2 batches. Tests basic functionality of the Hill Climbing model.
- `test_opp_hc_model_2`: Two orders, two aisles. Tests handling of spatial layout with multiple orders.
- `test_opp_hc_model_3`: Two possible routes with batches. Tests multiple routing alternatives.
- `test_opp_hc_model_4`: Complex scenario with multiple batches.
- `test_opp_hc_model_5`: Extended complex scenario.

### Tests 6-30 (Extended scenarios)

- `test_opp_hc_model_6`: 4 vertex, 2 orders, 1 batch. Tests functionality when two orders are linked to two locations.
- `test_opp_hc_model_7`: Two orders, two locations, two missions. Tests multi-mission scenarios.
- `test_opp_hc_model_8`: Six missions, three pickers, grid graph. Tests large-scale scenarios with multiple pickers.
- `test_opp_hc_model_9`: Three missions, two pickers, grid graph. Tests medium-scale multi-picker scenarios.
- `test_opp_hc_model_10`: Single mission, one picker, grid graph. Tests simple grid-based scenarios.
- `test_opp_hc_model_15`: Branched single mission route. Tests complex routing with branches.
- `test_opp_hc_model_16`: Additional grid-based test scenario.
- `test_opp_hc_model_17`: Branched single mission route. Tests branching logic in routing.
- `test_opp_hc_model_18`: Detour single mission route. Tests detour handling and optimization.
- `test_opp_hc_model_19`: Longer single mission route. Tests longer distance scenarios.
- `test_opp_hc_model_20`: Grid 5x3 with two pickers and four batches. Tests structured grid scenarios.
- `test_opp_hc_model_21`: Additional batch assignment test.
- `test_opp_hc_model_22_23`: Combined test for two related scenarios.
- `test_opp_hc_model_24`: Capacity and batching test scenario.
- `test_opp_hc_model_25`: Complex batch assignment scenario.
- `test_opp_hc_model_26`: Mix of zero and fractional `cap_n` values to validate capacity handling. Contains two cases:
  - Infeasible: Vehicle capacity is insufficient for the assigned orders.
  - Feasible: Vehicle capacity is sufficient for the assigned orders.
- `test_opp_hc_model_27`: Behavior when assigning orders to batches. Contains two cases:
  - Infeasible: Order assigned to multiple batches, violating constraint.
  - Feasible: Orders uniquely assigned to separate batches.
- `test_opp_hc_model_28`: Additional order-batch assignment test.
- `test_opp_hc_model_29`: Service-time (`s[i]`) handling. Three cases exercising per-location service time values:
  - `s=0` for all vertices — baseline, expected feasible/optimal.
  - `s=1` for all vertices — uniform non-zero service time.
  - `s=mixed` fractional values per-vertex — varied results.
- `test_opp_hc_model_30`: Edge and robustness cases for `s` handling:
  - Missing `s` (params.s absent) — defaults to zero service times.
  - Partial `s` (only subset of vertices present) — missing entries treated as 0.
  - Non-dict `s` values — treated as missing.
  - Large/fractional `s` values — numeric stability check.
  - Depot/final included in `s` — these are ignored.
  - Negative `s` values — behavior validation.

**Notes**
All tests are adapted from the OPP v3 linear model tests to verify that the hill climbing heuristic produces valid feasible solutions for the same input scenarios.

