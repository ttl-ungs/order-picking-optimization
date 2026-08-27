# Reporte de comparación de modelos

## 1. Tasa de éxito / convergencia

| model | scenario | total | ok | timeout | failed | success_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 48 | 48 | 0 | 0 | 100.0 |
| opp_aco_2 | stress | 20 | 17 | 1 | 2 | 85.0 |
| opp_aco_3 | normal | 12 | 12 | 0 | 0 | 100.0 |
| opp_aco_3 | stress | 20 | 14 | 1 | 5 | 70.0 |
| opp_hc_2 | normal | 46 | 46 | 0 | 0 | 100.0 |
| opp_hc_2 | stress | 43 | 32 | 11 | 0 | 74.4 |
| opp_hc_3 | normal | 6 | 6 | 0 | 0 | 100.0 |
| opp_hc_3 | stress | 20 | 17 | 3 | 0 | 85.0 |
| opp_v4 | normal | 44 | 43 | 1 | 0 | 97.7 |
| opp_v4 | stress | 8 | 1 | 7 | 0 | 12.5 |
| opp_v5 | normal | 28 | 28 | 0 | 0 | 100.0 |
| opp_v5 | stress | 3 | 0 | 3 | 0 | 0.0 |

## 2. Tiempo de ejecución (solo casos OK)

| model | scenario | mean_time | std_time | max_time | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 0.23610588908195493 | 0.327672399058028 | 1.4354429244995115 | 48 |
| opp_aco_2 | stress | 52.626901879030115 | 51.50154927523458 | 159.47207021713257 | 17 |
| opp_aco_3 | normal | 0.025555570920308385 | 0.04387347950663957 | 0.1223242282867431 | 12 |
| opp_aco_3 | stress | 274.496099284717 | 288.75962323931503 | 1020.2660281658171 | 14 |
| opp_hc_2 | normal | 0.008851419324460201 | 0.0043273053102638 | 0.0224010944366455 | 46 |
| opp_hc_2 | stress | 18.320306666195393 | 54.18233231800621 | 296.41067695617676 | 32 |
| opp_hc_3 | normal | 0.0038505395253499003 | 0.002514931435436244 | 0.0064420700073242 | 6 |
| opp_hc_3 | stress | 4.956314185086419 | 6.819183207581754 | 22.079998254776 | 17 |
| opp_v4 | normal | 2.5023141295410865 | 7.092974958272934 | 29.40972781181335 | 43 |
| opp_v4 | stress | 0.1135659217834472 | nan | 0.1135659217834472 | 1 |
| opp_v5 | normal | 0.2469221098082406 | 0.16591122132280145 | 0.8291668891906738 | 28 |

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
| opp_v5 | normal | 2.6808142170028874e-11 | 0.0 | 8.542402665284963e-11 | 2.9070243674830897e-10 | 22 |

## 5. Congestión (opp_hc_3 / opp_aco_3 vs. sus baselines v2)

### 5.1 Espera media por congestión

| model | scenario | mean_congestion_wait | std_congestion_wait | max_congestion_wait | n | congestion_modeled |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | nan | nan | nan | 0 | False |
| opp_aco_2 | stress | nan | nan | nan | 0 | False |
| opp_aco_3 | normal | 0.75 | 1.5 | 3.0 | 4 | True |
| opp_aco_3 | stress | 0.6153846153846154 | 1.2608503439122305 | 4.0 | 13 | True |
| opp_hc_2 | normal | nan | nan | nan | 0 | False |
| opp_hc_2 | stress | nan | nan | nan | 0 | False |
| opp_hc_3 | normal | 1.0 | 1.7320508075688772 | 3.0 | 3 | True |
| opp_hc_3 | stress | 1.125 | 2.4186773244895647 | 6.0 | 16 | True |
| opp_v4 | normal | nan | nan | nan | 0 | False |
| opp_v4 | stress | nan | nan | nan | 0 | False |
| opp_v5 | normal | nan | nan | nan | 0 | False |

### 5.2 Sobrecosto de tiempo por modelar congestión

| scenario | mean_time_overhead_pct | n_matched | aware_model | baseline_model |
| --- | --- | --- | --- | --- |
| normal | -15.574779336779315 | 1 | opp_hc_3 | opp_hc_2 |
| stress | 0.04639007306842391 | 16 | opp_hc_3 | opp_hc_2 |
| normal | 99.5794968744288 | 1 | opp_aco_3 | opp_aco_2 |
| stress | 512.7704991022023 | 14 | opp_aco_3 | opp_aco_2 |

## 6. Sensibilidad paramétrica (correlación de Pearson con total_time)

### 6.1 Nivel global (normal + estrés)

| model | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | 0.535 | 0.8314 | 0.4722 | 0.5915 | 0.5276 | -0.3722 | 65 |
| opp_aco_3 | 0.6342 | 0.3802 | 0.4262 | 0.622 | 0.4216 | -0.1912 | 18 |
| opp_hc_2 | 0.5505 | 0.7019 | 0.2855 | 0.5819 | 0.2203 | -0.1631 | 78 |
| opp_hc_3 | 0.2439 | 0.314 | 0.0174 | 0.5458 | 0.2783 | -0.152 | 20 |
| opp_v4 | 0.7512 | 0.4409 | 0.9152 | -0.0178 | 0.4444 | -0.387 | 23 |
| opp_v5 | 0.7871 | 0.4704 | 0.9045 | -0.0459 | 0.4477 | -0.4292 | 22 |

### 6.2 Nivel escenario

| model | scenario | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 0.4544 | 0.4759 | 0.5016 | 0.0808 | -0.015 | -0.496 | 48 |
| opp_aco_2 | stress | 0.2289 | 0.6957 | 0.0605 | 0.2004 | nan | nan | 17 |
| opp_aco_3 | normal | 0.2256 | 0.2256 | 0.9256 | -0.6652 | nan | 0.6652 | 4 |
| opp_aco_3 | stress | 0.5777 | 0.2352 | 0.2924 | 0.5184 | nan | nan | 14 |
| opp_hc_2 | normal | 0.5745 | 0.3289 | 0.2616 | 0.0451 | -0.077 | -0.4117 | 46 |
| opp_hc_2 | stress | 0.5058 | 0.6826 | 0.1746 | 0.5778 | 0.0616 | -0.0616 | 32 |
| opp_hc_3 | normal | 0.9629 | 0.9629 | nan | 0.9629 | nan | -0.9629 | 3 |
| opp_hc_3 | stress | 0.1684 | 0.2321 | -0.1067 | 0.4888 | nan | nan | 17 |
| opp_v4 | normal | 0.843 | 0.4845 | 0.9182 | -0.0086 | 0.4887 | -0.4204 | 22 |
| opp_v5 | normal | 0.7871 | 0.4704 | 0.9045 | -0.0459 | 0.4477 | -0.4292 | 22 |

## Gráficos generados

- `mean_time_normal.png`
- `mean_time_stress.png`
- `profiling_exact_model.png`
- `quality_gap.png`
- `congestion_wait.png`
- `scatter_opp_hc_2_stress_N.png`
- `scatter_opp_aco_2_stress_V.png`
- `scatter_opp_hc_3_stress_V.png`
- `scatter_opp_aco_3_stress_N.png`
