**Overview**
This document mirrors the "test_opp_v3" sheet in [tests/opp_v3/Test cases.xlsx](tests/opp_v2/Test%20cases.xlsx). Graph references in the table map to the Graph Catalog below; only rows marked "Ver Grafo" in the sheet receive a graph. Text is ASCII-transliterated from the original.

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
