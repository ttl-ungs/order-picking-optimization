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
`tests/outputs/<modelo>/<normal|stress>/*.csv`. Faltan corridas para varios
modelos/escenarios (`opp_hc_2`, `opp_aco_2`, `opp_hc_3`, `opp_aco_3` no
tienen ningún CSV todavía, y `opp_v4` no tiene corrida de estrés). Para
generarlos:

```bash
export WRITE_RESULTS_CSV=1

python tests/opp_v4/execute_tests.py            # opp_v4 normal
python tests/opp_hc_2/execute_tests.py          # opp_hc_2 normal
python tests/opp_hc_2/execute_stress_tests.py   # opp_hc_2 stress
python tests/opp_aco_2/execute_tests.py         # opp_aco_2 normal
python tests/opp_hc_3/execute_tests.py          # opp_hc_3 normal
python tests/opp_aco_3/execute_tests.py         # opp_aco_3 normal
```

Estado real de estrés por modelo (verificado en el repo, no asumido):

- `opp_hc_2`: tiene `execute_stress_tests.py` y casos en `tests/stress/` —
  listo para correr.
- `opp_v4`: tiene la carpeta `tests/opp_v4/tests/stress/` pero está vacía
  (solo `__init__.py`) y no hay `execute_stress_tests.py` — faltan escribir
  los casos de estrés antes de poder correrlos. Sin esto, la sección 3
  (profiling) y el gap de calidad en estrés quedan cojos.
- `opp_aco_2`, `opp_hc_3`, `opp_aco_3`: no tienen ni carpeta `tests/stress/`
  ni script de ejecución todavía — hay que crearlos siguiendo el patrón de
  `opp_hc_2` (reusar los mismos escenarios de estrés que ya existen para
  `opp_hc_2`/`opp_v3`, adaptando el DTO de cada modelo).

Los tests de estrés en el modelo exacto pueden tardar varios minutos por
instancia — correrlos con tiempo de sobra.

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
   contra `obj_val` del exacto en las *mismas* instancias (join por nombre de
   método de test, que es compartido entre variantes del modelo). Sin esto,
   "más rápido" no dice si la heurística además da soluciones razonables.
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
