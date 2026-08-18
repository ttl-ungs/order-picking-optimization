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
  — correrlos ahí solo quemaría CPU para un timeout garantizado.
- **`opp_aco_2`, `opp_hc_3`, `opp_aco_3` tienen los 11**, con 09/10/11
  gateados detrás de `RUN_LARGE_TESTS=1` (mismo mecanismo que ya usaba
  `opp_hc_2` test #15) porque son instancias pesadas (hasta 750 órdenes /
  5000 nodos) — corren, pero tardan.
- Si se necesita más resolución para la correlación paramétrica, se puede
  ampliar el subconjunto siguiendo el mismo patrón: reusar el *builder* de
  escenario de `opp_hc_2` (`scenario_custom_setup` / `scenario_double_grid` /
  `scenario_six_missions_two_periods_grid_graph`, todos funciones puras sin
  acoplamiento a ningún modelo) y copiar los parámetros numéricos del test
  original de `opp_hc_2`/`opp_v3` que se quiera portar.

### Nota sobre ACO en estrés

Al portar el test 04 a `opp_aco_2`, con los hiperparámetros default (15
hormigas, 60 iteraciones) el algoritmo **no encuentra solución factible** en
esa instancia (misma instancia donde `opp_hc_2` sí converge). No es un bug
del test: el propio historial de `opp_aco` (v1) ya tiene ese mismo resultado
registrado (`status=failed`) en
`tests/outputs/opp_aco/stress/output_opp_aco_stress_tests_20260617_123001.csv`
para ese escenario y para la mayoría de las instancias medianas/grandes. Es
en sí mismo un hallazgo real para la tesina — la tasa de éxito de ACO se
degrada en estrés bajo estos hiperparámetros — y la sección 1 del pipeline
(tasa de éxito/convergencia) está pensada justamente para cuantificarlo, no
para esconderlo ajustando parámetros hasta que "pase".

Los tests de estrés en el modelo exacto pueden tardar varios minutos por
instancia — correrlos con tiempo de sobra. `opp_v4` requiere el binario
`zimpl` instalado y en el `PATH` (no verificado en este sandbox: los tests
nuevos compilan y siguen exactamente el patrón de los tests normales de
`opp_v4`, que tampoco corren aquí por la misma razón).

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
