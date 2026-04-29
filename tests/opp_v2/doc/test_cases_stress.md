**Overview**
This document mirrors the "test_opp_v2" sheet in [tests/opp_v2/Test cases.xlsx](tests/opp_v2/Test%20cases.xlsx). It contains only stress tests. The graph catalog is maintained in test_cases_normal.md.

**Test Cases**
| ID | Name | Key | Description | Orders | Locations | Lots | Pickers | LotsFeasible | Expected | Obtained | Status | Time | Notes | Graph |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 12 | test_100_locations | Estres | Similar al test 9 | 12 | 10x10 | 6 | 3 | 0 | Feasible | Feasible | Pass | 4 segundos | - | - |
| 13 | test_400_locations | Estres | Similar al test 9 | 12 | 20x20 | 6 | 3 | 0 | Feasible | Feasible | Pass | 100 segundos (1.6 minutos) | - | - |
| 14 | test_625_locations | Estres | Similar al test 9 | 12 | 25x25 | 6 | 3 | 0 | Feasible | Feasible | Pass | 320 segundos (5.3 minutos) | - | - |
| 24 | test_4_orders_per_batch | Estres | Cada picker tiene un lote. Cada lote tiene 4 ordenes. Grafo 10x10. | 100 | 10x10 | 25 | 25 | - | Feasible | Feasible | Pass |  +20 minutos (no termine de ejecutarlo) | - | - |
| 25 | test_10_orders_per_batch | Estres | Cada picker tiene un lote. Cada lote tiene 10 ordenes. Grafo 10x10. | 100 | 10x10 | 10 | 10 | - | Feasible | Feasible | Pass | 2 minutos | - | - |
| 25 | test_4_orders_per_batch_10_pickers | Estres | - | 100 | 10x10 | 25 | 10 | - | Feasible | Feasible | Pass |  +20 minutos (no termine de ejecutarlo) | - | - |
| 25 | test_10_orders_per_batch_25_pickers | Estres | - | 100 | 10x10 | 10 | 25 | - | Feasible | Feasible | Pass | 5 minutos | En conclusion: la cantidad de lotes impacta mucho en el resultado, puede que hasta mas que la cantidad de ordenes. Idea: testear 25 lotes con 25 o 50 ordenes, a ver que tanto baja el tiempo de ejecucion | - |
