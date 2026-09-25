# Pipeline de análisis de resultados

Generaliza `docs/specs/model_analysis.md` (escrito originalmente para
`opp_v3`/`opp_hc_1`/`opp_aco_1`) a los modelos actuales:

| Label       | Rol                                                          |
|-------------|---------------------------------------------------------------|
| `opp_v4`    | Modelo exacto (ZIMPL + SCIP) — ground truth de calidad         |
| `opp_hc_2`  | Hill Climbing, pickers en paralelo, **sin** congestión         |
| `opp_aco_2` | ACO, pickers en paralelo, **sin** congestión                   |
| `opp_hc_3`  | Hill Climbing, congestion-aware                                |
| `opp_aco_3` | ACO, congestion-aware, multi-pheromone (m-ACO4)                |
| `opp_hc_4`  | Hill Climbing, velocidad de picker + cadena de frío (como `opp_v5_2_split`), **sin** congestión |
| `opp_aco_4` | ACO, velocidad de picker + cadena de frío (como `opp_v5_2_split`), **sin** congestión |

## 1. Generar los datos

El pipeline **no ejecuta los tests**, solo lee lo que ya está en
`results/<modelo>/<functional|stress>/*.csv`. Para generarlos:

```bash
export WRITE_RESULTS_CSV=1

python -m tests.run_suite opp_v4 functional
python -m tests.run_suite opp_v4 stress
python -m tests.run_suite opp_hc_2 functional
python -m tests.run_suite opp_hc_2 stress
python -m tests.run_suite opp_aco_2 functional
python -m tests.run_suite opp_aco_2 stress
python -m tests.run_suite opp_hc_3 functional
python -m tests.run_suite opp_hc_3 stress
python -m tests.run_suite opp_aco_3 functional
python -m tests.run_suite opp_aco_3 stress
```

(One shared entry point, `tests/run_suite.py`, replaced the ~24 near-identical
per-model `execute_tests.py`/`execute_stress_tests.py` scripts -- see its
module docstring. `opp`/`opp_v2` predate it and keep their own scripts, since
they don't use `TestRunner`/write CSVs at all.)

`--id` runs a single test instead of the full stress suite (p. ej.
`python -m tests.run_suite opp_hc_3 stress --id 04`).

### Alcance de los stress tests que se agregaron

`opp_hc_2` ya tenía su batería completa de 34 escenarios de estrés (heredada
de `opp_v3`/`opp_hc_1`/`opp_aco_1`). Para `opp_v4`, `opp_aco_2`, `opp_hc_3` y
`opp_aco_3` **no** se portaron los 34 — se eligió un subconjunto curado de
11 escenarios (mismo *builder* de escenario y mismos parámetros numéricos que
sus equivalentes en `opp_hc_2`, para que el join por instancia en `analysis/`
sea válido), pensado para cubrir el rango de `N` (cantidad de pedidos) y `V`
(tamaño del grafo) que necesita la sección 6 (correlación/sensibilidad):

| # en este repo | Origen (`opp_hc_2` test #) | Escenario                                    |
|-----------------|------------------------------|-----------------------------------------------|
| 01 / 02 / 03    | 01 / 02 / 03                 | grid 10x10 / 20x20 / 25x25 (100/400/625 nodos) |
| 04 / 05 / 06    | 04 / 05 / 06                 | custom setup, distintas órdenes por lote        |
| 07              | 09                           | capacidad infeasible (caso negativo a propósito) |
| 08              | 34                           | 320 órdenes, grilla 7x7                         |
| 09 / 10         | 11 / 12                      | 750 órdenes, grilla 10x10 / 25x25 (**grandes**) |
| 11              | 15                           | doble grilla 50x50, 750 órdenes (**grande**)    |

- **`opp_v4` solo tiene 01-08.** Los tests 09, 10 y 11 (750 órdenes / hasta
  5000 nodos) se excluyeron a propósito para el modelo exacto: el propio
  `opp_v3` (antecesor de `opp_v4`) ya demostró en su suite de estrés que a
  esa escala el solver exacto no converge en tiempo razonable (ver
  `results/opp_v3/stress/complete_output_v3_stress_tests.csv`, y la
  hipótesis de "asintotismo exponencial" en `docs/specs/model_analysis.md` sec. 5)
  — correrlos ahí solo quemaría CPU para un timeout garantizado. Confirmado
  empíricamente: de las 8 que sí tiene, solo 1 converge (la infeasible
  instantánea).

Sobre `RUN_LARGE_TESTS`: existía como gate para las instancias más pesadas
(09/10/11 acá, y varias más en la batería completa de `opp_hc_2`), pero se
eliminó (2026-08-19, a pedido explícito): todos los tests de estrés corren
siempre. Si ves referencias viejas a esa variable en commits/documentación
anteriores, ya no aplican.

#### Instancias intermedias (2026-08-26): 9 escenarios más, densidad baja

Con solo los 11 originales, la sección 6 (correlación) tenía muestras muy
chicas (8-11 puntos `OK` por modelo, y varios con `N` y `V` moviéndose casi
siempre juntos, sin poder aislar el efecto de cada uno). Se agregaron 9
escenarios más (`scenario_custom_setup`, misma familia que 04-11), pensados
específicamente para eso: densidad de pedidos-por-lote entre 2 y 10 (lejos
de la zona ~20-25+ que colapsa la construcción de rutas de ACO
independientemente del presupuesto — ver la nota de más abajo), y variando
`N`/`V` de a uno por vez (mismo `N`/`B` con distinta grilla, y viceversa) en
vez de siempre juntos:

| Escenario | batches, orders, rows, cols | N   | B  | V   | densidad |
|-----------|------------------------------|-----|----|-----|----------|
| A         | 10, 20, 5, 5                 | 20  | 10 | 25  | 2        |
| B         | 10, 20, 15, 15               | 20  | 10 | 225 | 2        |
| C         | 10, 20, 20, 20               | 20  | 10 | 400 | 2        |
| D         | 15, 60, 10, 10               | 60  | 15 | 100 | 4        |
| E         | 20, 100, 10, 10              | 100 | 20 | 100 | 5        |
| F         | 20, 100, 15, 15              | 100 | 20 | 225 | 5        |
| G         | 20, 100, 20, 20              | 100 | 20 | 400 | 5        |
| H         | 15, 100, 10, 10              | 100 | 15 | 100 | 6.67     |
| I         | 6, 60, 10, 10                | 60  | 6  | 100 | 10       |

Numeración: `opp_hc_2` las agregó como **35-43** (sigue su propia
numeración 01-34 ya existente); `opp_aco_2`/`opp_hc_3`/`opp_aco_3` las
agregaron como **12-20** (seguían su numeración 01-11). **No se agregaron a
`opp_v4`** — ya no converge ni en las instancias más chicas que tiene
(01-08), agregar más solo sumaría timeouts garantizados sin aportar datos.

Resultado real (n `OK` en sección 6, estrés, antes → después de sumar estas
9): `opp_hc_2` 23→32, `opp_aco_2` 8→15, `opp_hc_3` 8→20, `opp_aco_3` 4→7.
`opp_aco_3` sigue siendo la muestra más chica — es un reflejo genuino de que
le cuesta más converger (ver "Nota sobre ACO en estrés" abajo), no falta de
instancias corridas.

Si hace falta más resolución todavía, se puede seguir ampliando con el mismo
patrón: reusar el *builder* de escenario de `opp_hc_2`
(`scenario_custom_setup` / `scenario_double_grid` /
`scenario_six_missions_two_periods_grid_graph`, todas funciones puras sin
acoplamiento a ningún modelo), eligiendo densidad ≤10 para que converja de
forma confiable, y siguiendo la numeración de cada modelo desde donde quedó
(44+ en `opp_hc_2`, 21+ en los demás).

### Nota sobre ACO en estrés (bug corregido)

Al portar el test 04 a `opp_aco_2`, con los hiperparámetros default (15
hormigas, 60 iteraciones) el algoritmo daba **siempre** `infeasible` en esa
instancia (misma instancia donde `opp_hc_2` sí converge) — y ni subir
`A_ants`/`Max_it` a valores mucho más altos (150×100 = 15.000 intentos)
cambiaba el resultado. Investigado a fondo (2026-08-19), resultó ser un bug
real de construcción de rutas en `models/opp_aco_2/opp_aco_2.py` (y su
análoga en `models/opp_aco_3/opp_aco_3.py`), no una limitación inherente del
heurístico ni cuestión de tuneo:

1. **Fase 1** (caminata hacia las ubicaciones requeridas) prohibía pisar
   cualquier nodo ya visitado, incluso nodos de paso sin importancia →
   la hormiga se trababa sola en esquinas de grillas grandes.
2. **Fase 2** (conexión final por BFS) tenía el mismo problema, y era la
   causa **dominante** (~65% de los fallos medidos en una instancia de
   prueba).
3. Una vez arregladas 1 y 2, apareció el cuello de botella real: cada lote
   puede salir "con loop" (repite un nodo, lo cual el validador rechaza
   correctamente — esa restricción sí es compartida con el modelo exacto).
   El diseño original exigía que **todos** los lotes de una hormiga salieran
   sin loop *a la vez*; con una tasa de éxito por lote de 5-68%, la
   probabilidad de los 25 lotes de `test_case_04` a la vez era ~1e-21 —
   imposible sin importar el presupuesto de hormigas/iteraciones.

El fix real: cada lote se reintenta individualmente hasta salir limpio, en
vez de descartar toda la hormiga por un solo lote fallido (con rollback del
`CongestionTracker` en `opp_aco_3`, vía `CongestionTracker.snapshot()`/
`restore()`, para que un intento descartado no deje reservas fantasma). El
tope de reintentos (`_MAX_ROUTE_ATTEMPTS_PER_BATCH`, subido de 40 a 100 el
2026-08-20 tras confirmar empíricamente que 100 ayuda en casos intermedios
sin costo extra en los que ya andaban bien -- pero **no** en instancias con
~25+ ubicaciones requeridas por lote, ver más abajo) queda registrado como
columna en el CSV (`Max_route_attempts_per_batch`) para que quede trazable
con qué presupuesto se corrió cada fila. Con este fix, `test_case_04` (25 lotes)
resuelve `optimal` en ~13 minutos con los hiperparámetros **default**
(15×60) -- sin necesidad de tocar `A_ants`/`Max_it`. Al portarlo, la Fase 2
tenía además una sutileza: hay que intentar primero la ruta *limpia*
(evitando visitados) y solo si eso falla, permitir revisitar -- invertir el
orden causaba una regresión real en un test normal ya existente
(`test_repeated_picking_locations_2`, detectada y corregida en el mismo
trabajo).

Esto sigue siendo relevante para la tesina: aunque ya no es un bug, sí
confirma que la tasa de éxito de ACO en instancias con muchos lotes depende
fuertemente de la calidad de la construcción de rutas, no solo de
hiperparámetros. Con datos reales (2026-08-26, 20 instancias de estrés por
modelo tras sumar las intermedias): tasa de éxito en estrés `opp_hc_3` 85%,
`opp_aco_2` 75%, `opp_hc_2` 74% (34 instancias, batería heredada completa),
`opp_aco_3` 35%, `opp_v4` 12.5%. El costo de modelar congestión en tiempo de
estrés también es muy distinto entre arquitecturas: `opp_hc_3` no paga casi
nada frente a `opp_hc_2` (+0.05%, dentro del ruido), `opp_aco_3` paga +263%
frente a `opp_aco_2` -- la construcción determinística de HC compensa el
costo de simular congestión; el switch probabilístico τ1/τ2 de ACO3 no.

**Instancias que quedan fuera de alcance de cualquier tuneo -- y por qué NO
es infeasibilidad por construcción (hipótesis refutada, 2026-08-27)**:
`test_case_09`/`10`/`11` (750 órdenes, ~25 ubicaciones requeridas por lote) le
dan timeout incluso a `opp_hc_2` en la corrida real, y hasta el método
rápido de `opp_hc_2` (`_generate_feasible_route`, Dijkstra determinístico)
devuelve `None` para esos lotes. Con 2000 órdenes de visita distintos (al
azar) sobre ese mismo Dijkstra, ninguno encontró una ruta simple para el
lote B1 de `test_case_09` -- lo que en su momento se documentó acá como fuerte
evidencia de que **la instancia sería infeasible por construcción** bajo la
restricción "sin loops" (17), compartida por los 5 modelos.

**Se corrió el chequeo directo contra SCIP
(`tests/opp_v4/diagnostics/test_case_single_batch_infeasibility_check.py`,
con límite de 1800s) y la hipótesis quedó refutada**: SCIP resuelve ese
mismo lote B1 (25 ubicaciones requeridas, mismo grid 10x10) en **1.8
segundos**, `status=optimal`, encontrando una ruta simple de 56 nodos que
visita las 25 ubicaciones sin repetir ninguna (verificado reconstruyendo la
ruta desde las variables `z_ijb` activas -- 55 arcos, 56 nodos únicos, sin
loops). La instancia **sí es factible**; el patrón de la ruta óptima no
tiene nada patológico (recorre la grilla en zigzag), así que no es un caso
límite raro que SCIP encontró "de casualidad".

Esto redirige el hallazgo: el problema no es la instancia, es que **la
construcción por vecino-más-cercano (Dijkstra determinístico greedy) que
usa `opp_hc_2`/`opp_hc_3` no tiene backtracking** -- una vez que el greedy
se mete en un callejón sin salida (visita ubicaciones en un orden que deja
alguna ubicación requerida solo alcanzable revisitando un nodo ya usado),
no hay forma de deshacer una elección anterior, y **da igual en qué orden
se recorran las ubicaciones al azar**: 2000/2000 órdenes de visita fallaron
porque el método en sí -- no la instancia -- no puede encontrar la ruta
zigzag que SCIP sí encuentra explorando el espacio de soluciones completo
(MILP) en vez de construir la ruta paso a paso sin vuelta atrás. Es la
misma familia de bug que el de ACO (self-avoiding walk sin retroceso, ver
más abajo), pero en HC es 100% determinístico -- por eso ningún reintento
ni cambio de semilla lo arregla, y por eso HC nunca lo resuelve mientras
que ACO sí puede (con su fix de reintento-por-lote) porque ACO explora
alternativas donde HC comete el mismo error todas las veces.
Ver también `docs/thesis/results_outline.md` sección "Hallazgo más fuerte
todavía..." (a corregir con este resultado) para el registro completo.

### Optimización de rendimiento (2026-08-27): ~57-150x más rápido

Un profiling encontró que `_build_batch_route`/`_find_shortest_path_bfs`
(ACO2/ACO3) y `_dijkstra`/`_generate_feasible_route_bff` (HC2/HC3) hacían
`for n in location_graph.get_vertices(): if location_graph.has_edge(current, n)`
para encontrar los vecinos de un nodo -- un escaneo O(V) (con
`has_edge`/`get_distance` reconstruyendo un objeto `OPPLocation` nuevo por
cada candidato, solo para hashearlo) en vez de O(grado real, ~4 en una
grilla). En una instancia de estrés de 100 nodos, `has_edge` sola explicaba
~82% del tiempo total (87M de llamadas). Se agregó
`OPPLocationGraph.get_neighbors()` (lista de adyacencia precalculada,
ordenada -- mismo orden que `get_vertices()`, así que no cambia qué ruta
determinística eligen `opp_hc_2`/`opp_hc_3` cuando hay varias igual de
cortas) y se reemplazó el patrón en los 4 lugares. Resultado, mismo
resultado, más rápido nada más: `test_case_02` (400 nodos) 566s→3.7s (~153x);
perfil completo de un caso 149.8s→2.6s (~57x); el caso que sigue sin
converger (densidad 25) también corre ~16x más rápido aunque el resultado
final (`infeasible`) no cambia -- confirma que ese límite es matemático, no
de velocidad.

**Actualizado (2026-08-27): ya se re-corrieron `opp_aco_2`/`opp_aco_3` en
estrés con el fix aplicado.** `analysis/output/report.md` refleja los
números nuevos: `aco_2` stress mean 595s→52.6s (~11x), tasa de éxito
75%→85%; `aco_3` stress mean 985s→274.5s (~3.6x), tasa de éxito 35%→70%.
`opp_hc_2`/`opp_hc_3` también mejoraron, pero ya eran rápidas: no cambió la
conclusión ahí. El ranking relativo NO se invirtió -- HC sigue siendo más
rápido que ACO en ambos pares, porque ACO repite la construcción de ruta
`A_ants × Max_it` veces por diseño; el fix arregla el costo anormal por
paso, no la diferencia estructural esperada entre "una construcción greedy"
y "una búsqueda con muchas hormigas". Ver `docs/thesis/results_outline.md`
secciones 1-2 para el detalle.

Los tests de estrés pueden tardar bastante por instancia, sobre todo en ACO
(hasta ~38 min ya vistos en `opp_aco_3`) — correrlos con
`STRESS_TEST_TIMEOUT_MINUTES=40` (el default de `TEST_TIMEOUT_MINUTES`, 25,
se queda corto: algunas instancias que sí convergen tardan 24-25 min, muy al
límite). No hace falta volver a correr nada que ya corriste con 25 min si
convirgió (si convergió en X min, con cualquier timeout ≥ X también
convergería) ni lo que ya dio timeout con un valor menor (con un timeout más
chico todavía daría timeout) — el resultado a un timeout distinto se puede
inferir del `total_time` ya registrado sin gastar cómputo de nuevo, salvo
que quieras confirmarlo.

`opp_v4` requiere el binario `zimpl` instalado y en el `PATH`.

### Auditoría de código (2026-08-27): 3 bugs reales encontrados y corregidos

Se hizo una revisión completa de `opp_hc_2`/`opp_hc_3`/`opp_aco_2`/`opp_aco_3`
buscando bugs y mejoras (no solo performance). Encontró y corrigió:

1. **HC -- `_generate_feasible_route_bff` (fallback exhaustivo de construcción
   de ruta) podía reportar "infeasible" por error**, en `hc_2` y `hc_3` por
   igual. La deduplicación de estados `(nodo, requeridos_restantes)` entre
   caminos distintos podía descartar un camino que sí era viable, porque no
   tenía en cuenta qué nodos opcionales había "gastado" cada camino.
   Reproducido con un contraejemplo chico (depósito D, requeridos {A,B},
   grafo D-P, D-Q, P-A, Q-A, P-B, B-final): el método devolvía `None` pese a
   que `D→Q→A→P→B→final` es una ruta válida. Arreglado sacando la
   deduplicación cruzada entre caminos (solo se evita revisitar un nodo
   *dentro* del mismo camino) y agregando un presupuesto explícito de
   expansiones (`_MAX_BFF_EXPANSIONS = 200_000`) para acotar el costo, ya que
   sin ninguna poda esto es exponencial en el peor caso. **Verificado que
   esto NO cambia el resultado de `test_case_09`/`10`/`11`** (25 ubicaciones
   requeridas agota el presupuesto en ~1s, sigue devolviendo `None`) -- el
   bug solo afectaba instancias chicas/medianas, no las gigantes de estrés.
2. **HC -- `opp_hc_2._calculate_batch_execution_time` (solo usado para el
   reporte/`solution_info`, no para la búsqueda) tenía una fórmula rota**:
   indexaba el tiempo de servicio (`S`, por ubicación) usando IDs de orden,
   siempre devolviendo 0, y descartaba el término real de capacidad
   (`B_picking * sum(C_n)`). El objetivo que realmente optimiza el hill
   climbing (`RouteEvaluator`, y por lo tanto `obj_val`) nunca estuvo mal --
   `opp_hc_3` ya tenía la fórmula correcta (nunca se retro-portó a `hc_2`).
   Confirmado que `analysis/` no usa `batch_times`/`tardiness`/`earliness`
   de `solution_info` en ningún lado, solo `obj_val` -- este fix no invalida
   ningún dato ya generado.
3. **ACO -- en `opp_aco_3`, el paso de construcción guiado por la matriz de
   feromona de congestión (tau2, mitad de los pasos por defecto) tenía una
   visibilidad (`eta`) ciega a la distancia Y a si el vecino era una
   ubicación requerida**, dependiendo solo de la espera por congestión.
   Medido empíricamente: en un escenario con congestión real, 40% de los
   pasos guiados por tau2 tuvieron espera empatada entre vecinos (sin señal
   discriminante), y de esos, 92% tenían mezcla de vecinos requeridos/no
   requeridos -- es decir, casi la mitad de todas las decisiones de
   construcción en escenarios de baja/nula congestión (el caso común)
   eran ruido puro. Arreglado combinando el mismo término de cercanía a
   ubicaciones requeridas que ya usa tau1 con el término de evitar espera
   (`eta = (closeness * wait_avoidance) ** beta2`), así un paso guiado por
   congestión sigue avanzando hacia el objetivo cuando no hay nada real que
   evitar, sin perder la discriminación por espera cuando sí la hay.

**Impacto en los datos ya generados**: el fix #3 cambia el comportamiento
real de `opp_aco_3.solve()` -- **la batería de estrés de `opp_aco_3` que se
regeneró el 2026-08-27 (post-fix de performance) queda desactualizada de
nuevo y hay que volver a correrla** antes de cerrar la sección de
resultados. Los fixes #1/#2 no cambiaron ningún resultado ya observado
(#2 no toca el objetivo optimizado; #1 se verificó explícitamente que no
cambia `test_case_09/10/11`) pero, para ser prolijos, conviene re-correr también
`opp_hc_2`/`opp_hc_3` en estrés antes de dar los números por definitivos.

### Auditoría de código, parte 2 (2026-08-28): secuenciación en ACO

Revisando el hallazgo #4 de la auditoría (`opp_aco_2`/`opp_aco_3` nunca
buscan en qué orden procesa un picker sus lotes -- la cola queda fija en
orden de ID de lote, sin relación con fechas de vencimiento, a diferencia de
`opp_hc_2`/`opp_hc_3` que sí exploran swaps de secuencia), se agregó un fix
acotado en ambos modelos ACO: **ordenar la cola de cada picker por fecha de
vencimiento más temprana** entre las órdenes de cada lote (empatado por ID
de lote), justo después de la asignación lote→picker y antes de construir
rutas (importa el orden en `opp_aco_3` porque también define el orden
causal de congestión). Es la heurística clásica de scheduling (EDD) para
reducir tardanza -- no una búsqueda exhaustiva de secuencias ni una nueva
tabla de feromona (eso sería mucho más trabajo e incierto en su beneficio;
ver discusión de alcance en el hallazgo #4 original), pero cierra la mayor
parte de la brecha estructural frente a HC con un cambio chico y verificable.
Verificado con un caso concreto (3 lotes, vencimientos 30/5/15 → queda
ordenado 2do/3ro/1ro) y con las suites normales completas de `aco_2` (48/48)
y `aco_3` (59/59), ambas OK.

**Impacto en los datos ya generados**: este fix también cambia el
comportamiento real de ambos solvers (`opp_aco_2` y `opp_aco_3`) en
cualquier instancia con más de un lote por picker -- **hay que sumar
`opp_aco_2` a la lista de baterías de estrés a re-correr** antes de cerrar
la sección de resultados (ya estaba `opp_aco_3` por el fix #3 de arriba).

### Auditoría de código, parte 3 (2026-08-28): items menores pendientes

Se retomaron los hallazgos #5/#7 de la auditoría original (el #6, agregar
más posiciones de inserción al movimiento de reasignación de picker en HC,
queda como trabajo futuro documentado -- no se implementó, es una mejora de
alcance mayor, no un bug):

- **#5 -- sin seed en ningún lado (`hc_2`/`hc_3`/`aco_2`/`aco_3`)**: se
  agregó `Seed` (opcional, `None` por defecto) a `SolveModelDTO` (base
  compartida por las 4 DTOs), que si se define llama a `random.seed()` al
  inicio de `solve()`. Default `None` preserva el comportamiento anterior
  exactamente (no cambia ningún resultado ya generado). Verificado:
  mismo seed -> mismo `obj_val` en corridas repetidas.
- **#7 -- asimetría de refuerzo elitista en `opp_aco_3`**: el boost elitista
  solo reforzaba las matrices de feromona de arco (tiempo/congestión),
  nunca `picker_pheromones` -- inconsistente con `opp_aco_2`, donde sí lo
  hace. Agregado el mismo refuerzo elitista para `picker_pheromones` en
  `opp_aco_3`, a la misma escala que `opp_aco_2`. **Cambia el
  comportamiento real de `opp_aco_3`** (ya estaba en la lista de re-corridas
  pendientes por los fixes #3/#4).

Verificado con las 4 suites normales completas: `hc_2` 46/46, `hc_3` 51/51,
`aco_2` 48/48, `aco_3` 59/59, todas OK.

### Auditoría de código, parte 4 (2026-08-28): bug real en `analysis/load.py`
   -- el 97.7% de `opp_v4` normal estaba mal (corregido a 97.8%, cambio
   chico) -- y deduplicación en `metrics.py`

Se auditó código todavía no revisado en las partes 1-3: `models/base/`,
`models/utils/`, `models/opp_v4/opp_model_v4.zpl` (verificado con el
binario real de `zimpl`), las 4 DTOs completas, y el propio pipeline de
`analysis/` (la fuente de cada número citado en `docs/thesis/results_outline.md`).

**Sin hallazgos críticos en el código compartido/`opp_v4`** -- solo gaps
defensivos latentes, sin disparador actual. Corregidos los dos más
concretos en `models/utils/input_validation.py`:
- `orders_without_exactly_one_batch` reportaba "sin problema" si `Bn`
  estaba vacío pero `N` no (justo el caso que debería atrapar).
- `overloaded_batches` trataba un `C_n` faltante como capacidad 0 en
  silencio (ahora lanza `ValueError` en vez de enmascarar el problema).

**Sí hubo un hallazgo crítico real en `analysis/load.py`**: `_pick_csv`
elegía el CSV "más reciente" por mtime del filesystem -- pero el mtime se
resetea con cada `git checkout`/rebase al momento del checkout, no de la
corrida real. Confirmado en los datos: dos CSVs de `opp_v4` normal
compartían un mtime de checkout con solo 16 segundos de diferencia (un
artefacto del orden de escritura del checkout, no de cuándo se generó cada
uno realmente), y `_pick_csv` eligió la que casualmente cayó más tarde en
esa ventana -- que resultó ser la más VIEJA en términos reales (de antes de
que existieran `test_case_15/13/14`). El reporte publicado decía
`opp_v4` normal 97.7% (43/44) sobre esa base.

**Arreglado**: `load.py` ahora usa la fecha embebida en el *nombre* del
archivo (`YYYYMMDD_HHMMSS`, que sí es confiable, no depende del
filesystem) en vez de mtime. Se corrió la batería normal completa de
`opp_v4` de nuevo (fresca, 2026-08-28) para tener un CSV genuinamente
completo bajo la numeración actual de tests: **45/46 = 97.8%** (1 timeout
real: `test_fractional_and_zero_capacities_feasible`, un caso
numéricamente difícil para SCIP -- no un bug). **El número corregido
(97.8%) es casi idéntico al que estaba publicado (97.7%)** -- el bug de
`load.py` era real y merecía arreglarse por robustez, pero no
correspondía a un error grande en el número ya citado en la tesina, así
que no hace falta reescribir nada de lo ya redactado sobre este punto,
solo actualizar el decimal.

**Efecto colateral encontrado al aplicar el mismo fix a `opp_v4`
estrés**: ahí sí importaba -- el archivo más reciente por nombre de
archivo resultó ser una corrida *parcial* (3 de 8 tests) contra nombres de
escenario que **ya no existen** en el código actual (huérfanos de la
reorganización "Rename tests"). Se agregó un `LATEST_FILE_OVERRIDES`
explícito para `("opp_v4", "stress")` señalando al archivo viejo (2026-08-18)
cuyos 8 nombres de test sí coinciden con la suite actual, restaurando el
12.5% (1/8) ya documentado. Ese archivo sigue sin reflejar los fixes de
performance/algoritmo del 2026-08-27/28 -- correrlo de nuevo llevaría
horas (varios de sus 8 tests ya se sabe que agotan el timeout de 25 min
cada uno), así que queda pendiente como una corrida cara a programar,
no algo urgente dado que el número actual sigue siendo válido como
límite superior conocido.

**Segundo hallazgo real en `metrics.py`**: `quality_gap_table` y
`congestion_reduction_table` cruzaban filas por `(scenario, instance)` sin
deduplicar -- y el nombre de test (`instance`) no es único: distintos
archivos de test pueden definir un método con el mismo nombre para
escenarios genuinamente distintos. Confirmado con datos reales: `opp_v4`
tiene `test_bridge_disconnected_required_location` y
`test_grid_multi_location_orders` definidos dos veces cada uno (con formas
distintas), y `opp_hc_2` en estrés tiene `test_10_orders_per_batch_10_x_10`
definido en dos archivos distintos con `obj_val`/`total_time` totalmente
distintos. Un merge sin deduplicar podía inflar `n_matched` o, peor,
promediar una comparación contra la instancia equivocada sin ningún error
visible. **Arreglado**: nueva función `_dedupe_or_flag_collisions` en
`metrics.py` -- colapsa duplicados benignos (mismos valores), pero excluye
y reporta explícitamente cualquier colisión real (valores distintos bajo
el mismo nombre), en vez de fusionar a ciegas. Ya está activo y reportando
las 3 colisiones reales mencionadas arriba en cada corrida del pipeline.
**Pendiente de limpieza en el código de tests** (no en `analysis/`,
menor prioridad): renombrar los métodos de test colisionados en
`opp_v4`/`opp_hc_2` para que dejen de compartir nombre -- mientras tanto,
esas instancias específicas quedan excluidas de las tablas comparativas
en vez de corromperlas. **Hecho para `opp_v4` (2026-09-24)**: en
`test_case_23` y `test_case_24` los dos métodos pasan a
`test_grid_multi_location_orders_with_capacities` y
`test_bridge_disconnected_required_location_with_capacities` (el cuerpo es
idéntico al de `test_case_20`/`21`; solo registran además las capacidades,
que es lo que los hacía colisionar). Los opp_v5 que los heredan
(`test_case_25`/`26`) toman el nombre nuevo. Queda el de `opp_hc_2` en estrés.

### Cierre de la auditoría (2026-08-30): las 4 baterías de estrés
   re-corridas y consolidadas -- estado final

Con los 7 fixes de comportamiento (partes 1-3) y los 2 fixes de pipeline
(parte 4) ya aplicados, se re-corrieron `opp_hc_2`, `opp_hc_3`, `opp_aco_2`
y `opp_aco_3` en estrés de punta a punta (`opp_hc_2` en dos tandas --
`model_01-15` y `model_16-43` -- por comodidad de la persona corriéndolo,
consolidadas en un único CSV antes de pasarlas al pipeline, mismo patrón
usado anteriormente en el proyecto). Resultado, comparado con los números
pre-auditoría:

| Modelo | Éxito antes | Éxito después | Tiempo medio antes | Tiempo medio después |
| --- | --- | --- | --- | --- |
| `opp_hc_2` | 74.4% (32/43) | 74.4% (32/43) -- sin cambio | 18.3s | **2.97s** |
| `opp_hc_3` | 85% (17/20) | 85% (17/20) -- sin cambio | 4.96s | **0.56s** |
| `opp_aco_2` | 85% (17/20) | 85% (17/20) -- sin cambio | 52.6s | 54.8s -- sin cambio |
| `opp_aco_3` | 70% (14/20) | **85% (17/20)** | 274.5s | **176.5s** |

Lecturas clave:
- **`aco_3` es el único que cambió de tasa de éxito**, y en la dirección
  esperada -- sus tres fixes (#3 eta ciega a distancia, #4 secuenciación
  EDD, #7 asimetría elitista) atacaban directamente su capacidad de
  converger, no solo su velocidad.
- **`hc_2`/`hc_3` se volvieron mucho más rápidos sin cambiar su tasa de
  éxito** -- el fix del BFS de dos niveles (parte 1) no solo corrige el
  caso raro de falso-infeasible, también acelera el camino feliz (tier 1
  sigue siendo el mismo BFS memoizado rápido de siempre; antes de este
  cierre, una versión intermedia del fix -- sin el segundo nivel -- había
  *empeorado* la tasa de éxito por accidente al sacar la memoización
  sin reemplazo; ver el fix corregido de 2026-08-28 en la parte 1).
- El sobrecosto de congestión (`hc_3` vs. `hc_2`, `aco_3` vs. `aco_2`)
  cambió de magnitud con los tiempos nuevos pero la asimetría central se
  mantiene: `hc_3` +18.5% (antes ~0%, ahora se nota más porque `hc_2` se
  volvió mucho más rápido) vs. `aco_3` +231% (bajó del +513% pre-auditoría,
  porque `aco_3` mismo mejoró). Ver `docs/thesis/results_outline.md` sección 5
  para el detalle.

`docs/thesis/results_outline.md` ya refleja estos números finales en todas sus
secciones (1, 2, 5, 6) y su lista de pendientes quedó cerrada -- no falta
ninguna corrida más antes de pasar a redactar el texto de la tesina.

### Tests de `opp_v5_2_split` (2026-08-31): cobertura completa + validación de sus
   capacidades propias -- y un bug real encontrado

Se completó la cobertura de tests normales de `opp_v5_2_split`
(antes solo llegaba a `model_21`, sin los 9 casos que `opp_v4` tiene en
`model_20/21/24-30`) y se agregaron tests nuevos que validan, no solo
comparan, las dos capacidades propias de `opp_v5_2_split` (velocidad heterogénea de
pickers, cadena de frío):

- **Cobertura**: `tests/opp_v5_2_split/functional/test_opp_v5_model_{22,...,30}.py`
  -- una línea cada uno, usando el adaptador genérico `migrated_case()` que
  ya existía en `migrated_case.py` (creado para portar `model_01-19`, nunca
  extendido). `opp_v5_2_split` reusó los números 20/21 para sus propios tests de
  velocidad/frío, así que los 9 casos que faltaban de `opp_v4`
  (`model_20`=grilla, `model_21`=puente, `model_24-30`=pesos distintos,
  vencimientos extremos, lote vacío, capacidades fraccionarias/cero, orden
  en múltiples lotes, orden que excede el vehículo, tiempos de servicio) se
  agregaron como `model_22-30`. También se agregó el test de estrés #08 que
  faltaba (`tests/opp_v5_2_split/stress/test_case_08.py`, el único de
  los 8 de `opp_v4` que `opp_v5_2_split` no tenía).
- **Validación de funcionalidad** (`tests/opp_v5_2_split/functional/test_case_34.py`,
  nuevo): más allá de los 4 tests básicos que ya existían (`model_20`/`21`,
  "¿qué picker lo hace?"), se agregaron 3 tests que verifican la fórmula y
  los casos límite exactos:
  - Verifica numéricamente la fórmula documentada en
    `opp_model_v5_2_split_stage2_scheduling.zpl` (`t_exec_pb = tiempo_fijo + R_b_time / V_p`,
    donde `tiempo_fijo` NO se escala por velocidad) contra valores exactos
    calculados a mano, no solo "qué picker ganó".
  - Verifica el límite exacto de `T_frio_max` (`<=`, no `<`) -- un picker
    cuyo `t_exec_pb` coincide exactamente con el límite debe seguir siendo
    elegible.
  - **Encontró un bug real**: cuando ningún picker es elegible para un
    lote por cadena de frío, el comentario de `opp_model_v5_2_split_stage2_scheduling.zpl`
    sobre `B_sin_picker_elegible` dice que "el modelo va a dar infactible
    seguro" -- pero no es así. La restricción `assign_exactly_one_picker`
    queda con una suma vacía (`0 == 1`), y **ZIMPL la rechaza en tiempo de
    compilación** (`*** Error 106: Empty LHS, constraint trivially
    violated`), antes de que SCIP llegue a correr. `solve_zpl` levanta un
    `RuntimeError` sin manejar, no devuelve `status="infeasible"` como
    cualquier llamador esperaría según el propio comentario del modelo. El
    test documenta el comportamiento real (`assertRaises`), no lo
    enmascara -- **pendiente reportar** como bug de
    `models/opp_v5_2_split/opp_model_v5_2_split_stage2_scheduling.zpl` (el chequeo `eligible_pairs()`
    del lado Python es, hoy, lo único que evita este crash).

Verificado con la suite normal completa: 53 tests, 52 ok, 1 timeout
(`model_27`, el mismo caso patológico de capacidades fraccionarias/cero que
ya se conocía de `opp_v4` -- coherente, no es nuevo), 0 errores tras el fix
del test de infeasibilidad.

### Estrés de `opp_v5_2_split` (2026-08-31): batería completa -- 0% de éxito, y un
   hallazgo nuevo a investigar

Con las 8 baterías de estrés corridas de punta a punta (incluido el
`model_08` que se agregó en la ronda anterior), `opp_v5_2_split` da **0/8 (0%)**:
7 timeouts (a los 25 min) y **1 falla real, no por timeout**
(`model_05`, `test_10_orders_per_batch`, instancia de 10 lotes/100
órdenes/grilla 10x10).

Investigado el caso que falla: **la Etapa 1 (ruteo) reporta
`status=optimal`, pero ningún lote termina con exactamente un arco de
llegada al nodo final** (`assert_routes_cover_requirements` falla en
`n_final=0` para los 10 lotes, no en uno solo). Lo llamativo no es que
falle -- es *cómo*: cada lote tiene entre 9 y 33 arcos activos para
solo ~10 ubicaciones requeridas (una ruta simple debería necesitar
bastantes menos), con exactamente 1 arco de salida del depósito pero
**cero** arcos de llegada al final, pese a que el nodo final es
alcanzable en el grafo (verificado: hay arcos válidos hacia él). Esto
sugiere que, a esta escala (100 nodos, lotes con muchas ubicaciones
requeridas), la eliminación de subtours vía flujo Gavish-Graves de la
Etapa 1 podría estar dejando pasar arcos "de sobra" (ciclos u otras
estructuras desconectadas del camino depósito-final) sin que la
función objetivo los penalice lo suficiente como para descartarlos --
sería la contraparte, del lado exacto/`opp_v5_2_split`, del mismo tipo de
problema de construcción de rutas que ya se investigó y corrigió del
lado heurístico.

**Investigación más profunda (2026-09-01)**: aislando un solo lote de esa
instancia (mismo patrón que el diagnóstico de infeasibilidad de `opp_v4`)
se confirmó que **no es un bug del modelo de optimización en sí, sino de
cómo ZIMPL nombra las variables en el `.lp` compilado para esta
instancia**. Inspeccionando el `.lp` crudo:

- Las variables `z_ijb` correspondientes a arcos que las restricciones
  `no_inflow_depot`/`no_outflow_final` fuerzan a 0 (arcos que entran al
  depósito o salen del final) aparecen con nombres corruptos tipo
  `z_ijb$V100$V90@4` en vez de `z_ijb$V100$V90$B1` -- les falta el
  sufijo de lote y tienen un sufijo hexadecimal en su lugar.
- Peor: la variable que **sí importa** (el arco de *llegada* al nodo
  final, p. ej. `z_ijb$V90$V100$B1`) **no aparece en absoluto** en el
  `.lp`, ni siquiera con nombre corrupto -- confirmado que el arco
  `(V90, V100)` existe en los datos crudos (`data_E.dat`,
  `distances.dat`), así que debería haber generado una variable.

Esto excede lo que se puede diagnosticar sin entrar a las entrañas del
compilador de ZIMPL (no es un bug de este repositorio ni de
`opp_model_v5_2_split_stage1_routing.zpl` en un sentido que se pueda arreglar en Python).
Parece un problema de generación/truncamiento de nombres de ZIMPL
específico de instancias con muchos lotes y grafos grandes. 
Puede requerir ayuda de alguien con más experiencia en ZIMPL
o revisar su documentación/changelog sobre límites de nombres de
variable.

Con esto, `opp_v5_2_split` en estrés queda confirmado como **no competitivo a
esta escala** (0% contra el 12.5% de `opp_v4`, que además solo pierde
por timeout, no por soluciones mal formadas) -- se mantiene excluido de
las comparaciones de escalabilidad en `docs/thesis/results_outline.md`, ahora
con el dato completo (no parcial) respaldando esa decisión.

### Fix del bug de cadena de frío (2026-09-01)

Se corrigió el bug documentado arriba (`B_sin_picker_elegible` crashea en
vez de dar `infeasible` limpio): se agregó
`models/opp_v5_2_split/utils/cold_chain_validation.py::batches_without_eligible_picker`,
una réplica en Python de `PB_elig`/`t_exec_pb` (mismo patrón que
`models/utils/input_validation.py` usa para `opp_v4`), y se la conectó en
`OPPTestCaseSplit.run_pipeline` para cortocircuitar a `status="infeasible"`
**antes** de invocar ZIMPL para la Etapa 2, en vez de dejar que el error
de compilación se propague como excepción sin manejar. El test que
documentaba el bug (`test_case_34.py`) se actualizó para verificar
el comportamiento corregido (antes esperaba la excepción con
`assertRaises`; ahora espera `status == "infeasible"` limpio).

Este fix vive en el harness de tests (`OPPTestCaseSplit`), no en
`opp_model_v5_2_split_stage2_scheduling.zpl` en sí, porque `opp_v5_2_split` todavía no tiene un punto
de entrada de "producción" fuera de los tests -- si en algún momento lo
tiene, este mismo chequeo debería moverse ahí (o agregarse directamente
al `.zpl`, si ZIMPL ofrece una forma limpia de expresar "sum vacía ==
infeasible declarado" en vez de dejarlo fallar en compilación).

## 2. Correr el pipeline

```bash
python -m analysis.run_analysis
```

Escribe:
- `analysis/output/report.md` — las 6 tablas, en Markdown.
- `analysis/output/*.png` — los gráficos.

Si falta el CSV de algún `(modelo, escenario)`, el loader lo reporta por
consola y esa combinación simplemente no aparece en las tablas — nunca se
inventa un cero ni se descarta en silencio.

## 3. Qué mide cada sección

1. **Tasa de éxito/convergencia** — `ok` / `timeout` / `failed` por modelo y
   escenario. Denominador = todas las corridas, no solo las `ok` (si no, la
   tasa de éxito siempre sería 100%).
2. **Tiempo de ejecución** — media/desvío/máximo de `total_time`, solo casos
   `ok`. Es la comparación original que se había planteado (opp_v4 vs hc_2 vs
   aco_2, y aco_3 vs hc_3), ahora con desvío y no solo un promedio puntual.
3. **Profiling del exacto** — para `opp_v4`, qué porcentaje de `total_time`
   es SCIP resolviendo (`model_time`) vs. overhead (compilación ZIMPL +
   subprocess/Python). Heurísticas no tienen este split porque no llaman a un
   solver externo.
4. **Gap de optimalidad vs. opp_v4** — compara `obj_val` de cada heurística
   contra `obj_val` del exacto en las *mismas* instancias. El join es por
   nombre de método de test **y** por forma de la instancia (`N, V, B, P,
   C_v`) — el nombre solo no alcanza: se verificó empíricamente que
   `test_basic_two_orders_capacity_limit` da `obj_val≈744` en `opp_hc_2`
   (que cae al picker único implícito, `P=1`) y `obj_val≈30` en `opp_v4`
   (cuyo scenario builder ya trae `P=2` incluido) — mismos pesos, misma
   instancia nominal, pero paralelismo distinto, así que esos dos valores no
   son comparables. `quality_gap_table` excluye esos casos y lo reporta por
   consola en vez de mezclarlos en el promedio. Sin esto, "más rápido" no
   dice si la heurística además da soluciones razonables — y con el join mal
   hecho, tampoco lo dice, solo parece que sí.
5. **Congestión** — espera media por congestión (`obj_val_congestion`) para
   `opp_hc_3`/`opp_aco_3`, y el sobrecosto de tiempo que pagan frente a sus
   baselines `opp_hc_2`/`opp_aco_2` (que no miden congestión en absoluto —
   por eso el pipeline marca `congestion_modeled=False` para esos dos en vez
   de mostrar un 0 engañoso). Esta es la comparación real que sustenta el
   aporte de v3, más allá del "extra" de tiempo bruto.
6. **Sensibilidad paramétrica** — correlación de Pearson entre `total_time` y
   `N, V, B, C_v, W_full, W_ea_ta`, a nivel global y por escenario. Aísla qué
   variable es el cuello de botella de cada modelo (p. ej. si ACO sufre más
   por `V` — topología del almacén — que por `N` — cantidad de pedidos).

## Código

- `analysis/config.py` — mapeo de modelos/directorios, columnas, excepciones
  de "último archivo".
- `analysis/load.py` — descubre y concatena los CSVs en un DataFrame ordenado.
- `analysis/metrics.py` — las 6 tablas.
- `analysis/plots.py` — los gráficos (paleta fija: `#003366, #e6e6e6, #d9534f,
  #5bc0de, #5cb85c`, igual que la especificada en `docs/specs/model_analysis.md`).
- `analysis/run_analysis.py` — CLI que junta todo y escribe el reporte.
