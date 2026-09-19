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
- `opp_v4` (exacto): 97.8% en normal (45/46), 12.5% en estrés (1/8).
  Ninguna instancia no-trivial converge dentro de 25 min.
- Heurísticas en estrés (**datos finales, post-auditoría de código
  completa, 2026-08-30** -- performance + los 5 bugs corregidos en HC/ACO,
  ver `analysis/README.md`): `opp_hc_3` 85%, `opp_aco_2` 85%, `opp_aco_3`
  **85%** (subió de 70% pre-fix), `opp_hc_2` 74.4% (43/43, la batería más
  grande, sin cambio respecto a antes de los fixes -- confirmado con
  datos, no solo por inferencia).
- `aco_3` es el único que cambió de tasa de éxito con la auditoría de
  código (70%→85%) -- consistente con lo esperado: sus fixes (#3 visibilidad
  ciega a distancia, #4 secuenciación EDD, #7 asimetría elitista) atacaban
  directamente su capacidad de converger. `hc_2`/`hc_3`/`aco_2` se
  mantuvieron estables porque sus fixes (#1/#2 HC, #4 ACO) no apuntaban a
  la tasa de convergencia en sí.
- Conclusión: el modelo exacto deja de ser viable apenas se sale de
  instancias de juguete — sustenta la necesidad de heurísticos para
  cualquier caso de uso real. Entre los heurísticos, hay una jerarquía
  clara que **no** es "todos convergen igual".

## 2. Tiempo de ejecución (datos finales, post-auditoría de código, 2026-08-30)

- Tabla 2 + `mean_time_normal.png` / `mean_time_stress.png` (escala log).
- Estrés, media de tiempo (solo casos `ok`): `opp_hc_3` **0.56s** (bajó de
  4.96s -- el fix del BFS de dos niveles también acelera el camino feliz,
  ver más abajo), `opp_hc_2` **2.97s** (bajó de 18.3s, mismo motivo),
  `opp_aco_2` 54.8s (~sin cambio vs. 52.6s), `opp_aco_3` **176.5s** (bajó de
  274.5s -- converge más rápido además de más seguido, ver hallazgo de
  congestión más abajo).
- El ranking **no se invierte**: HC sigue siendo bastante más rápido que
  ACO en ambos pares (`hc_2` < `aco_2`, `hc_3` < `aco_3`). Tiene sentido --
  HC construye la ruta una sola vez de forma greedy; ACO repite la
  construcción `A_ants × Max_it` veces por definición del algoritmo, así
  que aun con el mismo costo por paso arreglado, hace muchísimo más
  trabajo total. Los fixes de performance/auditoría cerraron brechas
  anormales (bugs), no la brecha estructural esperada entre construir una
  ruta y buscar entre muchas.
- Normal ya era rápido en los 4 heurísticos (ms) y no cambió la conclusión
  ahí.

**Aclaración (2026-08-28): "más lento" no es "peor" -- es el trade-off
esperado, y los datos ya lo muestran en las otras dos dimensiones.** Es
tentador leer estos tiempos como "ACO es peor que HC" porque en teoría es
un algoritmo más sofisticado -- pero eso confunde "más avanzado" con
"gana en todo". Comparando por dimensión, cada algoritmo gana donde su
propio diseño predice que debería ganar:

| Dimensión | HC | ACO | Gana |
| --- | --- | --- | --- |
| Velocidad (estrés) | más rápido | más lento (`A_ants × Max_it` construcciones vs. una sola) | HC |
| Calidad (gap vs. exacto, normal, sección 4) | media 242% | media 71% | ACO |
| Tasa de éxito (estrés, sección 1) | 74.4% | 85% | ACO |

HC es rápido porque hace poco trabajo por corrida (una construcción greedy
+ búsqueda local acotada) -- pero por eso mismo queda atrapado sin salida
cuando esa construcción se mete en un callejón sin salida (el bug de BFS y
el de construcción sin backtracking, ambos documentados arriba). ACO paga
en tiempo exactamente lo que le compra en robustez y calidad: muchas
hormigas, muchas iteraciones, reintentos con revisita. Si ACO fuera
también más rápido *y* de mejor calidad *y* más robusto, ahí sí habría
algo sospechoso (una comparación injusta, o HC mal implementado). El
patrón que muestran los datos -- cada uno gana en la dimensión que su
propio diseño predice -- es el resultado esperado, no una debilidad de
ACO. Conclusión a favor de la tesina: no "ACO es peor", sino "ACO cambia
tiempo de cómputo por calidad y robustez frente a HC -- la elección
depende de qué recurso es más escaso en el caso de uso real".

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
- Sobrecosto de tiempo por modelar congestión, estrés (**datos finales,
  2026-08-30**): `opp_hc_3` **+18.5%** vs. `opp_hc_2` (subió del +0.05%
  "dentro del ruido" que se veía antes -- con el fix del BFS de dos
  niveles, `hc_2` se volvió mucho más rápido en el camino feliz, así que el
  costo fijo de simular congestión en `hc_3` ahora se nota proporcionalmente
  más, aunque en términos absolutos sigue siendo chico: 0.56s vs. 2.97s de
  media); `opp_aco_3` **+231%** vs. `opp_aco_2` (bajó bastante del +513%
  pre-auditoría -- los fixes #3/#4/#7 hicieron que `aco_3` converja más
  rápido Y más seguido, así que el sobrecosto relativo se achicó aunque
  sigue siendo grande).
- La asimetría central del hallazgo se mantiene igual de clara con los
  datos finales: `hc_3` paga un costo chico y estable por modelar
  congestión (~20% en el peor caso medido), `aco_3` paga un costo grande
  (~230%) -- la arquitectura importa mucho más que cualquier detalle de
  implementación puntual.
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
  **Datos finales, 2026-08-30** (post-auditoría de código completa, todos
  los `n` de estrés en su valor final).
- En estrés, `V` (tamaño de grafo) correlaciona más fuerte con el tiempo que
  `N` (cantidad de pedidos) en `hc_2` (r=0.63) y `aco_2` (r=0.71).
- `hc_3` en estrés: V (-0.07) y N (0.65) -- **ahora N domina claramente**,
  al revés de lo que se veía antes del fix del BFS (V/N parecidos, sin
  dominancia clara). Con el camino feliz mucho más rápido, el tiempo pasó
  a estar dominado por cuántos lotes/pedidos hay que procesar, no por
  cuánto cuesta cada paso de construcción de ruta en el grafo.
  `aco_3` en estrés **sigue rompiendo el patrón de hc_2/aco_2**: N (0.53)
  domina sobre V (0.27) -- mismo patrón que antes del fix (era N=0.58 vs.
  V=0.24), consistente con la hipótesis de que en `aco_3` el costo por
  paso no es solo "moverse en el grafo" sino también el switch
  probabilístico τ1/τ2 y el chequeo de congestión, que escalan más con N.
- En normal es al revés en `hc_2`: `N` pesa más que `V` (r=0.57 vs. 0.33).
- Confirma la hipótesis original de `specs/model_analysis.md` sec. 5
  ("asintotismo exponencial vs. V") para `hc_2`/`aco_2` -- pero solo se
  manifiesta a escala de estrés, no en instancias chicas, y no es universal
  entre los 4 heurísticos (`hc_3` y `aco_3` son ahora ambos la excepción,
  cada uno por su propio motivo).
- Muestras en estrés (finales): `hc_2` n=32, `hc_3` n=17, `aco_2` n=17,
  `aco_3` n=17 (subió de 14) -- las cuatro muestras ya son de tamaño
  razonable, ninguna es chica al punto de aclarar como limitación fuerte.

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
- **Se corrió `tests/opp_v4/diagnostics/test_case_single_batch_infeasibility_check.py`
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

3. ~~Auditoría de código encontró y corrigió bugs reales en HC/ACO (7
   hallazgos entre el 2026-08-27 y 2026-08-28), + un bug crítico en
   `analysis/load.py`/`metrics.py`~~ -- **hecho, con las 4 baterías de
   estrés re-corridas y consolidadas (2026-08-30)**. Ver
   `analysis/README.md` secciones "Auditoría de código, partes 1-4" para
   el detalle completo de cada fix. Resultado: `aco_3` 70%→85% de éxito
   (cambio real), `hc_2`/`hc_3`/`aco_2` estables en tasa de éxito pero con
   tiempos bastante más rápidos en HC (el fix del BFS también acelera el
   camino feliz, no solo corrige el caso raro que lo motivó).

**Estado final: no queda ninguna re-corrida pendiente** para los 5 modelos
con datos completos (`opp_v4`, `opp_hc_2`, `opp_hc_3`, `opp_aco_2`,
`opp_aco_3`). Excepciones documentadas y aceptadas: `opp_v4` en estrés
sigue con el dataset de 2026-08-18 (8 tests, no se re-corrió porque tomaría
horas y los fixes de esta auditoría no tocan `opp_v4`, que es exacto vía
SCIP, no heurístico); `opp_v5` sigue fuera del alcance mientras está en
construcción. Con esto, `docs/results_outline.md` está listo para pasar de
bosquejo a texto real de la sección de resultados.
