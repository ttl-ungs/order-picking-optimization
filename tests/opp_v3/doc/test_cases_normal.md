**Overview**
This document contains fast tests. Graph references map to the respective configurations (Graph Catalog omitted). 
*(Nota: Zona horaria establecida en Argentina UTC-3)*.

**Test Cases**
| ID | Name | Key | Description | Orders | Locations | Lots | Pickers | LotsFeasible | Expected | Obtained | Status | Time | Notes | Graph |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | test_two_possible_routes | Camino | El modelo elige entre rutas | - | - | - | - | - | Feasible | Feasible | Pass | 0.0229s | Obj: 144.0 | - |
| 4 | test_repeated_picking_locations | Camino | Rutas generan ciclo | - | - | - | - | - | Infeasible | Infeasible | Pass | 0.0120s | No permite ciclos | - |
| 5 | test_repeated_picking_locations_2 | Camino | Uso de comodín | - | - | - | - | - | Feasible | Feasible | Pass | 0.0111s | Obj: 69.0 | - |
| 6 | test_two_orders_two_locations | Locacion | Múltiples locaciones | 2 | 4 | 1 | 1 | 0 | Feasible | Feasible | Pass | 0.0098s | Grafo coincide | - |
| 7 | test_two_orders_two_locations_two_missions | Locacion | Múltiples misiones | 2 | 4 | 2 | 1 | 0 | Feasible | Feasible | Pass | 0.0075s | Grafo coincide | - |
| 8 | test_four_orders_two_locations_two_missions | Locacion | Cuatro órdenes | 4 | 5 | 2 | 1 | 0 | Feasible | Feasible | Pass | 0.0194s | Grafo coincide | - |
| 9 | test_twelve_orders_six_missions_three_pickers... | Tiempos | Infeasible esperado | 12 | 16 | 6 | 3 | 0 | Infeasible | Infeasible | Pass | 0.0893s | - | - |
| 28 | test_single_order_exceeds_vehicle | Capacidad | Orden excede veh. | - | - | - | - | - | Infeasible | Infeasible | Pass | 0.0616s | - | - |
| 29 | test_service_time_mixed / one / zero | Tiempos | Service time var. | - | - | - | - | - | Feasible | Feasible | Pass | ~0.0200s| Tiempos de servicio aplicados | - |
| 30 | test_depot_and_final_ignored_in_service_time | Edge | Tiempos depot/fin | - | - | - | - | - | Feasible | NotImplementedError | Fail | - | Error en `__mul__` (pyscipopt) | - |
| 30 | test_large_and_fractional_s | Edge | Tiempos frac. | - | - | - | - | - | Feasible | NotImplementedError | Fail | - | Error en `__mul__` (pyscipopt) | - |
| 30 | test_missing_s_uses_default_zero | Edge | Tiempos default | - | - | - | - | - | Feasible | NotImplementedError | Fail | - | Error en `__mul__` (pyscipopt) | - |
| 30 | test_negative_s_values_do_not_crash | Edge | Tiempos neg. | - | - | - | - | - | Feasible | NotImplementedError | Fail | - | Error en `__mul__` (pyscipopt) | - |
| 30 | test_non_dict_s_values | Edge | Tipo de dato | - | - | - | - | - | Feasible | NotImplementedError | Fail | - | Error en `__mul__` (pyscipopt) | - |
| 30 | test_partial_s_dictionary | Edge | Dict parcial | - | - | - | - | - | Feasible | NotImplementedError | Fail | - | Error en `__mul__` (pyscipopt) | - |