# Pipeline de análisis de resultados

`analysis/` **no ejecuta los tests**: lee lo que ya está en `results/<modelo>/<functional|stress>/*.csv`
y construye la comparabilidad entre los cuatro modelos (`opp_split`, `opp_mono`, `opp_hc`, `opp_aco`)
y los estudios de las heurísticas.

## 1. Generar los datos

```bash
export WRITE_RESULTS_CSV=1          # un CSV por corrida en results/<modelo>/<tier>/
export WRITE_SOLUTIONS=1            # solo opp_hc / opp_aco: guarda cada solución (para verification/)

python -m tests.run_suite opp_hc functional
python -m tests.run_suite opp_hc stress
python -m tests.run_suite opp_aco functional
python -m tests.run_suite opp_aco stress
python -m tests.run_suite opp_split functional      # necesita zimpl
python -m tests.run_suite opp_mono functional
```

`--id NN` corre un solo caso (por ejemplo `python -m tests.run_suite opp_hc stress --id 04`).
Los resultados consolidados que cuentan (los que lee `analysis/load.py`) están declarados en
`analysis/config.py` (`LATEST_FILE_OVERRIDES`): archivos de nombre fijo, sin fecha.

## 2. Qué hay en `analysis/`

| Archivo | Qué hace |
| --- | --- |
| `config.py` | Mapa de modelos a directorios de `results/`, y qué CSV cuenta para cada `(modelo, escenario)`. |
| `load.py` | Descubre y concatena los CSV en un DataFrame (una fila por ejecución de un test; el `instance` es el nombre del método, igual en los cuatro modelos). Si falta un `(modelo, escenario)` lo informa por consola. |
| `comparability.py` | El registro de **qué resultados del Split y de las heurísticas se pueden comparar** y el cruce con los últimos resultados. Ver `docs/specs/comparabilidad_split_heuristicas.md`. |
| `run_hc_budget_study.py` | Estudio del presupuesto de búsqueda de OPP-HC (`Max_it`, `Max_imp`). |
| `run_aco_ablation_study.py` | Ablación de los componentes híbridos de OPP-ACO (colonia sola, + búsqueda de rutas, + búsqueda de secuencia). |
| `run_aco_pheromone_study.py` | Sensibilidad de OPP-ACO a `alpha`, `beta` y `rho`. |
| `run_aco_seed_study.py` | Cuánto cambia el resultado de OPP-ACO con la semilla. |
| `run_equal_time_study.py` | Comparación a tiempo igual: cada modelo exacto corre el mismo tiempo que tardó la heurística. |
| `aco_study_common.py` | Utilidades de los estudios de OPP-ACO. |

Los estudios no son tests: cada uno escribe en `results/<modelo>/<estudio>/` (`ablation`, `pheromone`,
`seeds`, `budget`) o en `results/equal_time/`. Ejemplos:

```bash
PYTHONHASHSEED=0 python -m analysis.run_aco_ablation_study --id 04 --seeds 1 2 3
PYTHONHASHSEED=0 python -m analysis.run_aco_pheromone_study --id 06
python -m analysis.run_aco_seed_study --id 04 06 --seeds 1 2 --workers 2
python -m analysis.run_hc_budget_study --id 03 17 18 --seeds 1 2
python -m analysis.run_equal_time_study --budget-from opp_hc --id 04 05
```

El `--id` es el número del escenario de estrés (`tests/stress_cases/case_NN.py`).

## 3. Comparabilidad

```bash
python -m analysis.comparability
```

Escribe `results/comparability/comparability_split_vs_heuristics.csv` (el registro por instancia: qué
se puede comparar en estado y en objetivo, y por qué no cuando no) y
`results/comparability/results_split_vs_heuristics.csv` (el registro cruzado con los resultados de
`opp_aco` y `opp_hc`: objetivo, tiempo, `gap_pct`, `speedup`, `status_matches`). Toda tabla o gráfico
comparativo debe filtrar por `comparable_status` / `comparable_objective`.

La verificación de las soluciones de las heurísticas contra `opp_mono` (`verification/run_compliance.py`)
y la comparación entre `opp_split` y `opp_mono` (`verification/compare_split_vs_mono.py`) escriben en
`results/compliance/` y `results/comparability/compare_split_vs_mono.csv`.
