# Reporte de comparación de modelos

## 1. Tasa de éxito / convergencia

| model | scenario | total | ok | timeout | failed | success_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 48 | 48 | 0 | 0 | 100.0 |
| opp_aco_2 | stress | 11 | 8 | 2 | 1 | 72.7 |
| opp_aco_3 | normal | 12 | 12 | 0 | 0 | 100.0 |
| opp_aco_3 | stress | 11 | 4 | 5 | 2 | 36.4 |
| opp_hc_2 | normal | 46 | 46 | 0 | 0 | 100.0 |
| opp_hc_2 | stress | 34 | 23 | 11 | 0 | 67.6 |
| opp_hc_3 | normal | 6 | 6 | 0 | 0 | 100.0 |
| opp_hc_3 | stress | 11 | 8 | 3 | 0 | 72.7 |
| opp_v4 | normal | 44 | 43 | 1 | 0 | 97.7 |
| opp_v4 | stress | 8 | 1 | 7 | 0 | 12.5 |

## 2. Tiempo de ejecución (solo casos OK)

| model | scenario | mean_time | std_time | max_time | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 0.23610588908195493 | 0.327672399058028 | 1.4354429244995115 | 48 |
| opp_aco_2 | stress | 508.2595696747303 | 479.06542914003273 | 1444.3947761058807 | 8 |
| opp_aco_3 | normal | 0.025555570920308385 | 0.04387347950663957 | 0.1223242282867431 | 12 |
| opp_aco_3 | stress | 669.5413167476654 | 1018.6434971662344 | 2185.4849269390106 | 4 |
| opp_hc_2 | normal | 0.008851419324460201 | 0.0043273053102638 | 0.0224010944366455 | 46 |
| opp_hc_2 | stress | 23.28625359742538 | 63.480850213385985 | 296.41067695617676 | 23 |
| opp_hc_3 | normal | 0.0038505395253499003 | 0.002514931435436244 | 0.0064420700073242 | 6 |
| opp_hc_3 | stress | 2.6666124165058136 | 3.0417344777546083 | 8.85811710357666 | 8 |
| opp_v4 | normal | 2.5023141295410865 | 7.092974958272934 | 29.40972781181335 | 43 |
| opp_v4 | stress | 0.1135659217834472 | nan | 0.1135659217834472 | 1 |

## 3. Profiling del modelo exacto (opp_v4)

| scenario | mean_total_time | mean_solver_time | n | solver_ratio_pct | overhead_ratio_pct |
| --- | --- | --- | --- | --- | --- |
| normal | 2.5023141295410865 | 2.3012240820152816 | 43 | 92.0 | 8.0 |
| stress | 0.1135659217834472 | 0.0 | 1 | 0.0 | 100.0 |

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
| opp_aco_2 | stress | nan | nan | nan | 0 | False |
| opp_aco_3 | normal | 0.75 | 1.5 | 3.0 | 4 | True |
| opp_aco_3 | stress | 0.6666666666666666 | 1.1547005383792517 | 2.0 | 3 | True |
| opp_hc_2 | normal | nan | nan | nan | 0 | False |
| opp_hc_2 | stress | nan | nan | nan | 0 | False |
| opp_hc_3 | normal | 1.0 | 1.7320508075688772 | 3.0 | 3 | True |
| opp_hc_3 | stress | 2.5714285714285716 | 3.2071349029490928 | 6.0 | 7 | True |
| opp_v4 | normal | nan | nan | nan | 0 | False |
| opp_v4 | stress | nan | nan | nan | 0 | False |

### 5.2 Sobrecosto de tiempo por modelar congestión

| scenario | mean_time_overhead_pct | n_matched | aware_model | baseline_model |
| --- | --- | --- | --- | --- |
| normal | -15.574779336779315 | 1 | opp_hc_3 | opp_hc_2 |
| stress | -26.515760355899374 | 7 | opp_hc_3 | opp_hc_2 |
| normal | 99.5794968744288 | 1 | opp_aco_3 | opp_aco_2 |
| stress | 236.52930857530566 | 4 | opp_aco_3 | opp_aco_2 |

## 6. Sensibilidad paramétrica (correlación de Pearson con total_time)

### 6.1 Nivel global (normal + estrés)

| model | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | 0.3745 | 0.8742 | 0.3821 | 0.3275 | 0.4978 | -0.318 | 56 |
| opp_aco_3 | 0.9956 | 0.2727 | 0.6532 | 0.9725 | 0.4728 | -0.1787 | 8 |
| opp_hc_2 | 0.5506 | 0.7671 | 0.2891 | 0.6387 | 0.2459 | -0.1757 | 69 |
| opp_hc_3 | 0.3647 | 0.4222 | 0.0525 | 0.769 | 0.4388 | -0.2266 | 11 |
| opp_v4 | 0.7512 | 0.4409 | 0.9152 | -0.0178 | 0.4444 | -0.387 | 23 |

### 6.2 Nivel escenario

| model | scenario | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 0.4544 | 0.4759 | 0.5016 | 0.0808 | -0.015 | -0.496 | 48 |
| opp_aco_2 | stress | -0.0209 | 0.7839 | -0.1306 | -0.051 | nan | nan | 8 |
| opp_aco_3 | normal | 0.2256 | 0.2256 | 0.9256 | -0.6652 | nan | 0.6652 | 4 |
| opp_aco_3 | stress | 0.996 | -0.1672 | 0.5225 | 0.965 | nan | nan | 4 |
| opp_hc_2 | normal | 0.5745 | 0.3289 | 0.2616 | 0.0451 | -0.077 | -0.4117 | 46 |
| opp_hc_2 | stress | 0.4892 | 0.7433 | 0.1437 | 0.6158 | 0.0798 | -0.0798 | 23 |
| opp_hc_3 | normal | 0.9629 | 0.9629 | nan | 0.9629 | nan | -0.9629 | 3 |
| opp_hc_3 | stress | 0.2525 | 0.2875 | -0.1769 | 0.7272 | nan | nan | 8 |
| opp_v4 | normal | 0.843 | 0.4845 | 0.9182 | -0.0086 | 0.4887 | -0.4204 | 22 |

## Gráficos generados

- `mean_time_normal.png`
- `mean_time_stress.png`
- `profiling_exact_model.png`
- `quality_gap.png`
- `congestion_wait.png`
- `scatter_opp_v4_stress_N.png`
- `scatter_opp_hc_2_stress_N.png`
- `scatter_opp_aco_2_stress_V.png`
