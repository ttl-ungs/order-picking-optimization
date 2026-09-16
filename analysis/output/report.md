# Reporte de comparación de modelos

## 1. Tasa de éxito / convergencia

| model | scenario | total | ok | timeout | failed | success_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 48 | 48 | 0 | 0 | 100.0 |
| opp_aco_2 | stress | 20 | 17 | 1 | 2 | 85.0 |
| opp_aco_3 | normal | 59 | 59 | 0 | 0 | 100.0 |
| opp_aco_3 | stress | 20 | 17 | 1 | 2 | 85.0 |
| opp_aco_4 | normal | 54 | 54 | 0 | 0 | 100.0 |
| opp_aco_4 | stress | 22 | 19 | 1 | 2 | 86.4 |
| opp_hc_2 | normal | 46 | 46 | 0 | 0 | 100.0 |
| opp_hc_2 | stress | 27 | 18 | 9 | 0 | 66.7 |
| opp_hc_3 | normal | 51 | 51 | 0 | 0 | 100.0 |
| opp_hc_3 | stress | 20 | 17 | 3 | 0 | 85.0 |
| opp_hc_4 | normal | 51 | 51 | 0 | 0 | 100.0 |
| opp_hc_4 | stress | 13 | 11 | 2 | 0 | 84.6 |
| opp_v4 | normal | 46 | 45 | 1 | 0 | 97.8 |
| opp_v4 | stress | 8 | 1 | 7 | 0 | 12.5 |
| opp_v5 | normal | 53 | 52 | 1 | 0 | 98.1 |
| opp_v5 | stress | 8 | 0 | 7 | 1 | 0.0 |

## 2. Tiempo de ejecución (solo casos OK)

| model | scenario | mean_time | std_time | max_time | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 0.18396599094072974 | 0.25233488683120814 | 1.1211960315704346 | 48 |
| opp_aco_2 | stress | 58.91277899461634 | 56.85699358458275 | 173.91740012168884 | 17 |
| opp_aco_3 | normal | 0.31300401687622065 | 0.5325745150178871 | 2.8098819255828857 | 59 |
| opp_aco_3 | stress | 165.19943078826455 | 175.6710896237539 | 588.5939273834229 | 17 |
| opp_aco_4 | normal | 0.2124941172423186 | 0.27627083509078293 | 1.1925182342529297 | 54 |
| opp_aco_4 | stress | 60.363566875457764 | 64.0981211666289 | 195.39006304740903 | 19 |
| opp_hc_2 | normal | 0.0080522609793621 | 0.002854513253927423 | 0.0171408653259277 | 46 |
| opp_hc_2 | stress | 4.475473337703281 | 11.285555462972114 | 46.435662031173706 | 18 |
| opp_hc_3 | normal | 0.008639742346370875 | 0.0037625092452699288 | 0.0201351642608642 | 51 |
| opp_hc_3 | stress | 0.9233007992015165 | 0.9115397280264553 | 3.1994469165802 | 17 |
| opp_hc_4 | normal | 0.010444061428892796 | 0.004429294748174813 | 0.0256180763244628 | 51 |
| opp_hc_4 | stress | 0.438485557382757 | 0.5644101767700619 | 1.7878050804138184 | 11 |
| opp_v4 | normal | 2.002520778444078 | 5.637359480157549 | 25.34288787841797 | 45 |
| opp_v4 | stress | 0.1135659217834472 | nan | 0.1135659217834472 | 1 |
| opp_v5 | normal | 0.4888411026734572 | 1.6418191378580667 | 8.62041711807251 | 52 |

## 2.1 Memoria pico (RAM, MB, solo casos OK)

| model | scenario | mean_rss_mb | std_rss_mb | max_rss_mb | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 22.4951171875 | 0.5246297874062654 | 24.359375 | 48 |
| opp_aco_2 | stress | 26.748161764705884 | 8.428222768570478 | 55.59375 | 17 |
| opp_aco_3 | normal | 22.274099576271187 | 0.5197176433031622 | 23.28125 | 59 |
| opp_aco_3 | stress | 29.337316176470587 | 12.65634410992153 | 70.6875 | 17 |
| opp_aco_4 | normal | 22.780671296296298 | 0.5802204420541677 | 23.65625 | 54 |
| opp_aco_4 | stress | 25.961348684210527 | 7.938855569022323 | 55.203125 | 19 |
| opp_hc_2 | normal | 22.394701086956523 | 0.5528143232827556 | 24.09375 | 46 |
| opp_hc_2 | stress | 46.96961805555556 | 40.61036906793127 | 165.875 | 18 |
| opp_hc_3 | normal | 22.307291666666668 | 0.4563534414701687 | 23.390625 | 51 |
| opp_hc_3 | stress | 31.43014705882353 | 21.57959164495379 | 93.875 | 17 |
| opp_hc_4 | normal | 22.61917892156863 | 0.8232400782331437 | 24.546875 | 51 |
| opp_hc_4 | stress | 27.789772727272727 | 16.388766523027495 | 75.96875 | 11 |
| opp_v4 | normal | 57.17916666666667 | 19.992079286493517 | 120.34375 | 45 |
| opp_v5 | normal | 52.83173076923077 | 6.507113094717316 | 79.59375 | 52 |

## 2.2 Nivel de servicio (% de órdenes sin tardanza, solo casos con dato)

| model | scenario | mean_sla_pct | min_sla_pct | n |
| --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 43.75 | 0.0 | 40 |
| opp_aco_2 | stress | 0.0 | 0.0 | 16 |
| opp_aco_3 | normal | 47.674418604651166 | 0.0 | 43 |
| opp_aco_3 | stress | 0.0 | 0.0 | 16 |
| opp_aco_4 | normal | 50.0 | 0.0 | 45 |
| opp_aco_4 | stress | 0.0 | 0.0 | 18 |
| opp_hc_2 | normal | 44.87179487179487 | 0.0 | 39 |
| opp_hc_2 | stress | 0.0 | 0.0 | 16 |
| opp_hc_3 | normal | 47.5609756097561 | 0.0 | 41 |
| opp_hc_3 | stress | 0.0 | 0.0 | 16 |
| opp_hc_4 | normal | 50.0 | 0.0 | 43 |
| opp_hc_4 | stress | 0.0 | 0.0 | 9 |
| opp_v4 | normal | 44.5945945945946 | 0.0 | 37 |
| opp_v5 | normal | 46.42857142857143 | 0.0 | 42 |

## 2.3 Iteración de convergencia (solo Hill Climbing / ACO)

| model | scenario | mean_iterations_run | mean_best_found_at_iteration | mean_convergence_pct | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 60.0 | 2.0 | 3.3333333333333335 | 40 |
| opp_aco_2 | stress | 60.0 | 37.1875 | 61.979166666666664 | 16 |
| opp_aco_3 | normal | 57.76744186046512 | 2.9302325581395348 | 5.465116279069767 | 43 |
| opp_aco_3 | stress | 60.0 | 30.25 | 50.416666666666664 | 16 |
| opp_aco_4 | normal | 60.0 | 1.9555555555555555 | 3.2592592592592595 | 45 |
| opp_aco_4 | stress | 60.0 | 35.72222222222222 | 59.53703703703704 | 18 |
| opp_hc_2 | normal | 31.128205128205128 | 1.1282051282051282 | 3.170542283445509 | 39 |
| opp_hc_2 | stress | 77.4375 | 49.125 | 39.66145522982999 | 16 |
| opp_hc_3 | normal | 32.26829268292683 | 2.268292682926829 | 5.580514668385273 | 41 |
| opp_hc_3 | stress | 89.625 | 59.625 | 44.69159414868709 | 16 |
| opp_hc_4 | normal | 33.69767441860465 | 2.302325581395349 | 4.529028449975625 | 43 |
| opp_hc_4 | stress | 65.66666666666667 | 35.666666666666664 | 27.380553895654415 | 9 |

## 3. Profiling del modelo exacto (opp_v4)

| scenario | mean_total_time | mean_solver_time | n | solver_ratio_pct | overhead_ratio_pct |
| --- | --- | --- | --- | --- | --- |
| normal | 2.002520778444078 | 1.797218492296007 | 45 | 89.7 | 10.3 |
| stress | 0.1135659217834472 | 0.0 | 1 | 0.0 | 100.0 |

## 4. Gap de optimalidad vs. opp_v4

| model | scenario | mean_gap_pct | median_gap_pct | std_gap_pct | max_gap_pct | n_matched |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 71.22773178522324 | 0.0 | 199.87217644021445 | 472.0 | 9 |
| opp_aco_3 | normal | 70.94082381347417 | 0.0 | 200.29580092085584 | 472.0 | 9 |
| opp_aco_4 | normal | 71.22773178522324 | 0.0 | 199.87217644021445 | 472.0 | 9 |
| opp_hc_2 | normal | 241.6721762296677 | 0.0 | 533.4208746881704 | 1180.0 | 9 |
| opp_hc_3 | normal | 241.90973156926384 | 0.0 | 533.3002566895905 | 1180.0 | 9 |
| opp_hc_4 | normal | 241.6721762296677 | 0.0 | 533.4208746881704 | 1180.0 | 9 |
| opp_v5 | normal | -0.2555403797832111 | 0.0 | 1.4227886198363342 | 7.739048953165537e-11 | 31 |

## 4.1 Gap de optimalidad vs. opp_v5 (opp_hc_4 / opp_aco_4)

| model | scenario | mean_gap_pct | median_gap_pct | std_gap_pct | max_gap_pct | n_matched |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_4 | normal | 71.22773178522328 | 0.0 | 199.87217644021445 | 472.0 | 9 |
| opp_hc_4 | normal | 241.6721762296677 | 0.0 | 533.4208746881704 | 1180.0 | 9 |

## 5. Congestión (opp_hc_3 / opp_aco_3 vs. sus baselines v2)

### 5.1 Espera media por congestión

| model | scenario | mean_congestion_wait | std_congestion_wait | max_congestion_wait | mean_collisions | max_collisions | n | congestion_modeled |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | nan | nan | nan | nan | nan | 0 | False |
| opp_aco_2 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_aco_3 | normal | 0.11627906976744186 | 0.5437656325319977 | 3.0 | 0.046511627906976744 | 1.0 | 43 | True |
| opp_aco_3 | stress | 0.625 | 1.408308678285174 | 4.0 | 0.3125 | 2.0 | 16 | True |
| opp_aco_4 | normal | nan | nan | nan | nan | nan | 0 | False |
| opp_aco_4 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_2 | normal | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_2 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_3 | normal | 0.17073170731707318 | 0.7714414762115869 | 4.0 | 0.07317073170731707 | 2.0 | 41 | True |
| opp_hc_3 | stress | 1.125 | 2.4186773244895647 | 6.0 | 0.4375 | 3.0 | 16 | True |
| opp_hc_4 | normal | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_4 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_v4 | normal | nan | nan | nan | nan | nan | 0 | False |
| opp_v4 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_v5 | normal | nan | nan | nan | nan | nan | 0 | False |

### 5.2 Sobrecosto de tiempo por modelar congestión

| scenario | mean_time_overhead_pct | n_matched | aware_model | baseline_model |
| --- | --- | --- | --- | --- |
| normal | 13.043235462638608 | 46 | opp_hc_3 | opp_hc_2 |
| stress | 60.6186724986318 | 7 | opp_hc_3 | opp_hc_2 |
| normal | 93.35940683742062 | 48 | opp_aco_3 | opp_aco_2 |
| stress | 165.43543227106733 | 17 | opp_aco_3 | opp_aco_2 |

## 6. Sensibilidad paramétrica (correlación de Pearson con total_time)

### 6.1 Nivel global (normal + estrés)

| model | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | 0.5265 | 0.8371 | 0.4687 | 0.5859 | 0.532 | -0.3729 | 65 |
| opp_aco_3 | 0.6693 | 0.5885 | 0.5343 | 0.7242 | 0.5087 | -0.3299 | 68 |
| opp_aco_4 | 0.545 | 0.8118 | 0.4925 | 0.6115 | 0.5151 | -0.3046 | 73 |
| opp_hc_2 | 0.7207 | 0.7324 | 0.4129 | 0.7272 | 0.2655 | -0.1838 | 64 |
| opp_hc_3 | 0.7814 | 0.3697 | 0.5092 | 0.8295 | 0.5229 | -0.3441 | 65 |
| opp_hc_4 | 0.7642 | 0.3039 | 0.4803 | 0.866 | 0.4203 | -0.2235 | 62 |
| opp_v4 | 0.751 | 0.4403 | 0.9151 | -0.018 | 0.4441 | -0.3868 | 23 |
| opp_v5 | 0.843 | 0.4822 | 0.92 | -0.0164 | 0.4855 | -0.4162 | 21 |

### 6.2 Nivel escenario

| model | scenario | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | normal | 0.5165 | 0.1495 | 0.1768 | -0.0908 | -0.0507 | -0.2146 | 48 |
| opp_aco_2 | stress | 0.2105 | 0.7043 | 0.0487 | 0.1807 | nan | nan | 17 |
| opp_aco_3 | normal | 0.4198 | 0.1298 | 0.1245 | -0.0603 | 0.0488 | -0.1307 | 51 |
| opp_aco_3 | stress | 0.4655 | 0.2752 | 0.2009 | 0.5211 | nan | nan | 17 |
| opp_aco_4 | normal | 0.5649 | 0.2026 | 0.2164 | -0.0617 | -0.0219 | -0.1258 | 54 |
| opp_aco_4 | stress | 0.2874 | 0.6746 | 0.151 | 0.3164 | nan | nan | 19 |
| opp_hc_2 | normal | 0.5326 | 0.2851 | 0.1348 | 0.2305 | 0.0702 | -0.4831 | 46 |
| opp_hc_2 | stress | 0.6809 | 0.6948 | 0.3013 | 0.7059 | 0.0922 | -0.0922 | 18 |
| opp_hc_3 | normal | 0.6224 | 0.2918 | 0.2688 | -0.0146 | -0.1051 | -0.3398 | 48 |
| opp_hc_3 | stress | 0.6452 | -0.1381 | 0.137 | 0.7302 | nan | nan | 17 |
| opp_hc_4 | normal | 0.5886 | 0.2916 | 0.2454 | 0.0743 | 0.0999 | -0.4174 | 51 |
| opp_hc_4 | stress | 0.6909 | -0.071 | 0.2228 | 0.9589 | 0.115 | -0.115 | 11 |
| opp_v4 | normal | 0.843 | 0.484 | 0.9181 | -0.0088 | 0.4885 | -0.4204 | 22 |
| opp_v5 | normal | 0.843 | 0.4822 | 0.92 | -0.0164 | 0.4855 | -0.4162 | 21 |

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
- `quality_gap_v5.png`
- `congestion_wait.png`
- `scatter_opp_hc_2_stress_N.png`
- `scatter_opp_aco_2_stress_V.png`
- `scatter_opp_hc_3_stress_V.png`
- `scatter_opp_aco_3_stress_N.png`
