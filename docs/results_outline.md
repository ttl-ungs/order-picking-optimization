# Bosquejo — Sección de Resultados

Estructura sugerida, un sub-apartado por cada sección del pipeline
(`analysis/output/report.md`). Cada uno: **qué muestra el dato**, **qué
gráfico/tabla citar**, **qué conclusión defendible se puede escribir**.

## Encuadre metodológico: por qué los modelos simples (`hc_2`/`aco_2`/`v4`)
   siguen siendo necesarios aunque existan versiones más complejas

Vale la pena dejar esto explícito antes de leer el resto, porque no es
obvio a primera vista: con `hc_3`/`aco_3` (congestión) y `v5` (descomposición
en 2 etapas, velocidad heterogénea, cadena de frío) ya en el repositorio, uno
podría pensar que `hc_2`/`aco_2`/`v4` quedaron "atrás" -- versiones más
simples que la complejidad más reciente dejó obsoletas. Es al revés: son el
**grupo de control** que hace que las comparaciones con los modelos
complejos signifiquen algo.

- El diseño real del proyecto agrega **una sola variable por vez** sobre un
  par base:
  ```
  hc_2  ──(+congestión)────────────────────> hc_3
  aco_2 ──(+congestión)────────────────────> aco_3
  v4    ──(+2 etapas, +V_p, +cadena de frío)> v5
  ```
- Esto es diseño experimental controlado, no un descuido. El resultado que
  más vale la pena resaltar de todo el análisis (sección 5, el costo de
  modelar congestión) **no existiría sin el par simple**: `hc_3` +0.05% vs.
  `aco_3` +513% frente a sus baselines solo es interpretable porque hay un
  `hc_2`/`aco_2` sin congestión contra el cual restar. Lo mismo aplica a
  `v5`: la pregunta que lo hace valioso no es "¿v5 es mejor que v4?" en
  abstracto, es "¿la descomposición en 2 etapas ayuda a que el exacto
  escale?" -- y esa pregunta necesita que `v4` siga existiendo tal cual,
  como referencia fija.
- La alternativa (que cada modelo tuviera todas las features combinadas)
  no aportaría más rigor, lo diluiría: con features mezcladas no se puede
  atribuir ningún efecto a ninguna causa en particular, y el costo en
  trabajo escala combinatoriamente (features × arquitecturas) sin ningún
  beneficio metodológico a cambio -- se evaluó concretamente cuánto costaría
  sumarle velocidad heterogénea y cadena de frío a `hc_2`/`aco_2` (~1 día de
  trabajo por los dos, entre código core, escenarios/tests nuevos y
  regresión) y se decidió no hacerlo por este motivo, no por falta de
  tiempo.
- Consecuencia práctica: sin `hc_2`/`aco_2` tampoco habría muestra grande
  para el gap de calidad contra `v4` (sección 4 -- son los heurísticos más
  rápidos de correr, de ahí la mayor cantidad de instancias comparables), ni
  existiría el hallazgo del bug de construcción de rutas (sección
  "Hallazgo transversal" -- se encontró comparando la versión simple, que
  debería ser la más confiable, contra el exacto).
- Para la tesina: dejar esto como una **decisión de diseño metodológico
  explícita**, no como una limitación a disculpar -- cada complejidad se
  aísla a propósito contra su par simple, en vez de perseguir el modelo más
  realista posible.

## 1. Convergencia: el exacto no escala, las heurísticas sí (con matices)

- Tabla 1 + `mean_time_stress.png`.
- `opp_v4` (exacto): 97.7% en normal, **12.5% en estrés** (1/8). Ninguna
  instancia no-trivial converge dentro de 25 min.
- Heurísticas en estrés (post-fix de performance, 2026-08-27): `opp_hc_3`
  85%, `opp_aco_2` 85%, `opp_hc_2` 74.4% (batería de 34, la más grande),
  `opp_aco_3` 70%. `aco_2`/`aco_3` subieron su tasa de éxito respecto a la
  medición pre-fix (75%→85% y 35%→70%) -- con rutas más rápidas de
  construir, menos instancias pegan contra el timeout externo antes de que
  el algoritmo termine de converger.
- Conclusión: el modelo exacto deja de ser viable apenas se sale de
  instancias de juguete — sustenta la necesidad de heurísticos para
  cualquier caso de uso real. Entre los heurísticos, hay una jerarquía
  clara que **no** es "todos convergen igual".

## 2. Tiempo de ejecución (datos post-fix de performance, 2026-08-27)

- Tabla 2 + `mean_time_normal.png` / `mean_time_stress.png` (escala log).
- Estrés, media de tiempo (solo casos `ok`): `opp_hc_3` 4.96s, `opp_hc_2`
  18.3s, `opp_aco_2` **52.6s** (antes 595s, ~11x), `opp_aco_3` **274.5s**
  (antes 985s, ~3.6x).
- El fix de performance (sección siguiente) mejora mucho los tiempos
  absolutos de ACO, pero **no invierte el ranking**: HC sigue siendo
  bastante más rápido que ACO en ambos pares (`hc_2` < `aco_2`, `hc_3` <
  `aco_3`). Tiene sentido -- HC construye la ruta una sola vez de forma
  greedy; ACO repite la construcción `A_ants × Max_it` veces por
  definición del algoritmo, así que aun con el mismo costo por paso
  arreglado, hace muchísimo más trabajo total. El fix cerró la brecha que
  era "anormal" (el bug O(V) por paso), no la brecha estructural esperada
  entre construir una ruta y buscar entre muchas.
- Normal ya era rápido en los 4 heurísticos (ms) y no cambió la conclusión
  ahí.

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
- Sobrecosto de tiempo por modelar congestión, estrés (post-fix,
  2026-08-27): `opp_hc_3` +0.05% (dentro del ruido) vs. `opp_hc_2`;
  `opp_aco_3` **+513%** vs. `opp_aco_2` (subió del +263% medido antes del
  fix -- no porque `aco_3` haya empeorado en términos absolutos, sino
  porque `aco_2` mejoró mucho más en términos relativos: el fix ayuda más
  cuanto más simple es la construcción de ruta por paso, y `aco_2` no paga
  el switch probabilístico τ1/τ2 que sí paga `aco_3`. La asimetría entre
  arquitecturas es todavía más marcada con datos correctos, no menos).
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

## 6. Sensibilidad paramétrica: V pesa más que N en estrés (matiz: no en aco_3)

- Tabla 6 + los 4 scatters (`hc_2`/N, `aco_2`/V, `hc_3`/V, `aco_3`/N).
  Números post-fix de performance (2026-08-27, más instancias `ok` que
  antes al bajar el timeout externo).
- En estrés, `V` (tamaño de grafo) correlaciona más fuerte con el tiempo que
  `N` (cantidad de pedidos) en `hc_2` (r=0.68) y `aco_2` (r=0.70).
- `hc_3` en estrés: V (0.23) y N (0.17) parecidos, sin dominancia clara.
  `aco_3` en estrés **rompe el patrón**: N (0.58) domina sobre V (0.24) --
  lo opuesto a `aco_2`. Posible explicación: en `aco_3` el costo por paso ya
  no es solo "moverse en el grafo" sino también el switch probabilístico
  τ1/τ2 y el chequeo de congestión, que escalan más con la cantidad de
  pedidos/lotes a programar (N) que con el tamaño del grafo (V) -- hipótesis
  a mencionar como tal, no como conclusión firme dado el n chico.
- En normal es al revés en `hc_2`: `N` pesa más que `V` (r=0.57 vs. 0.33).
- Confirma la hipótesis original de `specs/model_analysis.md` sec. 5
  ("asintotismo exponencial vs. V") para `hc_2`/`aco_2` -- pero solo se
  manifiesta a escala de estrés, no en instancias chicas, y no es universal
  entre los 4 heurísticos (`aco_3` es la excepción).
- Muestras en estrés (post-fix): `hc_2` n=32, `hc_3` n=17, `aco_2` n=17
  (subió de 15), `aco_3` n=14 (subió bastante de 7 -- ya no es una muestra
  tan chica, aunque sigue siendo la más chica de las cuatro).

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
- **Decisión (2026-08-27): no se implementa ningún fix para esto.** Se
  evaluaron dos opciones concretas -- (a) en HC, caer a resolver el lote
  puntual como sub-problema exacto vía SCIP cuando el greedy falla (~2s,
  ya demostrado que funciona, pero le agrega a HC una dependencia de
  `zimpl`/SCIP y cambia su naturaleza de heurístico puro); (b) en ACO,
  agregar lookahead a la selección de vecino en vez de solo reintentar al
  azar -- y se decidió dejarlo documentado como limitación conocida en vez
  de implementarlas: el hallazgo es válido y defendible tal cual ("HC/ACO
  tienen un límite estructural de construcción, demostrado contra SCIP") y
  no compromete los stress tests ya corridos ni los que están en curso.

---

## Pendiente antes de dar esto por cerrado

1. ~~Re-correr `opp_aco_2`/`opp_aco_3` en estrés con el fix de
   performance~~ -- **hecho (2026-08-27)**: `aco_2` 595s→52.6s (~11x,
   75%→85% éxito), `aco_3` 985s→274.5s (~3.6x, 35%→70% éxito). Pipeline
   regenerado, `analysis/output/report.md` y este bosquejo ya reflejan los
   números nuevos.
2. ~~Correr `test_single_batch_infeasibility_check.py` contra SCIP~~ --
   **hecho (2026-08-27)**: `status=optimal` en 1.8s, hipótesis de
   infeasibilidad por construcción **refutada**. Ver hallazgo actualizado
   arriba.

Con (1) y (2) resueltos, ya no queda ningún dato pendiente de re-correr --
se puede pasar a escribir la sección de resultados de la tesina a partir de
este bosquejo.
