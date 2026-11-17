# Comparabilidad entre el Split y las heurísticas (opp_aco, opp_hc)

Este documento define **qué resultados de los modelos exactos (`opp_split`, `opp_mono`) y de las heurísticas (`opp_aco`, `opp_hc`) se pueden comparar**, y cuáles deben quedar afuera de cualquier tabla o gráfico comparativo.

La fuente de verdad es el registro `results/comparability/comparability_split_vs_heuristics.csv`, que se genera con:

```
python -m experiments.comparison.comparability
```

Toda tabla o gráfico que compare el Split con las heurísticas debe filtrar por sus columnas `comparable_status` y `comparable_objective`, en lugar de decidir caso por caso. Las tablas de este documento son una foto del 2026-09-28; si cambian los tests, manda el CSV.

## Qué se compara y con qué

| Qué | Instancias de las heurísticas | Referencia del Split |
|---|---|---|
| **Funcional** | `<Caso>.<test del Split>[__<k>]` en los CSV funcionales de `opp_aco` y `opp_hc`: una fila por instancia, de las corridas del 2026-09-29, cuando las heurísticas resolvían cada instancia exportada por separado (`__<k>` solo si un test tiene varias instancias). Hoy corren los mismos casos que el Split (`tests/opp_{aco,hc}/functional/test_functional_cases.py`), con una fila por test | Estado y objetivo por instancia en `tests/shared_scenarios/functional/functional_instances.json` |
| **Estrés** | Los casos de `tests/stress_cases/` (19 escenarios), con el mismo nombre de método en los CSV de los cuatro modelos | CSV de estrés de `opp_split`, combinados por `experiments.common.load`: 04–19 con W_c = 27 y 01–03 de las corridas consolidadas |
| **Tiempo igual** | CSV de estrés de cada heurística | `results/equal_time/output_equal_time_<heurística>_*.csv`, donde el Split corre con el tiempo de la heurística como límite |

**Para comparar funcionales se usan solo las instancias de `test_functional_cases.py`**: son las que resuelven exactamente los mismos datos que el Split. Los otros tests funcionales de opp_aco y opp_hc (`invalid_speed_rejected` y, en ACO, `unreachable_required_location`) no tienen un par en el Split.

## Cómo se garantiza que sean los mismos datos

- **Funcional.** `tests/shared_scenarios/functional/export_functional_instances.py` corre la suite funcional de `opp_split` y captura cada escenario en el momento en que el Split escribe sus archivos `.dat`. Guarda también el estado y el objetivo finales del Split.
  - Las heurísticas corren los mismos casos funcionales que el Split: el mismo escenario y las mismas aserciones, con un adaptador que les da su solución con los nombres de las variables de los modelos exactos (`tests/infra/cases/heuristic_model_case.py`).
  - Donde el escenario no define velocidades ni límite de frío, se completan con V_p = 1,0 y T_cold = 10⁹, igual que hace el Split.
  - Hay que volver a correr el exportador si cambia un test o un escenario funcional del Split. Necesita zimpl y SCIP.
- **Estrés.** Los tests de las dos heurísticas llaman al mismo constructor de escenario, con los mismos argumentos, que los del Split. Se verificó para los 19 el 2026-09-28.

## Reglas de comparabilidad

Están implementadas en `tests/infra/factories/functional_instances.py` (`comparability`, `split_waiting_batches`).

| Situación | ¿Estado comparable? | ¿Objetivo comparable? | Motivo |
|---|---|---|---|
| el Split no terminó (timeout) | No | No | No hay referencia |
| el Split fija la asignación batch→picker (`x_pb`) | No | No | Las heurísticas no admiten esa restricción. Hoy no hay ningún caso |
| el Split infeasible | **Sí** | No | No hay objetivo; sí se compara que la heurística también dé infeasible |
| el Split usa espera voluntaria | **Sí** | No | Ver abajo |
| el Split óptimo, sin espera | **Sí** | **Sí** | Mismos datos, mismo objetivo |

**Espera voluntaria.** En el Split la restricción es `c_pb >= T_exec_pb`, no una igualdad. Eso le permite reportar un batch como terminado más tarde de lo que termina físicamente, para reducir la earliness. Las heurísticas reportan tiempos reales y no pueden hacerlo, así que en esos casos el objetivo del Split es menor por diseño del modelo, no por un mejor plan.
- **Cómo se detecta.** Sobre la solución del Split: un batch espera si su `c_pb` supera la finalización del batch anterior del mismo picker más su `T_exec_pb`.
- **Cuándo se cuenta.** Solo si la earliness tiene peso (`W_pen · W_e > 0`). Si no lo tiene, esperar no puede bajar el objetivo.
- **Verificación exacta del 2026-09-28.** En las 9 instancias marcadas, "rutas más cortas + espera óptima" reproduce exactamente el objetivo del Split. ACO, en esas mismas instancias, obtiene el mejor scheduling posible sin espera para sus rutas.

**Estrés.** No hay espera que descartar:
- En 04–19, W_c = 27 es mayor que las órdenes por batch, así que esperar nunca conviene.
- En 01–03, todas las órdenes llegan tarde, así que no hay earliness que recortar.

Los escenarios de estrés donde el Split hizo timeout no tienen referencia de objetivo. Se usan para comparar escala (la heurística resuelve y el Split no) y en el experimento de tiempo igual, no para calcular brechas.

## Resumen (2026-09-28)

| Parte | Comparables en estado y objetivo | Solo en estado | No comparables |
|---|---|---|---|
| Funcional (67 instancias + 2 tests sin instancia) | 45 | 21: 12 infeasibles y 9 con espera del Split | 3: 1 timeout, 1 excluido y 1 que no llega al solver |
| Estrés (19 escenarios) | 9 | 0 | 10: el Split timeout |

### Funcional: instancias no comparables en objetivo

| Test del Split | Instancia en opp_aco/opp_hc (`Caso.test`) | Estado del Split | ¿Estado comparable? | Motivo |
|---|---|---|---|---|
| `test_basic_two_orders_capacity_limit` | `Case01.test_basic_two_orders_capacity_limit` | optimal | Sí | el Split usa espera voluntaria en B1 |
| `test_longer_single_mission_duplicate_location` | `Case19.test_longer_single_mission_duplicate_location` | optimal | Sí | el Split usa espera voluntaria en B1 |
| `test_longer_single_mission_route` | `Case19.test_longer_single_mission_route` | optimal | Sí | el Split usa espera voluntaria en B1 |
| `test_bridge_earliness_order_size` | `Case26.test_bridge_earliness_order_size__1` | optimal | Sí | el Split usa espera voluntaria en B2, B4 |
| `test_bridge_earliness_order_size` | `Case26.test_bridge_earliness_order_size__2` | optimal | Sí | el Split usa espera voluntaria en B1, B3 |
| `test_one_empty_batch_allowed` | `Case29.test_one_empty_batch_allowed` | optimal | Sí | el Split usa espera voluntaria en B2, B3 |
| `test_order_assigned_to_single_batch_feasible` | `Case31.test_order_assigned_to_single_batch_feasible` | optimal | Sí | el Split usa espera voluntaria en B1, B2 |
| `test_service_time_zero` | `Case33.test_service_time_zero` | optimal | Sí | el Split usa espera voluntaria en B1 |
| `test_repeated_picking_locations` | `Case07.test_repeated_picking_locations` | infeasible | Sí | Sin objetivo |
| `test_bridge_disconnected_required_location` | `Case21.test_bridge_disconnected_required_location` | infeasible | Sí | Sin objetivo |
| `test_bridge_disconnected_required_location_with_capacities` | `Case26.test_bridge_disconnected_required_location_with_capacities` | infeasible | Sí | Sin objetivo |
| `test_preflight_detects_when_no_picker_is_eligible` | `Case24bPreflightEligibility.test_preflight_detects_when_no_picker_is_eligible` | infeasible | Sí | Sin objetivo |
| `test_grid_batch_infeasible_order_size` | `Case25.test_grid_batch_infeasible_order_size` | infeasible | Sí | Sin objetivo |
| `test_grid_order_size_bigger_than_cart_infeasible` | `Case25.test_grid_order_size_bigger_than_cart_infeasible` | infeasible | Sí | Sin objetivo |
| `test_fractional_and_zero_capacities_infeasible` | `Case30.test_fractional_and_zero_capacities_infeasible` | infeasible | Sí | Sin objetivo |
| `test_order_assigned_to_multiple_batches_infeasible` | `Case31.test_order_assigned_to_multiple_batches_infeasible` | infeasible | Sí | Sin objetivo |
| `test_single_order_exceeds_vehicle` | `Case32.test_single_order_exceeds_vehicle` | infeasible | Sí | Sin objetivo |
| `test_no_eligible_picker_returns_infeasible_gracefully` | `Case34ColdChainEdgeCases.test_no_eligible_picker_returns_infeasible_gracefully` | infeasible | Sí | Sin objetivo |
| `test_fixed_time_counts_toward_the_cold_limit` | `Case35ColdChainCoverage.test_fixed_time_counts_toward_the_cold_limit` | infeasible | Sí | Sin objetivo |
| `test_route_that_must_revisit_a_vertex_is_infeasible` | `Case38SimplePathLimit.test_route_that_must_revisit_a_vertex_is_infeasible` | infeasible | Sí | Sin objetivo |
| `test_fractional_and_zero_capacities_feasible` | `Case30.test_fractional_and_zero_capacities_feasible` | timeout | No | el Split no terminó; ya hacía timeout en la suite normal |
| `test_batch_is_delayed_while_early_orders_outweigh_completion_weight` | — | — | No | Excluido: el test verifica justamente que el Split espere |
| `test_non_positive_speed_is_rejected_before_solving` | — | — | No | el Split rechaza la entrada antes de resolver. Las heurísticas tienen su propio test: `test_zero_speed_is_rejected` / `test_negative_speed_is_rejected` |

Las otras 45 instancias funcionales son comparables en estado y objetivo.

### Estrés: escenarios sin referencia de objetivo (timeout del Split)

`test_realistic_crew_16x16_warehouse`, `test_larger_crew_8_batches_4_pickers`, `test_larger_crew_10_batches_5_pickers`, `test_larger_crew_12_batches_6_pickers`, `test_large_crew_single_wave`, `test_large_crew_three_second_batches`, `test_large_crew_half_second_batches`, `test_large_crew_two_batches_each`, `test_25_orders_per_batch_30_batches_100x100`, `test_8_orders_per_batch_7x7_320_orders`.

Los otros 9 son comparables en estado y objetivo.

## Cómo cruzar los datos

**El cruce ya está hecho:** `python -m experiments.comparison.comparability` también escribe `results/comparability/results_split_vs_heuristics.csv`. Tiene una fila por instancia (funcional o de estrés) y por heurística, y usa los CSV de opp_aco y opp_hc que elige `experiments.common.load`.

| Columna | Qué es |
|---|---|
| Columnas del registro | `tier`, `split_test`, `heuristic_instance`, `split_status`, `split_obj`, `comparable_status`, `comparable_objective`, `not_comparable_reason` |
| `heuristic` | `opp_aco` u `opp_hc` |
| `heuristic_obj`, `heuristic_time`, `heuristic_source` | Resultado de la heurística y CSV de donde sale |
| `heuristic_found_solution` | La heurística reportó un objetivo |
| `status_matches` | Encontró solución donde el Split la encontró y no encontró donde el Split probó infeasibilidad. Vacío si el estado no es comparable |
| `gap_pct` | 100 · (heurística − el Split) / \|el Split\|. Solo donde el objetivo es comparable. Negativo significa que la heurística es mejor. Las diferencias menores a 10⁻⁶ % se redondean a 0 |
| `split_time`, `split_time_source` | Tiempo del Split. En los timeouts es el límite (40 min en estrés) |
| `speedup`, `speedup_is_lower_bound` | split_time / heuristic_time. Si el Split hizo timeout es una cota inferior |

**Tiempo del Split en funcionales.** El CSV funcional del Split guarda una fila por método de test, con la última resolución. Por eso `split_time` se completa solo si se cumplen las tres condiciones siguientes; si no, queda vacío (hoy se completa en 50 de 67 instancias):
- el nombre del método aparece una sola vez en ese CSV;
- el test tiene una sola instancia;
- el objetivo del CSV coincide con el del registro.

Si hace falta armar el cruce a mano:

- **Funcional.**
  - Unir el CSV funcional de la heurística con el registro por `instance` = `heuristic_instance`. `instance` es el nombre del método, el último segmento de la columna `test`.
  - El objetivo del Split se toma de `split_obj` del registro. No usar el CSV funcional del Split: guarda un solo objetivo por test, el de su última resolución, y algunos tests resuelven más de una instancia.
- **Estrés.** Unir por nombre de método. En el registro, `split_test` = `heuristic_instance`.
- **opp_mono** resuelve las mismas instancias que opp_split, porque usa los mismos tests. Su referencia de estrés es parcial: 01–03 de la corrida consolidada, 04 de la corrida con W_c = 27, 05–10 en corrida al 2026-09-28 y 11–19 sin correr. En 04 hizo timeout, así que no aporta referencia de objetivo.
