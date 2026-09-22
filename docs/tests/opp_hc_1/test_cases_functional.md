**Overview**
This document contains tests for the OPP Hill Climbing heuristic model. Graph references in the table map to the Graph Catalog below; only rows marked "Ver Grafo" in the sheet receive a graph.

**Graph Catalog**

**Test Cases**

### Additional normal tests added

- `test_opp_hc_1_model_extra_single_order_exceeds_vehicle`: single order with `cap_n` greater than `cap_vehicle` -> expected infeasible; hill climbing finds solution despite capacity violation. Observed: feasible/optimal (heuristic is permissive).
- `test_opp_hc_1_model_extra_empty_batch`: medium grid with one intentionally empty batch among others -> expected feasible. Observed: feasible/optimal.
- `test_case_21`: mix of zero and fractional `cap_n` values to validate capacity handling. Contains two cases:
  - Infeasible: Vehicle capacity is insufficient for the assigned orders. Observed: optimal (heuristic permissive).
  - Feasible: Vehicle capacity is sufficient for the assigned orders. Observed: feasible/optimal.
- `test_case_22`: behavior when assigning orders to batches. Contains two cases:
  - Infeasible: Order assigned to multiple batches, violating constraint $\sum_{b} y_{nb} = 1$. Observed: optimal (heuristic permissive).
  - Feasible: Orders uniquely assigned to separate batches. Observed: feasible/optimal.
- `test_opp_hc_1_model_extra_due_dates_extreme`: compare behavior under very tight vs relaxed due dates (tardiness effects) -> expected feasible for relaxed, tight may be infeasible. Observed: both feasible (heuristic handles edge cases well).

### Service-time (`s[i]`) tests added

- `test_case_24`: three cases exercising per-location service time values:
  - `s=0` for all vertices — baseline, expected feasible/optimal. Observed: optimal.
  - `s=1` for all vertices — uniform non-zero service time. Observed: optimal.
  - `s=mixed` fractional values per-vertex — varied results but model solved. Observed: optimal/feasible.

- `test_case_25`: edge and robustness cases for `s` handling:
  - Missing `s` (params.s absent) — defaults to zero service times; currently crashes with AttributeError on params.Bn. Requires null-safety fix.
  - Partial `s` (only subset of vertices present) — missing entries treated as 0. Currently crashes with AttributeError on params.Bn. Requires null-safety fix.
  - Non-dict `s` values (e.g., numeric, list) — treated as missing. Currently crashes with AttributeError on params.Bn. Requires null-safety fix.
  - Large/fractional `s` values — numeric stability check. Currently crashes with AttributeError on params.Bn. Requires null-safety fix.
  - Depot/final included in `s` — these are ignored by the service-time term. Currently crashes with AttributeError on params.Bn. Requires null-safety fix.
  - Negative `s` values — model behavior under negative values. Currently crashes with AttributeError on params.Bn. Requires null-safety fix.

All 46 tests imported and executed; pass rate: 29/46 (63%). 6 tests fail due to AttributeError (params.Bn = None handling). 5 tests fail due to route generation issues. 5 tests fail due to infeasibility detection being too permissive (heuristic vs exact solver trade-off). See test modules for details.


