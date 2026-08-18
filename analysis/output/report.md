# Reporte de comparación de modelos

## 1. Tasa de éxito / convergencia

| model | scenario | total | ok | timeout | failed | success_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 48 | 48 | 0 | 0 | 100.0 |
| opp_aco_3 | normal | 12 | 12 | 0 | 0 | 100.0 |
| opp_hc_2 | normal | 46 | 46 | 0 | 0 | 100.0 |
| opp_hc_3 | normal | 6 | 6 | 0 | 0 | 100.0 |
| opp_v4 | normal | 44 | 43 | 1 | 0 | 97.7 |

## 2. Tiempo de ejecución (solo casos OK)

| model | scenario | mean_time | std_time | max_time | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 0.23610588908195493 | 0.327672399058028 | 1.4354429244995115 | 48 |
| opp_aco_3 | normal | 0.025555570920308385 | 0.04387347950663957 | 0.1223242282867431 | 12 |
| opp_hc_2 | normal | 0.008851419324460201 | 0.0043273053102638 | 0.0224010944366455 | 46 |
| opp_hc_3 | normal | 0.0038505395253499003 | 0.002514931435436244 | 0.0064420700073242 | 6 |
| opp_v4 | normal | 2.5023141295410865 | 7.092974958272934 | 29.40972781181335 | 43 |

## 3. Profiling del modelo exacto (opp_v4)

| scenario | mean_total_time | mean_solver_time | n | solver_ratio_pct | overhead_ratio_pct |
| --- | --- | --- | --- | --- | --- |
| normal | 2.5023141295410865 | 2.3012240820152816 | 43 | 92.0 | 8.0 |

## 4. Gap de optimalidad vs. opp_v4

| model | scenario | mean_gap_pct | median_gap_pct | std_gap_pct | max_gap_pct | n_matched |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 71.22773178525641 | 0.0 | 199.87217644020114 | 472.0 | 9 |
| opp_hc_2 | normal | 242.22025794370185 | 0.0 | 533.1439832436165 | 1180.0 | 9 |

## 5. Congestión (opp_hc_3 / opp_aco_3 vs. sus baselines v2)

### 5.1 Espera media por congestión

| model | scenario | mean_congestion_wait | std_congestion_wait | max_congestion_wait | n | congestion_modeled |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | nan | nan | nan | 0 | False |
| opp_aco_3 | normal | 0.75 | 1.5 | 3.0 | 4 | True |
| opp_hc_2 | normal | nan | nan | nan | 0 | False |
| opp_hc_3 | normal | 1.0 | 1.7320508075688772 | 3.0 | 3 | True |
| opp_v4 | normal | nan | nan | nan | 0 | False |

### 5.2 Sobrecosto de tiempo por modelar congestión

| scenario | mean_time_overhead_pct | n_matched | aware_model | baseline_model |
| --- | --- | --- | --- | --- |
| normal | -15.574779336779315 | 1 | opp_hc_3 | opp_hc_2 |
| normal | 99.5794968744288 | 1 | opp_aco_3 | opp_aco_2 |

## 6. Sensibilidad paramétrica (correlación de Pearson con total_time)

### 6.1 Nivel global (normal + estrés)

| model | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | 0.4544 | 0.4759 | 0.5016 | 0.0808 | -0.015 | -0.496 | 48 |
| opp_aco_3 | 0.2256 | 0.2256 | 0.9256 | -0.6652 | nan | 0.6652 | 4 |
| opp_hc_2 | 0.5745 | 0.3289 | 0.2616 | 0.0451 | -0.077 | -0.4117 | 46 |
| opp_hc_3 | 0.9629 | 0.9629 | nan | 0.9629 | nan | -0.9629 | 3 |
| opp_v4 | 0.843 | 0.4845 | 0.9182 | -0.0086 | 0.4887 | -0.4204 | 22 |

### 6.2 Nivel escenario

| model | scenario | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 0.4544 | 0.4759 | 0.5016 | 0.0808 | -0.015 | -0.496 | 48 |
| opp_aco_3 | normal | 0.2256 | 0.2256 | 0.9256 | -0.6652 | nan | 0.6652 | 4 |
| opp_hc_2 | normal | 0.5745 | 0.3289 | 0.2616 | 0.0451 | -0.077 | -0.4117 | 46 |
| opp_hc_3 | normal | 0.9629 | 0.9629 | nan | 0.9629 | nan | -0.9629 | 3 |
| opp_v4 | normal | 0.843 | 0.4845 | 0.9182 | -0.0086 | 0.4887 | -0.4204 | 22 |

## Gráficos generados

- `mean_time_normal.png`
- `profiling_exact_model.png`
- `quality_gap.png`
- `congestion_wait.png`
