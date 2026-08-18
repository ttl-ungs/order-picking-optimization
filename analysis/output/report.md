# Reporte de comparación de modelos

## 1. Tasa de éxito / convergencia

| model | scenario | total | ok | timeout | failed | success_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| opp_v4 | normal | 21 | 21 | 0 | 0 | 100.0 |

## 2. Tiempo de ejecución (solo casos OK)

| model | scenario | mean_time | std_time | max_time | n |
| --- | --- | --- | --- | --- | --- |
| opp_v4 | normal | 2.3025635537647067 | 6.58383973717829 | 22.104615926742554 | 21 |

## 3. Profiling del modelo exacto (opp_v4)

| scenario | mean_total_time | mean_solver_time | n | solver_ratio_pct | overhead_ratio_pct |
| --- | --- | --- | --- | --- | --- |
| normal | 2.3025635537647067 | 2.2072848592485697 | 21 | 95.9 | 4.1 |

## 4. Gap de optimalidad vs. opp_v4

_(sin datos)_

## 5. Congestión (opp_hc_3 / opp_aco_3 vs. sus baselines v2)

### 5.1 Espera media por congestión

| model | scenario | mean_congestion_wait | std_congestion_wait | max_congestion_wait | n | congestion_modeled |
| --- | --- | --- | --- | --- | --- | --- |
| opp_v4 | normal | nan | nan | nan | 0 | False |

### 5.2 Sobrecosto de tiempo por modelar congestión

_(sin datos)_

## 6. Sensibilidad paramétrica (correlación de Pearson con total_time)

### 6.1 Nivel global (normal + estrés)

| model | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| opp_v4 | 0.9174 | 0.4853 | 0.9233 | -0.0247 | 0.4759 | -0.4509 | 19 |

### 6.2 Nivel escenario

| model | scenario | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_v4 | normal | 0.9174 | 0.4853 | 0.9233 | -0.0247 | 0.4759 | -0.4509 | 19 |

## Gráficos generados

- `mean_time_normal.png`
- `profiling_exact_model.png`
- `congestion_wait.png`
