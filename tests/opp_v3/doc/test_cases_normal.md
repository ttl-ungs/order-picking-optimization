**Overview**
This documen contains fast tests. Graph references in the table map to the Graph Catalog below; only rows marked "Ver Grafo" in the sheet receive a graph.

**Graph Catalog**

**Test Cases**
   
### Additional normal tests added

- `test_opp_v3_model_extra_single_order_exceeds_vehicle`: single order with `cap_n` greater than `cap_vehicle` -> expected infeasible. Observed: infeasible.
- `test_opp_v3_model_extra_empty_batch`: medium grid with one intentionally empty batch among others -> expected feasible. Observed: feasible/optimal.
- `test_opp_v3_model_26`: mix of zero and fractional `cap_n` values to validate capacity handling. Contains two cases:
  - Infeasible: Vehicle capacity is insufficient for the assigned orders.
  - Feasible: Vehicle capacity is sufficient for the assigned orders.
- `test_opp_v3_model_27`: behavior when assigning orders to batches. Contains two cases:
  - Infeasible: Order assigned to multiple batches, violating constraint $\sum_{b} y_{nb} = 1$.
  - Feasible: Orders uniquely assigned to separate batches.
- `test_opp_v3_model_extra_due_dates_extreme`: compare behavior under very tight vs relaxed due dates (tardiness effects) -> expected feasible for relaxed, tight may be infeasible. Observed: relaxed feasible; tight run produced feasible/optimal in this instance.

### Service-time (`s[i]`) tests added

- `test_opp_v3_model_29`: three cases exercising per-location service time values:
  - `s=0` for all vertices — baseline, expected feasible/optimal. Observed: optimal.
  - `s=1` for all vertices — uniform non-zero service time. Observed: optimal.
  - `s=mixed` fractional values per-vertex — varied results but model solved. Observed: optimal/feasible.

- `test_opp_v3_model_30`: edge and robustness cases for `s` handling:
  - Missing `s` (params.s absent) — defaults to zero service times; model runs. Observed: solved.
  - Partial `s` (only subset of vertices present) — missing entries treated as 0. Observed: solved.
  - Non-dict `s` values (e.g., numeric, list) — treated as missing; model does not crash. Observed: solved.
  - Large/fractional `s` values — numeric stability check. Observed: solved.
  - Depot/final included in `s` — these are ignored by the service-time term. Observed: solved (execution times reflect only non-depot/non-final vertices).
  - Negative `s` values — model does not crash; behaviour currently accepted (may require validation). Observed: solved.

All added tests imported and executed; full run (9 tests) returned OK. See test modules for details and example runs.
