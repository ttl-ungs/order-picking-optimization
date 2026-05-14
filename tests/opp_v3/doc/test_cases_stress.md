**Overview**
This document mirrors the "test_opp_v3" sheet in [tests/opp_v3/Test cases.xlsx](tests/opp_v2/Test%20cases.xlsx). It contains only stress tests. The graph catalog is maintained in test_cases_normal.md.

**Test Cases**
| ID | Name | Key | Description | Orders | Locations | Lots | Pickers | LotsFeasible | Expected | Obtained | Status | Time | Notes | Graph |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | test_100_locations | Estres | 12 orders, 6 batches on 10x10 grid. | 12 | 10x10 | 6 | - | 0 | Feasible | Infeasible | Fail | 3.02 s | Infeasible in presolve. | - |
| 2 | test_400_locations | Estres | 12 orders, 6 batches on 20x20 grid. | 12 | 20x20 | 6 | - | 0 | Feasible | Infeasible | Fail | 59.19 s | Infeasible in presolve. | - |
| 3 | test_625_locations | Estres | 12 orders, 6 batches on 25x25 grid. | 12 | 25x25 | 6 | - | 0 | Feasible | Infeasible | Fail | 295.90 s | Infeasible in presolve. | - |
| 4 | test_4_orders_per_batch | Estres | 4 orders per batch. 25 batches, 100 orders. 10x10 grid. | 100 | 10x10 | 25 | - | - | Feasible | Timeout | Timeout | 300.01 s | Stopped at 5 min limit. | - |
| 5 | test_10_orders_per_batch | Estres | 10 orders per batch. 10 batches, 100 orders. 10x10 grid. | 100 | 10x10 | 10 | - | - | Feasible | Feasible | Pass | 128.64 s | - | - |
| 6 | test_empty_batches | Estres | Empty batches. 50 batches, 25 orders. 10x10 grid. | 25 | 10x10 | 50 | - | - | Feasible | Feasible | Pass | 44.82 s | - | - |
| 7 | test_multi_location_orders | Estres | Multi-location orders. 30 orders, 10 batches. 10x10 grid. | 30 | 10x10 | 10 | - | - | Feasible | Feasible | Pass | 9.27 s | - | - |
| 8 | test_shared_hotspots | Estres | Shared hot-spot locations. 30 orders, 10 batches. 10x10 grid. | 30 | 10x10 | 10 | - | - | Feasible | Feasible | Pass | 7.98 s | - | - |
| 9 | test_infeasible_capacity | Estres | Infeasible capacity. 10 orders, 2 batches. 4x4 grid. | 10 | 4x4 | 2 | - | - | Infeasible | Infeasible | Pass | 0.36 s | - | - |
| 10 | test_disconnected_graph | Estres | Disconnected multigrid. 6 orders, 12 batches. 5x5 + 3x3. | 6 | 5x5 + 3x3 | 12 | - | - | Infeasible | Infeasible | Pass | 1.35 s | - | - |
