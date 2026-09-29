# Comparabilidad entre v5 y las heurísticas (aco_4, hc_4)

Este documento define **qué resultados de v5 (`opp_v5_2_split`, `opp_v5_1_mono`) y de las heurísticas (`opp_aco_4`, `opp_hc_4`) se pueden comparar**, y cuáles deben quedar afuera de cualquier tabla o gráfico comparativo.

La fuente de verdad es el registro `results/comparability/comparability_v5_vs_heuristics.csv`, que se genera con:

```
python -m analysis.comparability
```

Toda tabla o gráfico que compare v5 con las heurísticas debe filtrar por sus columnas `comparable_status` y `comparable_objective`, en lugar de decidir caso por caso. Las tablas de este documento son una foto del 2026-09-28; si cambian los tests, manda el CSV.

## Qué se compara y con qué

| Qué | Instancias de las heurísticas | Referencia de v5 |
|---|---|---|
| **Funcional** | `test_v5eq__<test de v5>[__<k>]` en `tests/opp_{aco,hc}_4/functional/test_case_v5_equivalence.py` | Estado y objetivo por instancia en `tests/shared_scenarios/functional/v5_equivalence_scenarios.json` |
| **Estrés** | `test_case_NN` en `tests/opp_{aco,hc}_4/stress/`, con la misma numeración y el mismo nombre de método que v5 | CSV de estrés de `opp_v5_2_split`, combinados por `analysis.load`: 04–19 con W_c = 27 y 01–03 de las corridas consolidadas |
| **Tiempo igual** | CSV de estrés de cada heurística | `results/equal_time/output_equal_time_<heurística>_*.csv`, donde v5 corre con el tiempo de la heurística como límite |

**Los demás tests funcionales de aco_4 y hc_4 no son comparables con v5, aunque compartan el nombre.** La mayoría envuelve tests de aco_2 y hc_2 que no definen pickers y corren con uno solo, mientras que el test de v5 del mismo nombre usa dos. Para comparar funcionales se usan solo las instancias `test_v5eq__*`.

## Cómo se garantiza que sean los mismos datos

- **Funcional.** `tests/shared_scenarios/functional/export_v5_equivalence_scenarios.py` corre la suite funcional de `opp_v5_2_split` y captura cada escenario en el momento en que v5 escribe sus archivos `.dat`. Guarda también el estado y el objetivo finales de v5.
  - Las heurísticas resuelven exactamente ese escenario con `tests/infra/factories/v5_scenario_adapter.py`.
  - Donde el escenario no define velocidades ni límite de frío, se completan con V_p = 1,0 y T_cold = 10⁹, igual que hace v5.
  - Hay que volver a correr el exportador si cambia un test o un escenario funcional de v5. Necesita zimpl y SCIP.
- **Estrés.** Los tests de las dos heurísticas llaman al mismo constructor de escenario, con los mismos argumentos, que los de v5. Se verificó para los 19 el 2026-09-28.

## Reglas de comparabilidad

Están implementadas en `tests/infra/factories/v5_equivalence.py` (`comparability`, `v5_waiting_batches`).

| Situación | ¿Estado comparable? | ¿Objetivo comparable? | Motivo |
|---|---|---|---|
| v5 no terminó (timeout) | No | No | No hay referencia |
| v5 fija la asignación batch→picker (`X_pb`) | No | No | Las heurísticas no admiten esa restricción. Hoy no hay ningún caso |
| v5 infeasible | **Sí** | No | No hay objetivo; sí se compara que la heurística también dé infeasible |
| v5 usa espera voluntaria | **Sí** | No | Ver abajo |
| v5 óptimo, sin espera | **Sí** | **Sí** | Mismos datos, mismo objetivo |

**Espera voluntaria.** En v5 la restricción es `v_pb >= T_exec_pb`, no una igualdad. Eso le permite reportar un batch como terminado más tarde de lo que termina físicamente, para reducir la earliness. Las heurísticas reportan tiempos reales y no pueden hacerlo, así que en esos casos el objetivo de v5 es menor por diseño del modelo, no por un mejor plan.
- **Cómo se detecta.** Sobre la solución de v5: un batch espera si su `v_pb` supera la finalización del batch anterior del mismo picker más su `T_exec_pb`.
- **Cuándo se cuenta.** Solo si la earliness tiene peso (`W_pen · W_e > 0`). Si no lo tiene, esperar no puede bajar el objetivo.
- **Verificación exacta del 2026-09-28.** En las 9 instancias marcadas, "rutas más cortas + espera óptima" reproduce exactamente el objetivo de v5. ACO, en esas mismas instancias, obtiene el mejor scheduling posible sin espera para sus rutas.

**Estrés.** No hay espera que descartar:
- En 04–19, W_c = 27 es mayor que las órdenes por batch, así que esperar nunca conviene.
- En 01–03, todas las órdenes llegan tarde, así que no hay earliness que recortar.

Los escenarios de estrés donde v5 hizo timeout no tienen referencia de objetivo. Se usan para comparar escala (la heurística resuelve y v5 no) y en el experimento de tiempo igual, no para calcular brechas.

## Resumen (2026-09-28)

| Parte | Comparables en estado y objetivo | Solo en estado | No comparables |
|---|---|---|---|
| Funcional (67 instancias + 2 tests sin instancia) | 45 | 21: 12 infeasibles y 9 con espera de v5 | 3: 1 timeout, 1 excluido y 1 que no llega al solver |
| Estrés (19 escenarios) | 9 | 0 | 10: v5 timeout |

### Funcional: instancias no comparables en objetivo

| Test de v5 | Instancia en aco_4/hc_4 | Estado de v5 | ¿Estado comparable? | Motivo |
|---|---|---|---|---|
| `test_basic_two_orders_capacity_limit` | `test_v5eq__test_basic_two_orders_capacity_limit` | optimal | Sí | v5 usa espera voluntaria en B1 |
| `test_two_possible_routes` | `test_v5eq__test_two_possible_routes` | optimal | Sí | v5 usa espera voluntaria en B1, B2 |
| `test_longer_single_mission_duplicate_location` | `test_v5eq__test_longer_single_mission_duplicate_location` | optimal | Sí | v5 usa espera voluntaria en B1 |
| `test_longer_single_mission_route` | `test_v5eq__test_longer_single_mission_route` | optimal | Sí | v5 usa espera voluntaria en B1 |
| `test_bridge_earliness_order_size` | `test_v5eq__test_bridge_earliness_order_size__1` | optimal | Sí | v5 usa espera voluntaria en B2, B4 |
| `test_bridge_earliness_order_size` | `test_v5eq__test_bridge_earliness_order_size__2` | optimal | Sí | v5 usa espera voluntaria en B1, B3 |
| `test_one_empty_batch_allowed` | `test_v5eq__test_one_empty_batch_allowed` | optimal | Sí | v5 usa espera voluntaria en B2, B3 |
| `test_order_assigned_to_single_batch_feasible` | `test_v5eq__test_order_assigned_to_single_batch_feasible` | optimal | Sí | v5 usa espera voluntaria en B1, B2 |
| `test_service_time_zero` | `test_v5eq__test_service_time_zero` | optimal | Sí | v5 usa espera voluntaria en B1 |
| `test_repeated_picking_locations` | `test_v5eq__test_repeated_picking_locations` | infeasible | Sí | Sin objetivo |
| `test_bridge_disconnected_required_location` | `test_v5eq__test_bridge_disconnected_required_location` | infeasible | Sí | Sin objetivo |
| `test_bridge_disconnected_required_location_with_capacities` | `test_v5eq__test_bridge_disconnected_required_location_with_capacities` | infeasible | Sí | Sin objetivo |
| `test_preflight_detects_when_no_picker_is_eligible` | `test_v5eq__test_preflight_detects_when_no_picker_is_eligible` | infeasible | Sí | Sin objetivo |
| `test_grid_batch_infeasible_order_size` | `test_v5eq__test_grid_batch_infeasible_order_size` | infeasible | Sí | Sin objetivo |
| `test_grid_order_size_bigger_than_cart_infeasible` | `test_v5eq__test_grid_order_size_bigger_than_cart_infeasible` | infeasible | Sí | Sin objetivo |
| `test_fractional_and_zero_capacities_infeasible` | `test_v5eq__test_fractional_and_zero_capacities_infeasible` | infeasible | Sí | Sin objetivo |
| `test_order_assigned_to_multiple_batches_infeasible` | `test_v5eq__test_order_assigned_to_multiple_batches_infeasible` | infeasible | Sí | Sin objetivo |
| `test_single_order_exceeds_vehicle` | `test_v5eq__test_single_order_exceeds_vehicle` | infeasible | Sí | Sin objetivo |
| `test_no_eligible_picker_returns_infeasible_gracefully` | `test_v5eq__test_no_eligible_picker_returns_infeasible_gracefully` | infeasible | Sí | Sin objetivo |
| `test_fixed_time_counts_toward_the_cold_limit` | `test_v5eq__test_fixed_time_counts_toward_the_cold_limit` | infeasible | Sí | Sin objetivo |
| `test_route_that_must_revisit_a_vertex_is_infeasible` | `test_v5eq__test_route_that_must_revisit_a_vertex_is_infeasible` | infeasible | Sí | Sin objetivo |
| `test_fractional_and_zero_capacities_feasible` | `test_v5eq__test_fractional_and_zero_capacities_feasible` | timeout | No | v5 no terminó; ya hacía timeout en la suite normal |
| `test_batch_is_delayed_while_early_orders_outweigh_completion_weight` | — | — | No | Excluido: el test verifica justamente que v5 espere |
| `test_non_positive_speed_is_rejected_before_solving` | — | — | No | v5 rechaza la entrada antes de resolver. Las heurísticas tienen su propio test: `test_zero_speed_is_rejected` / `test_negative_speed_is_rejected` |

Las otras 45 instancias funcionales son comparables en estado y objetivo.

### Estrés: escenarios sin referencia de objetivo (v5_2 timeout)

`test_realistic_crew_16x16_warehouse`, `test_larger_crew_8_batches_4_pickers`, `test_larger_crew_10_batches_5_pickers`, `test_larger_crew_12_batches_6_pickers`, `test_large_crew_single_wave`, `test_large_crew_three_second_batches`, `test_large_crew_half_second_batches`, `test_large_crew_two_batches_each`, `test_25_orders_per_batch_30_batches_100x100`, `test_8_orders_per_batch_7x7_320_orders`.

Los otros 9 son comparables en estado y objetivo.

## Cómo cruzar los datos

**El cruce ya está hecho:** `python -m analysis.comparability` también escribe `results/comparability/results_v5_vs_heuristics.csv`. Tiene una fila por instancia (funcional o de estrés) y por heurística, y usa los CSV de aco_4 y hc_4 que elige `analysis.load`.

| Columna | Qué es |
|---|---|
| Columnas del registro | `tier`, `v5_test`, `heuristic_instance`, `v5_status`, `v5_obj`, `comparable_status`, `comparable_objective`, `not_comparable_reason` |
| `heuristic` | `opp_aco_4` u `opp_hc_4` |
| `heuristic_obj`, `heuristic_time`, `heuristic_source` | Resultado de la heurística y CSV de donde sale |
| `heuristic_found_solution` | La heurística reportó un objetivo |
| `status_matches` | Encontró solución donde v5 la encontró y no encontró donde v5 probó infeasibilidad. Vacío si el estado no es comparable |
| `gap_pct` | 100 · (heurística − v5) / \|v5\|. Solo donde el objetivo es comparable. Negativo significa que la heurística es mejor. Las diferencias menores a 10⁻⁶ % se redondean a 0 |
| `v5_time`, `v5_time_source` | Tiempo de v5. En los timeouts es el límite (40 min en estrés) |
| `speedup`, `speedup_is_lower_bound` | v5_time / heuristic_time. Si v5 hizo timeout es una cota inferior |

**Tiempo de v5 en funcionales.** El CSV funcional de v5 guarda una fila por método de test, con la última resolución. Por eso `v5_time` se completa solo si se cumplen las tres condiciones siguientes; si no, queda vacío (hoy se completa en 50 de 67 instancias):
- el nombre del método aparece una sola vez en ese CSV;
- el test tiene una sola instancia;
- el objetivo del CSV coincide con el del registro.

Si hace falta armar el cruce a mano:

- **Funcional.**
  - Unir el CSV funcional de la heurística con el registro por `instance` = `heuristic_instance`. `instance` es el nombre del método, el último segmento de la columna `test`.
  - El objetivo de v5 se toma de `v5_obj` del registro. No usar el CSV funcional de v5: guarda un solo objetivo por test, el de su última resolución, y algunos tests resuelven más de una instancia.
- **Estrés.** Unir por nombre de método. En el registro, `v5_test` = `heuristic_instance`.
- **v5_1_mono** resuelve las mismas instancias que v5_2_split, porque usa los mismos tests. Su referencia de estrés es parcial: 01–03 de la corrida consolidada, 04 de la corrida con W_c = 27, 05–10 en corrida al 2026-09-28 y 11–19 sin correr. En 04 hizo timeout, así que no aporta referencia de objetivo.
