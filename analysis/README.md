# Pipeline de análisis de resultados

Generaliza `specs/model_analysis.md` (escrito originalmente para
`opp_v3`/`opp_hc`/`opp_aco`) a los modelos actuales:

| Label       | Rol                                                          |
|-------------|---------------------------------------------------------------|
| `opp_v4`    | Modelo exacto (ZIMPL + SCIP) — ground truth de calidad         |
| `opp_hc_2`  | Hill Climbing, pickers en paralelo, **sin** congestión         |
| `opp_aco_2` | ACO, pickers en paralelo, **sin** congestión                   |
| `opp_hc_3`  | Hill Climbing, congestion-aware                                |
| `opp_aco_3` | ACO, congestion-aware, multi-pheromone (m-ACO4)                |

## 1. Generar los datos

El pipeline **no ejecuta los tests**, solo lee lo que ya está en
`tests/outputs/<modelo>/<normal|stress>/*.csv`. Para generarlos:

```bash
export WRITE_RESULTS_CSV=1

python tests/opp_v4/execute_tests.py            # opp_v4 normal
python tests/opp_v4/execute_stress_tests.py     # opp_v4 stress
python tests/opp_hc_2/execute_tests.py          # opp_hc_2 normal
python tests/opp_hc_2/execute_stress_tests.py   # opp_hc_2 stress
python tests/opp_aco_2/execute_tests.py         # opp_aco_2 normal
python tests/opp_aco_2/execute_stress_tests.py  # opp_aco_2 stress
python tests/opp_hc_3/execute_tests.py          # opp_hc_3 normal
python tests/opp_hc_3/execute_stress_tests.py   # opp_hc_3 stress
python tests/opp_aco_3/execute_tests.py         # opp_aco_3 normal
python tests/opp_aco_3/execute_stress_tests.py  # opp_aco_3 stress
```

Cada `execute_stress_tests.py` acepta un id de dos dígitos como único
argumento para correr un solo test (p. ej. `python tests/opp_hc_3/execute_stress_tests.py 04`).

### Alcance de los stress tests que se agregaron

`opp_hc_2` ya tenía su batería completa de 34 escenarios de estrés (heredada
de `opp_v3`/`opp_hc`/`opp_aco`). Para `opp_v4`, `opp_aco_2`, `opp_hc_3` y
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
  `tests/outputs/opp_v3/stress/complete_output_v3_stress_tests.csv`, y la
  hipótesis de "asintotismo exponencial" en `specs/model_analysis.md` sec. 5)
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
   probabilidad de los 25 lotes de `test_04` a la vez era ~1e-21 —
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
con qué presupuesto se corrió cada fila. Con este fix, `test_04` (25 lotes)
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

**Instancias que quedan fuera de alcance de cualquier tuneo, y por qué**
(2026-08-27): `test_09`/`10`/`11` (750 órdenes, ~25 ubicaciones requeridas
por lote) le dan timeout incluso a `opp_hc_2` en la corrida real, y hasta el
método rápido de `opp_hc_2` (`_generate_feasible_route`, Dijkstra
determinístico) devuelve `None` para esos lotes. Se investigó **si existe
siquiera una ruta simple** (sin repetir ningún nodo) que visite esas 25
ubicaciones en esa grilla de 10x10, probando 2000 órdenes de visita
distintos (al azar, no solo "el más cercano primero") con el mismo Dijkstra
de `opp_hc_2` -- **ninguno de los 2000 encontró una ruta simple**
(verificado que el método en sí no tiene un bug: en un lote fácil de 4
ubicaciones, sí encuentra rutas válidas en 17/200 intentos).

Esto probablemente significa que **la instancia es infeasible por
construcción bajo la restricción "sin loops" (17)** -- compartida por los 5
modelos, incluido el exacto -- no que sea "difícil de resolver". Explicaría
de una sola vez por qué fallan los cinco: no es debilidad puntual de ningún
algoritmo, es que el problema, tal como está planteado, puede no tener
solución. La causa más probable: `scenario_custom_setup` reparte pedidos a
lotes por *round-robin* sin verificar si el conjunto de ubicaciones
resultante por lote admite una ruta simple en la grilla -- a partir de
cierta densidad (pedidos por lote) es fácil terminar con un lote cuyas
ubicaciones no se pueden recorrer sin pasar dos veces por el mismo pasillo.
No se investigó (todavía) agregar una validación de feasibility geométrica
al generador; ver la sección "Sobre permitir ciclos en las rutas" más abajo
para la discusión de qué implicaría relajar esa restricción en vez de
evitar generar estas instancias.

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
resultado, más rápido nada más: `test_02` (400 nodos) 566s→3.7s (~153x);
perfil completo de un caso 149.8s→2.6s (~57x); el caso que sigue sin
converger (densidad 25) también corre ~16x más rápido aunque el resultado
final (`infeasible`) no cambia -- confirma que ese límite es matemático, no
de velocidad.

**Los números de tiempo de estrés para `opp_aco_2`/`opp_aco_3` en las
tablas de este documento y en `analysis/output/report.md` son anteriores a
este fix y están desactualizados** -- hay que volver a correr esas dos
baterías de estrés para tener cifras reales. `opp_hc_2`/`opp_hc_3` también
mejoraron, pero ya eran rápidas: no se espera que cambie la conclusión ahí.

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
  #5bc0de, #5cb85c`, igual que la especificada en `specs/model_analysis.md`).
- `analysis/run_analysis.py` — CLI que junta todo y escribe el reporte.
