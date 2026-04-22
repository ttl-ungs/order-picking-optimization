# Tests

Este documento describe un flujo de trabajo para disenar y mantener los tests de OPP (v1 y v2) de manera consistente.

## Objetivo

- Validar rutas factibles en grafos representativos.
- Verificar penalizaciones por tardanza/adelanto con escenarios controlados.
- Cubrir casos multi picker y multi lote.
- Incluir casos infeasible con causas claras.

## Estructura

- tests/opp_v2/scenarios: definicion de grafos y asignaciones base.
- tests/opp_v2/tests: casos de prueba por grafo (happy path, penalizaciones, etc).
- tests/opp/tests: helpers compartidos.
- tests/opp_v2/tests/route_assertions.py: utilidades para validar rutas y lotes.

## Flujo por grafo (recomendado)

1) Happy path
- Usar un set minimo de ordenes que active nodos clave.
- Validar que la ruta visite todas las ubicaciones requeridas.
- Para un solo lote, usar assert_route_covers_orders.
- Para multiples lotes, usar assert_batch_routes_cover_locations.

2) Penalizaciones (tardanza/adelanto)
- Reutilizar el mismo grafo y asignaciones (N, a, y) para estabilidad.
- Aislar la penalizacion:
  - w1 = 0.0, w2 = 1.0
  - gamma = 0.0 (ignorar adelanto)
  - delta = 1.0
- Caso con tardanza:
  - due_date muy baja (ej. 0.0) para forzar ta_n > 0.
- Caso mejor:
  - due_date alta (ej. 100.0) para esperar ta_n ~= 0.
- Medir sumatoria con OPPTestCase.sum_vars_with_prefix(model, "ta_").

3) Multi picker / multi lote
- Definir x y y de modo que cada picker tenga 1+ lotes.
- Verificar rutas por lote (assert_batch_routes_cover_locations).
- Permitir ubicaciones compartidas entre lotes si el caso lo necesita.

4) Infeasible
- Forzar una causa especifica:
  - Duplicar una ubicacion dentro del mismo lote.
  - Capacidad del vehiculo demasiado baja.
  - Grafo desconectado en una ubicacion requerida.
- Validar status "infeasible".

## Helpers recomendados

- OPPTestCase.normalize_due_dates(orders, override, default)
- OPPTestCase.apply_weight_overrides(w1, w2, gamma, delta, ...)
- OPPTestCase.sum_vars_with_prefix(model, prefix)

Usar estos helpers evita duplicacion y hace mas facil mantener los tests.

## Consideraciones

Los layouts más comunes, según gemini, son de tipo:

| Distribución | Estructura del Grafo | Uso Común |
| --- | --- | --- |
| Bloque Único | Grilla simple (m×n). | Almacenes pequeños, fácil implementación. |
| Multibloque | Grillas conectadas por nodos intermedios. | Centros de distribución grandes (Amazon, centros logísticos). |
| No Tradicional | Grafos con aristas diagonales (Fishbone). | Almacenes de alta densidad con picking intensivo. |

Sería interesante investigar un poco más del tema.

## Ejecucion

Desde la raiz del repo:

python -m unittest tests.opp_v2.tests.test_opp_v2_model_{numero}
