**Overview**
This document contains fast tests. Graph references map to the respective configurations (Graph Catalog omitted). 

**Test Cases**
| ID | Name | Key | Description | Orders | Locations | Lots | Pickers | LotsFeasible | Expected | Obtained | Status | Time | Notes | Graph |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | test_two_orders_two_aisles_one_picking_point_per_order | Locacion | Ruta desde depósito | - | - | - | - | - | Feasible | False (no inicia en L1) | Fail | 0.0006s | No inicia en depot | - |
| 4 | test_two_orders_two_aisles_using_one_aisle | Locacion | Ruta desde depósito | - | - | - | - | - | Feasible | False (no inicia en L1) | Fail | 0.0005s | No inicia en depot | - |
| 5 | test_basic_two_orders_with_different_weights | Basico | Diferentes pesos | - | - | - | - | - | Feasible | Feasible | Pass | 0.0004s | - | - |
| 6 | test_two_orders_two_locations | Locacion | Rutas esperadas | 2 | 4 | 1 | 1 | 0 | Feasible | Feasible | Pass | 0.0005s | Grafo coincide | - |
| 7 | test_two_orders_two_locations_two_missions | Locacion | Múltiples misiones | 2 | 4 | 2 | 1 | 0 | Feasible | Feasible | Pass | 0.0007s | Grafo coincide | - |
| 8 | test_four_orders_two_locations_two_missions | Locacion | Cuatro órdenes | 4 | 5 | 2 | 1 | 0 | Feasible | Feasible | Pass | 0.0005s | Grafo coincide | - |
| 9 | test_twelve_orders_six_missions_three_pickers... | Tiempos | Infeasible esperado | 12 | 16 | 6 | 3 | 0 | Infeasible | Feasible | Fail | 0.0017s | El modelo encontró solución errónea | - |
| 15 | test_3_orders_1_mission_1_picker | Camino | Grafo esperado | 3 | 16 | 1 | 1 | 0 | Feasible | Mismatch | Fail | - | Error de aserción en grafos | - |
| 18 | test_detour_single_mission_route | Camino | Grafo sin ciclos | 5 | 8 | 1 | 1 | 1 | Feasible | Disconnected en L1 | Fail | - | Ruta desconectada | - |
| 20 | test_grid_batch_infeasible_order_size | Capacidad | Tamaño inválido | - | - | - | - | - | Infeasible | Optimal | Fail | - | Falla restricción capacidad | - |
| 20 | test_grid_order_size_bigger_than_cart_infeasible| Capacidad | Tamaño excede | - | - | - | - | - | Infeasible | Optimal | Fail | - | Falla restricción capacidad | - |
| 21 | test_bridge_disconnected_required_location | Conexión | Locación aislada | 12 | 12 | 4 | 2 | 4 | Infeasible | Optimal | Fail | - | Grafo no detectó desconexión | - |
| 22/23| test_tardiness_when_batch_finishes_after_due_date| Tardanza | due_date = 0 | 1 | 16 | 1 | 1 | 1 | ta > 0, ea = 0 | ta > 0, ea = 0 | Pass | 0.0373s | SCIP optimal | - |
| 24 | test_due_dates_tight_vs_relaxed | Tardanza | Ajuste de fechas | - | - | - | - | - | Feasible | Feasible | Pass | 0.0074s | - | - |
| 25 | test_one_empty_batch_allowed | Edge | Lote vacío | - | - | - | - | - | Feasible | Feasible | Pass | 0.0010s | - | - |
| 26 | test_fractional_and_zero_capacities_feasible | Capacidad | Fracciones/Cero | - | - | - | - | - | Feasible | Feasible | Pass | 0.0006s | - | - |
| 26 | test_fractional_and_zero_capacities_infeasible | Capacidad | Fracciones/Cero | - | - | - | - | - | Infeasible | Optimal | Fail | 0.0008s | Solución encontrada errónea | - |
| 27 | test_order_assigned_to_multiple_batches_infeasible| Lotes | Múltiples asign | - | - | - | - | - | Infeasible | Optimal | Fail | 0.0006s | Solución encontrada errónea | - |
| 28 | test_single_order_exceeds_vehicle | Capacidad | Orden excede veh. | - | - | - | - | - | Infeasible | Optimal | Fail | 0.0003s | Solución encontrada errónea | - |
| 29 | test_service_time_mixed / one / zero | Tiempos | Service time var. | - | - | - | - | - | Feasible | Feasible | Pass | ~0.0005s| - | - |
| 30 | test_depot_and_final_ignored_in_service_time | Edge | Tiempos depot/fin | - | - | - | - | - | Feasible | AttributeError | Fail | - | 'NoneType' object has no attribute 'items' | - |
| 30 | test_large_and_fractional_s | Edge | Tiempos frac. | - | - | - | - | - | Feasible | AttributeError | Fail | - | 'NoneType' object has no attribute 'items' | - |
| 30 | test_missing_s_uses_default_zero | Edge | Tiempos default | - | - | - | - | - | Feasible | AttributeError | Fail | - | 'NoneType' object has no attribute 'items' | - |
| 30 | test_negative_s_values_do_not_crash | Edge | Tiempos neg. | - | - | - | - | - | Feasible | AttributeError | Fail | - | 'NoneType' object has no attribute 'items' | - |
| 30 | test_non_dict_s_values | Edge | Tipo de dato | - | - | - | - | - | Feasible | AttributeError | Fail | - | 'NoneType' object has no attribute 'items' | - |
| 30 | test_partial_s_dictionary | Edge | Dict parcial | - | - | - | - | - | Feasible | AttributeError | Fail | - | 'NoneType' object has no attribute 'items' | - |