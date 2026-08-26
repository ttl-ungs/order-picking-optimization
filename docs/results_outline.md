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

## 2. Tiempo de ejecución: ACO es sistemáticamente más lento que HC

- Tabla 2 + `mean_time_normal.png` / `mean_time_stress.png` (escala log).
- Normal: `hc_2` ~9ms, `hc_3` ~4ms, `aco_2` ~236ms, `aco_3` ~26ms — HC ya es
  1-2 órdenes de magnitud más rápido acá.
- Estrés: `hc_2` ~18s, `hc_3` ~5s, `aco_2` ~595s, `aco_3` ~985s — la brecha
  se agranda, no se achica, con el tamaño de la instancia.
- **Punto a resolver antes de escribir esto como conclusión final**: no es
  el resultado esperado a priori (ACO suele venderse como más rápido que
  búsqueda local por batch). Está en investigación si es inherente al
  diseño (población de hormigas + reintento por lote) o una ineficiencia de
  implementación corregible — ver hallazgo de performance más abajo.

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
- Instancias de ~25+ ubicaciones requeridas por lote (`test_09/10/11`)
  siguen sin converger — pero **tampoco convergen en HC** (ni con su
  algoritmo rápido determinístico), así que es un límite combinatorio real
  de la instancia, no una debilidad puntual de ACO.

---

## Pendiente antes de dar esto por cerrado

Investigando en paralelo (ver mensaje siguiente) si la brecha de tiempo
ACO vs. HC (sección 2) es inherente al diseño o una ineficiencia de
implementación corregible con bajo riesgo. Si es lo segundo, conviene
arreglarlo **antes** de fijar los números de la sección 2 en la tesina —
volver a redactarla después de publicar sería peor que esperar unos
minutos más al profiling.
