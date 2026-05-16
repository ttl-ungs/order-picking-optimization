**Overview**                                                            
This document contains only stress tests. The graph catalog is maintained in test_cases_normal.md.

**Test Cases**
| ID | Name | Key | Description | Orders | Locations | Lots | Pickers | LotsFeasible | Expected | Obtained | Status | Time | Notes | Graph |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | test_100_locations | Estres | 12 orders, 6 batches on 10x10 grid. | 12 | 10x10 | 6 | - | 0 | Feasible | Feasible | Pass | 3.14 s | - | - |
| 2 | test_400_locations | Estres | 12 orders, 6 batches on 20x20 grid. | 12 | 20x20 | 6 | - | 0 | Feasible | Feasible | Pass | 58.34 s | - | - |
| 3 | test_625_locations | Estres | 12 orders, 6 batches on 25x25 grid. | 12 | 25x25 | 6 | - | 0 | Feasible | Feasible | Pass | 264.04 s | - | - |
| 4 | test_4_orders_per_batch | Estres | 4 orders per batch. 25 batches, 100 orders. 10x10 grid. | 100 | 10x10 | 25 | - | - | Feasible | Timeout | Timeout | 300.00 s | Stopped at 5 min limit. | - |
| 5 | test_10_orders_per_batch | Estres | 10 orders per batch. 10 batches, 100 orders. 10x10 grid. | 100 | 10x10 | 10 | - | - | Feasible | Feasible | Pass | 109.45 s | - | - |
| 6 | test_empty_batches | Estres | Empty batches. 50 batches, 25 orders. 10x10 grid. | 25 | 10x10 | 50 | - | - | Feasible | Feasible | Pass | 33.64 s | - | - |
| 7 | test_multi_location_orders | Estres | Multi-location orders. 30 orders, 10 batches. 10x10 grid. | 30 | 10x10 | 10 | - | - | Feasible | Feasible | Pass | 7.25 s | - | - |
| 8 | test_shared_hotspots | Estres | Shared hot-spot locations. 30 orders, 10 batches. 10x10 grid. | 30 | 10x10 | 10 | - | - | Feasible | Feasible | Pass | 5.85 s | - | - |
| 9 | test_infeasible_capacity | Estres | Infeasible capacity. 10 orders, 2 batches. 4x4 grid. | 10 | 4x4 | 2 | - | - | Infeasible | Infeasible | Pass | 0.13 s | - | - |
| 10 | test_disconnected_graph | Estres | Disconnected multigrid. 6 orders, 12 batches. 5x5 + 3x3. | 6 | 5x5 + 3x3 | 12 | - | - | Infeasible | Infeasible | Pass | 0.75 s | - | - |
| 11 | test_25_orders_per_batch_30_batches_10x10 | Estres | 25 orders per batch. 30 batches, 750 orders. 10x10 grid. | 750 | 10x10 | 30 | - | - | Feasible | Timeout | Timeout | 300.00 s | Stopped at 5 min limit. | - |
| 12 | test_25_orders_per_batch_30_batches_25x25 | Estres | 25 orders per batch. 30 batches, 750 orders. 25x25 grid. | 750 | 25x25 | 30 | - | - | Feasible | Timeout | Timeout | 300.00 s | Stopped at 5 min limit. | - |
| 13 | test_25_orders_per_batch_30_batches_100x100 | Estres | 25 orders per batch. 30 batches, 750 orders. 100x100 grid. | 750 | 100x100 | 30 | - | - | Feasible | Feasible | Pass | 0.12 s | - | - |
| 14 | test_30_orders_per_batch_20_batches_100x100 | Estres | 30 orders per batch. 20 batches, 600 orders. 100x100 grid. | 600 | 100x100 | 20 | - | - | Feasible | Feasible | Pass | 0.10 s | - | - |
| 15 | test_25_orders_per_batch_30_batches_double_50x50 | Estres | 25 orders per batch. 30 batches, 750 orders. Two 50x50 grids with connectors. | 750 | 50x50 + 50x50 | 30 | - | - | Feasible | Feasible | Pass | 0.10 s | - | - |
| 16 | test_20_orders_per_batch_40_batches_double_50x50 | Estres | 20 orders per batch. 40 batches, 800 orders. Two 50x50 grids with connectors. | 800 | 50x50 + 50x50 | 40 | - | - | Feasible | Feasible | Pass | 0.09 s | - | - |
