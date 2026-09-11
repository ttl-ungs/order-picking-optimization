# Reporte de comparación de modelos

## 1. Tasa de éxito / convergencia

| model | scenario | total | ok | timeout | failed | success_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 48 | 48 | 0 | 0 | 100.0 |
| opp_aco_2 | stress | 20 | 17 | 1 | 2 | 85.0 |
| opp_aco_3 | normal | 12 | 12 | 0 | 0 | 100.0 |
| opp_aco_3 | stress | 20 | 17 | 1 | 2 | 85.0 |
| opp_aco_4 | normal | 52 | 52 | 0 | 0 | 100.0 |
| opp_aco_4 | stress | 22 | 14 | 1 | 7 | 63.6 |
| opp_hc_2 | normal | 46 | 46 | 0 | 0 | 100.0 |
| opp_hc_2 | stress | 43 | 32 | 11 | 0 | 74.4 |
| opp_hc_3 | normal | 6 | 6 | 0 | 0 | 100.0 |
| opp_hc_3 | stress | 20 | 17 | 3 | 0 | 85.0 |
| opp_hc_4 | normal | 50 | 50 | 0 | 0 | 100.0 |
| opp_hc_4 | stress | 13 | 11 | 2 | 0 | 84.6 |
| opp_v4 | normal | 46 | 45 | 1 | 0 | 97.8 |
| opp_v4 | stress | 8 | 1 | 7 | 0 | 12.5 |
| opp_v5 | normal | 53 | 52 | 1 | 0 | 98.1 |
| opp_v5 | stress | 8 | 0 | 7 | 1 | 0.0 |

## 2. Tiempo de ejecución (solo casos OK)

| model | scenario | mean_time | std_time | max_time | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 0.23610588908195493 | 0.327672399058028 | 1.4354429244995115 | 48 |
| opp_aco_2 | stress | 54.83279884562773 | 53.908574179657755 | 168.5711851119995 | 17 |
| opp_aco_3 | normal | 0.025555570920308385 | 0.04387347950663957 | 0.1223242282867431 | 12 |
| opp_aco_3 | stress | 176.54810125687544 | 178.81893384318866 | 588.2318289279938 | 17 |
| opp_aco_4 | normal | 0.2268606011684124 | 0.30490133187022567 | 1.3257269859313965 | 52 |
| opp_aco_4 | stress | 179.25389174052648 | 374.2022925142759 | 1437.7297501564026 | 14 |
| opp_hc_2 | normal | 0.008851419324460201 | 0.0043273053102638 | 0.0224010944366455 | 46 |
| opp_hc_2 | stress | 2.9689269065856934 | 8.172350553423682 | 43.730140209198 | 32 |
| opp_hc_3 | normal | 0.0038505395253499003 | 0.002514931435436244 | 0.0064420700073242 | 6 |
| opp_hc_3 | stress | 0.563104419147267 | 0.4753807938995693 | 1.4223179817199707 | 17 |
| opp_hc_4 | normal | 0.008774585723876906 | 0.003065250933611688 | 0.0188100337982177 | 50 |
| opp_hc_4 | stress | 0.4299586686221036 | 0.461716348069904 | 1.34344220161438 | 11 |
| opp_v4 | normal | 2.048522546556261 | 5.831397336622343 | 26.211292028427124 | 45 |
| opp_v4 | stress | 0.1135659217834472 | nan | 0.1135659217834472 | 1 |
| opp_v5 | normal | 0.15018961521295396 | 0.17979811670383003 | 1.217266082763672 | 52 |

## 2.1 Memoria pico (RAM, MB, solo casos OK)

_(sin datos)_

## 2.2 Nivel de servicio (% de órdenes sin tardanza, solo casos con dato)

_(sin datos)_

## 2.3 Iteración de convergencia (solo Hill Climbing / ACO)

_(sin datos)_

## 3. Profiling del modelo exacto (opp_v4)

| scenario | mean_total_time | mean_solver_time | n | solver_ratio_pct | overhead_ratio_pct |
| --- | --- | --- | --- | --- | --- |
| normal | 2.048522546556261 | 1.8545493019951715 | 45 | 90.5 | 9.5 |
| stress | 0.1135659217834472 | 0.0 | 1 | 0.0 | 100.0 |

## 4. Gap de optimalidad vs. opp_v4

| model | scenario | mean_gap_pct | median_gap_pct | std_gap_pct | max_gap_pct | n_matched |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 71.22773178522324 | 0.0 | 199.87217644021445 | 472.0 | 9 |
| opp_aco_4 | normal | 71.22773178522324 | 0.0 | 199.87217644021445 | 472.0 | 9 |
| opp_hc_2 | normal | 242.2202579436687 | 0.0 | 533.1439832436334 | 1180.0 | 9 |
| opp_hc_4 | normal | 242.9510335623367 | 0.0 | 532.7824643414737 | 1180.0 | 9 |
| opp_v5 | normal | -0.2555403797941615 | 0.0 | 1.4227886198343525 | 7.735572291461509e-11 | 31 |

## 5. Congestión (opp_hc_3 / opp_aco_3 vs. sus baselines v2)

### 5.1 Espera media por congestión

| model | scenario | mean_congestion_wait | std_congestion_wait | max_congestion_wait | mean_collisions | max_collisions | n | congestion_modeled |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | nan | nan | nan | nan | nan | 0 | False |
| opp_aco_2 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_aco_3 | normal | 0.75 | 1.5 | 3.0 | nan | nan | 4 | True |
| opp_aco_3 | stress | 0.75 | 1.61245154965971 | 4.0 | nan | nan | 16 | True |
| opp_aco_4 | normal | nan | nan | nan | nan | nan | 0 | False |
| opp_aco_4 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_2 | normal | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_2 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_3 | normal | 1.0 | 1.7320508075688772 | 3.0 | nan | nan | 3 | True |
| opp_hc_3 | stress | 1.125 | 2.4186773244895647 | 6.0 | nan | nan | 16 | True |
| opp_hc_4 | normal | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_4 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_v4 | normal | nan | nan | nan | nan | nan | 0 | False |
| opp_v4 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_v5 | normal | nan | nan | nan | nan | nan | 0 | False |

### 5.2 Sobrecosto de tiempo por modelar congestión

| scenario | mean_time_overhead_pct | n_matched | aware_model | baseline_model |
| --- | --- | --- | --- | --- |
| normal | -15.574779336779315 | 1 | opp_hc_3 | opp_hc_2 |
| stress | 18.54392133413714 | 16 | opp_hc_3 | opp_hc_2 |
| normal | 99.5794968744288 | 1 | opp_aco_3 | opp_aco_2 |
| stress | 230.9798807065909 | 17 | opp_aco_3 | opp_aco_2 |

## 6. Sensibilidad paramétrica (correlación de Pearson con total_time)

### 6.1 Nivel global (normal + estrés)

| model | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | 0.5246 | 0.839 | 0.4658 | 0.5868 | 0.5263 | -0.3711 | 65 |
| opp_aco_3 | 0.5975 | 0.3993 | 0.3763 | 0.5951 | 0.4058 | -0.187 | 21 |
| opp_aco_4 | 0.8413 | 0.2771 | 0.5479 | 0.4085 | 0.3107 | -0.1858 | 66 |
| opp_hc_2 | 0.6999 | 0.6658 | 0.3984 | 0.5963 | 0.2339 | -0.173 | 78 |
| opp_hc_3 | 0.6944 | 0.1095 | 0.2999 | 0.8049 | 0.4237 | -0.2316 | 20 |
| opp_hc_4 | 0.6969 | 0.3829 | 0.5534 | 0.6534 | 0.4474 | -0.2367 | 61 |
| opp_v4 | 0.7511 | 0.4413 | 0.915 | -0.0171 | 0.4447 | -0.3873 | 23 |
| opp_v5 | 0.8233 | 0.4794 | 0.8895 | -0.005 | 0.4797 | -0.4194 | 22 |

### 6.2 Nivel escenario

| model | scenario | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 0.4544 | 0.4759 | 0.5016 | 0.0808 | -0.015 | -0.496 | 48 |
| opp_aco_2 | stress | 0.2127 | 0.71 | 0.0505 | 0.1925 | nan | nan | 17 |
| opp_aco_3 | normal | 0.2256 | 0.2256 | 0.9256 | -0.6652 | nan | 0.6652 | 4 |
| opp_aco_3 | stress | 0.5281 | 0.2718 | 0.2383 | 0.4882 | nan | nan | 17 |
| opp_aco_4 | normal | 0.5568 | 0.1893 | 0.1981 | -0.0673 | 0.011 | -0.1337 | 52 |
| opp_aco_4 | stress | 0.8371 | 0.0125 | 0.429 | 0.2047 | nan | nan | 14 |
| opp_hc_2 | normal | 0.5745 | 0.3289 | 0.2616 | 0.0451 | -0.077 | -0.4117 | 46 |
| opp_hc_2 | stress | 0.6704 | 0.6339 | 0.3092 | 0.5854 | 0.0609 | -0.0609 | 32 |
| opp_hc_3 | normal | 0.9629 | 0.9629 | nan | 0.9629 | nan | -0.9629 | 3 |
| opp_hc_3 | stress | 0.6492 | -0.0672 | 0.1571 | 0.7561 | nan | nan | 17 |
| opp_hc_4 | normal | 0.5246 | 0.2569 | 0.158 | 0.0433 | -0.0593 | -0.2547 | 50 |
| opp_hc_4 | stress | 0.5938 | -0.0131 | 0.2965 | 0.6237 | 0.0364 | -0.0364 | 11 |
| opp_v4 | normal | 0.843 | 0.485 | 0.918 | -0.0078 | 0.4891 | -0.4207 | 22 |
| opp_v5 | normal | 0.8233 | 0.4794 | 0.8895 | -0.005 | 0.4797 | -0.4194 | 22 |

## 7. Estabilidad frente a la semilla (30 corridas por instancia, solo heurísticos)

| model | instance | n_seeds | n_ok | success_rate_pct | mean_obj_val | std_obj_val | best_obj_val | worst_obj_val | gap_best_worst_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | medium_multi_picker | 30 | 30 | 100.0 | 5683.0 | 0.0 | 5683.0 | 5683.0 | 0.0 |
| opp_aco_2 | small_multi_picker | 30 | 30 | 100.0 | 1338.0 | 0.0 | 1338.0 | 1338.0 | 0.0 |
| opp_aco_2 | tiny_two_orders | 30 | 30 | 100.0 | 753.0 | 0.0 | 753.0 | 753.0 | 0.0 |
| opp_aco_3 | medium_multi_picker | 30 | 30 | 100.0 | 5835.53 | 43.21 | 5771.0 | 5947.0 | 3.05 |
| opp_aco_3 | small_multi_picker | 30 | 30 | 100.0 | 1338.0 | 0.0 | 1338.0 | 1338.0 | 0.0 |
| opp_aco_3 | tiny_two_orders | 30 | 30 | 100.0 | 753.0 | 0.0 | 753.0 | 753.0 | 0.0 |
| opp_aco_4 | medium_multi_picker | 30 | 30 | 100.0 | 5683.0 | 0.0 | 5683.0 | 5683.0 | 0.0 |
| opp_aco_4 | small_multi_picker | 30 | 30 | 100.0 | 1338.0 | 0.0 | 1338.0 | 1338.0 | 0.0 |
| opp_aco_4 | tiny_two_orders | 30 | 30 | 100.0 | 753.0 | 0.0 | 753.0 | 753.0 | 0.0 |
| opp_hc_2 | medium_multi_picker | 30 | 30 | 100.0 | 5860.47 | 8.03 | 5859.0 | 5903.0 | 0.75 |
| opp_hc_2 | small_multi_picker | 30 | 30 | 100.0 | 1338.0 | 0.0 | 1338.0 | 1338.0 | 0.0 |
| opp_hc_2 | tiny_two_orders | 30 | 30 | 100.0 | 744.0 | 0.0 | 744.0 | 744.0 | 0.0 |
| opp_hc_3 | medium_multi_picker | 30 | 30 | 100.0 | 5948.47 | 8.03 | 5947.0 | 5991.0 | 0.74 |
| opp_hc_3 | small_multi_picker | 30 | 30 | 100.0 | 1338.0 | 0.0 | 1338.0 | 1338.0 | 0.0 |
| opp_hc_3 | tiny_two_orders | 30 | 30 | 100.0 | 744.0 | 0.0 | 744.0 | 744.0 | 0.0 |
| opp_hc_4 | medium_multi_picker | 30 | 30 | 100.0 | 5860.47 | 8.03 | 5859.0 | 5903.0 | 0.75 |
| opp_hc_4 | small_multi_picker | 30 | 30 | 100.0 | 1338.0 | 0.0 | 1338.0 | 1338.0 | 0.0 |
| opp_hc_4 | tiny_two_orders | 30 | 30 | 100.0 | 744.0 | 0.0 | 744.0 | 744.0 | 0.0 |

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
