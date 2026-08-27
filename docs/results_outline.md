# Bosquejo — Sección de Resultados

Estructura sugerida, un sub-apartado por cada sección del pipeline
(`analysis/output/report.md`). Cada uno: **qué muestra el dato**, **qué
gráfico/tabla citar**, **qué conclusión defendible se puede escribir**.

## 1. Convergencia: el exacto no escala, las heurísticas sí (con matices)

- Tabla 1 + `mean_time_stress.png`.
- `opp_v4` (exacto): 97.7% en normal, **12.5% en estrés** (1/8). Ninguna
  instancia no-trivial converge dentro de 25 min.
- Heurísticas en estrés: `opp_hc_3` 85%, `opp_aco_2` 75%, `opp_hc_2` 74.4%
  (batería de 34, la más grande), `opp_aco_3` 35%.
- Conclusión: el modelo exacto deja de ser viable apenas se sale de
  instancias de juguete — sustenta la necesidad de heurísticos para
  cualquier caso de uso real. Entre los heurísticos, hay una jerarquía
  clara que **no** es "todos convergen igual".

## 2. Tiempo de ejecución: ⚠️ números de estrés desactualizados, hay que
   volver a correr antes de escribir esta sección

- Tabla 2 + `mean_time_normal.png` / `mean_time_stress.png` (escala log).
- Los valores de estrés para `opp_aco_2`/`opp_aco_3` que están hoy en
  `analysis/output/report.md` (`hc_2` ~18s, `hc_3` ~5s, `aco_2` ~595s,
  `aco_3` ~985s) se midieron **antes** del fix de performance del
  2026-08-27 (ver más abajo) y ya no son representativos — con el fix, un
  caso que tardaba 566s ahora tarda 3.7s (~153x). Falta re-correr las
  baterías de estrés de `aco_2`/`aco_3` para tener la tabla real.
- Lo que **no** cambia con el fix: el ranking relativo entre modelos podría
  invertirse o achicarse, pero recién se sabe con los datos nuevos — no
  escribir esta sección hasta tenerlos.
- Normal ya era rápido en los 4 heurísticos (ms), no se espera que cambie la
  conclusión ahí; los números de esa tabla siguen siendo válidos.

## Hallazgo metodológico: bug de performance O(V) en la construcción de rutas

Vale la pena una subsección propia (no es parte del pipeline, pero explica
por qué la sección 2 se reescribe): profiling encontró que
`_build_batch_route`/`_find_shortest_path_bfs` (ACO2/ACO3) y
`_dijkstra`/`_generate_feasible_route_bff` (HC2/HC3) buscaban los vecinos de
un nodo escaneando **todos** los vértices del grafo y probando `has_edge`
uno por uno (O(V) por paso, con `has_edge` reconstruyendo un objeto nuevo
por candidato solo para hashearlo) en vez de usar la adyacencia real
(grado ~4 en una grilla). En una instancia de 100 nodos, `has_edge` sola
explicaba **~82% del tiempo total** (87 millones de llamadas). Se agregó
`OPPLocationGraph.get_neighbors()` (adyacencia precalculada, mismo orden
que antes -- no cambia qué ruta determinística eligen HC2/HC3 cuando hay
varias igual de cortas, verificado con la suite normal completa antes/
después). Mismo resultado, mucho más rápido: 149.8s→2.6s (~57x) en un
perfil completo; 566s→3.7s (~153x) en la instancia más grande medida; hasta
el caso que sigue sin converger corre ~16x más rápido (confirma que ese
límite es matemático, no de velocidad -- ver más abajo). Se puede mencionar
en la tesina como parte del trabajo de implementación, no solo de
modelado -- es la clase de detalle que separa un prototipo de algo que
efectivamente se pueda correr a la escala que la tesina necesita.

## 3. Profiling del exacto

- Tabla 3 + `profiling_exact_model.png`.
- Normal: 92% del tiempo es SCIP resolviendo, 8% overhead (ZIMPL + Python).
- Estrés: el único caso `OK` es el infeasible instantáneo (0% solver, 100%
  overhead trivial) — no hay dato real de perfil en estrés porque no hay
  ninguna instancia no-trivial que el exacto resuelva.

## 4. Gap de calidad: la heurística encuentra el óptimo más seguido de lo
   que la media sugiere

- Tabla 4 + `quality_gap.png` (media vs. mediana).
- Solo 9 instancias comparables (mismo N/V/B/P/C_v) en escenario normal;
  cero en estrés (el exacto casi no converge ahí).
- Mediana = 0% para `hc_2` y `aco_2` — la heurística da el óptimo en más de
  la mitad de los casos comparables. La media (71%/242%) está inflada por
  un puñado de outliers.
- Metodológicamente interesante: el join por nombre de test **no alcanza**
  para saber si dos filas son la misma instancia — hay que verificar forma
  (N/V/B/P/C_v) también, porque el mismo nombre de test puede significar
  paralelismo distinto entre modelos (hallazgo documentado en
  `analysis/README.md` sec. "Gap de optimalidad").

## 5. Congestión: el aporte central — y una asimetría real entre HC3 y ACO3

- Tabla 5 + `congestion_wait.png`.
- `opp_hc_3`/`opp_aco_3` son los únicos que miden espera por congestión
  (`opp_hc_2`/`opp_aco_2`/`opp_v4` no la modelan — por diseño).
- Sobrecosto de tiempo por modelar congestión, estrés: `opp_hc_3` +0.05%
  (dentro del ruido) vs. `opp_hc_2`; `opp_aco_3` **+263%** vs. `opp_aco_2`.
- Por qué: `opp_hc_3` sigue construyendo la ruta con Dijkstra determinístico
  y solo *precia* la congestión al final — casi gratis. `opp_aco_3` decide,
  paso a paso, entre la matriz de feromona de tiempo y la de congestión
  (m-ACO4, switch probabilístico τ1/τ2) — cada paso guiado por congestión
  es un paso *no* guiado por cercanía a la ubicación requerida, lo que baja
  la tasa de rutas limpias por intento (ver hallazgo de bug de ACO, sección
  siguiente) y encarece todo lo demás en cadena.
- Este es el resultado que más vale la pena resaltar: **el costo de
  incorporar congestión depende fuertemente de cómo está diseñado el
  heurístico base, no es un costo fijo del fenómeno en sí**.

## 6. Sensibilidad paramétrica: V pesa más que N en estrés

- Tabla 6 + los 4 scatters (`hc_2`/N, `aco_2`/V, `hc_3`/V, `aco_3`/N).
- En estrés, `V` (tamaño de grafo) correlaciona más fuerte con el tiempo que
  `N` (cantidad de pedidos) tanto en `hc_2` (r=0.68) como `aco_2` (r=0.71).
- En normal es al revés: `N` pesa más que `V` (`hc_2` r=0.57 vs. 0.33).
- Confirma la hipótesis original de `specs/model_analysis.md` sec. 5
  ("asintotismo exponencial vs. V") — pero solo se manifiesta a escala de
  estrés, no en instancias chicas.
- Muestras: `hc_2` n=32, `hc_3` n=20 (confiables); `aco_2` n=15 (razonable);
  `aco_3` n=7 (chica — aclarar como limitación, no ocultar).

## Hallazgo transversal: el bug de construcción de rutas de ACO

No es parte de una sección del pipeline, pero sostiene por qué la
comparación ACO2/ACO3 es válida y por qué el N=7 de `aco_3` es un reflejo
real, no un artefacto:

- Construcción original: caminata aleatoria sin revisitas + BFS restrictivo
  al nodo final + exigencia de que **todos** los lotes de una hormiga salgan
  sin loop *a la vez*. Con 25 lotes, probabilidad conjunta ~1e-21 —
  matemáticamente imposible sin importar el presupuesto.
- Fix real (no solo hiperparámetros): permitir revisitar como último
  recurso, reintentar cada lote individualmente hasta 100 veces, con
  rollback del `CongestionTracker` en ACO3.
- Con el fix, `opp_v4`-equivalente de 25 lotes pasó de `infeasible` siempre
  a `optimal` en ~13 min con hiperparámetros default.

## Hallazgo más fuerte todavía: no es infeasibilidad por construcción --
   es que la construcción greedy de HC no tiene vuelta atrás (confirmado
   contra SCIP, 2026-08-27)

Las instancias de ~25+ ubicaciones requeridas por lote (`test_09/10/11`)
siguen sin converger en `opp_hc_2`/`opp_hc_3` -- la hipótesis inicial era
que esas instancias fueran infeasibles por construcción. **Se confirmó
directamente contra SCIP que la hipótesis es incorrecta**:

- Con 2000 órdenes de visita distintos (al azar) sobre el Dijkstra
  determinístico de `opp_hc_2`, **ninguno** encontró una ruta simple para el
  lote de 25 ubicaciones de `test_09` (verificado que el método no tiene un
  bug genérico: en un lote fácil de 4 ubicaciones sí encuentra rutas en
  17/200) -- esto en su momento parecía fuerte evidencia de infeasibilidad.
- **Se corrió `tests/opp_v4/tests/diagnostics/test_single_batch_infeasibility_check.py`
  contra SCIP real** (límite de 1800s, `zimpl` vía conda env `optimizacion`):
  SCIP resuelve ese mismo lote en **1.8 segundos**, `status=optimal`,
  con una ruta simple de 56 nodos (55 arcos, sin loops) que visita las 25
  ubicaciones -- verificado reconstruyendo la ruta desde las variables
  activas. **La instancia es factible.** La ruta óptima recorre la grilla en
  zigzag, sin nada patológico que explique por qué 2000/2000 intentos
  aleatorios de Dijkstra fallaron.
- Conclusión correcta: el problema es que la construcción por
  vecino-más-cercano (Dijkstra greedy, sin backtracking) de
  `opp_hc_2`/`opp_hc_3` puede meterse en un callejón sin salida del que no
  puede deshacer una elección anterior -- y como es 100% determinístico,
  **da igual el orden de visita**: siempre comete el mismo error. Es la
  misma familia de bug que el de construcción de rutas de ACO (self-avoiding
  walk sin retroceso, sección anterior) pero sin la vía de escape que tiene
  ACO (reintento aleatorio por lote con revisita como último recurso) --
  por eso ACO puede llegar a resolver instancias de este tipo con su fix y
  HC nunca, aunque HC sea mucho más rápido en el caso general.
- Esto es un límite real y defendible de la estrategia de construcción de
  HC, no de la instancia ni de una casualidad del generador de escenarios
  -- vale la pena mencionarlo en la tesina como una limitación conocida del
  enfoque greedy sin backtracking, con evidencia directa (SCIP resuelve en
  ~2s lo que HC nunca resuelve).
- Se discutió permitir ciclos en las rutas como fix general, pero se
  decidió no implementarlo sin más discusión: rompe la equivalencia de
  restricciones con el exacto a menos que se relaje ahí también (ver
  `analysis/README.md` sección "Sobre permitir ciclos en las rutas"). Buen
  candidato para la sección de "trabajo futuro" de la tesina -- por ejemplo,
  agregar backtracking real (no solo revisita aleatoria) a la construcción
  greedy de HC.

---

## Pendiente antes de dar esto por cerrado

1. **Re-correr `opp_aco_2`/`opp_aco_3` en estrés** con el fix de performance
   (sección 2) -- los números actuales del reporte son de la versión lenta.
   *(En curso, 2026-08-27: Lucia corriendo de a poco.)*
2. ~~Correr `test_single_batch_infeasibility_check.py` contra SCIP~~ --
   **hecho (2026-08-27)**: `status=optimal` en 1.8s, hipótesis de
   infeasibilidad por construcción **refutada**. Ver hallazgo actualizado
   arriba.
3. Con (1) ya se puede escribir la sección de resultados sin tener que
   volver a corregirla después.
