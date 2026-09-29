# Reporte de comparación de modelos

## 1. Tasa de éxito / convergencia

| model | scenario | total | ok | timeout | failed | success_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 48 | 48 | 0 | 0 | 100.0 |
| opp_aco_2 | stress | 20 | 17 | 1 | 2 | 85.0 |
| opp_aco_3 | functional | 59 | 59 | 0 | 0 | 100.0 |
| opp_aco_3 | stress | 20 | 17 | 1 | 2 | 85.0 |
| opp_aco_4 | functional | 131 | 131 | 0 | 0 | 100.0 |
| opp_aco_4 | stress | 19 | 19 | 0 | 0 | 100.0 |
| opp_hc_2 | functional | 46 | 46 | 0 | 0 | 100.0 |
| opp_hc_2 | stress | 27 | 18 | 9 | 0 | 66.7 |
| opp_hc_3 | functional | 51 | 51 | 0 | 0 | 100.0 |
| opp_hc_3 | stress | 1 | 1 | 0 | 0 | 100.0 |
| opp_hc_4 | functional | 131 | 131 | 0 | 0 | 100.0 |
| opp_hc_4 | stress | 19 | 19 | 0 | 0 | 100.0 |
| opp_v4 | functional | 2 | 2 | 0 | 0 | 100.0 |
| opp_v4 | stress | 8 | 1 | 7 | 0 | 12.5 |
| opp_v5_1_mono | functional | 63 | 62 | 1 | 0 | 98.4 |
| opp_v5_1_mono | stress | 4 | 0 | 3 | 0 | 0.0 |
| opp_v5_2_split | functional | 64 | 63 | 1 | 0 | 98.4 |
| opp_v5_2_split | stress | 19 | 9 | 10 | 0 | 47.4 |

## 2. Tiempo de ejecución (solo casos OK)

| model | scenario | mean_time | std_time | max_time | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 0.18396599094072974 | 0.2523348868312082 | 1.1211960315704346 | 48 |
| opp_aco_2 | stress | 58.91277899461634 | 56.85699358458276 | 173.91740012168884 | 17 |
| opp_aco_3 | functional | 0.31300401687622065 | 0.5325745150178871 | 2.8098819255828857 | 59 |
| opp_aco_3 | stress | 165.19943078826455 | 175.6710896237539 | 588.5939273834229 | 17 |
| opp_aco_4 | functional | 0.41030748927866223 | 0.4651468522977284 | 2.1905760765075684 | 131 |
| opp_aco_4 | stress | 252.01117679947302 | 462.880909747617 | 2094.7729003429413 | 19 |
| opp_hc_2 | functional | 0.0080522609793621 | 0.002854513253927423 | 0.0171408653259277 | 46 |
| opp_hc_2 | stress | 4.475473337703281 | 11.285555462972114 | 46.435662031173706 | 18 |
| opp_hc_3 | functional | 0.008639742346370875 | 0.0037625092452699288 | 0.0201351642608642 | 51 |
| opp_hc_3 | stress | 0.3684804439544678 | nan | 0.3684804439544678 | 1 |
| opp_hc_4 | functional | 0.061682695650872345 | 0.018286889432953982 | 0.1268568038940429 | 131 |
| opp_hc_4 | stress | 56.44854645980032 | 235.56591220576246 | 1029.1946642398834 | 19 |
| opp_v4 | functional | 0.3006782531738281 | 0.009512712296302846 | 0.3074047565460205 | 2 |
| opp_v4 | stress | 0.1135659217834472 | nan | 0.1135659217834472 | 1 |
| opp_v5_1_mono | functional | 2.298395341442477 | 7.877137532846327 | 43.53396797180176 | 62 |
| opp_v5_2_split | functional | 0.44793626240321566 | 0.6234425893613882 | 3.8630294799804688 | 63 |
| opp_v5_2_split | stress | 216.83580197228326 | 270.22769323482225 | 904.0794003009796 | 9 |

## 2.1 Memoria pico (RAM, MB, solo casos OK)

| model | scenario | mean_rss_mb | std_rss_mb | max_rss_mb | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 22.4951171875 | 0.5246297874062654 | 24.359375 | 48 |
| opp_aco_2 | stress | 26.748161764705884 | 8.428222768570478 | 55.59375 | 17 |
| opp_aco_3 | functional | 22.274099576271187 | 0.5197176433031622 | 23.28125 | 59 |
| opp_aco_3 | stress | 29.337316176470587 | 12.65634410992153 | 70.6875 | 17 |
| opp_aco_4 | functional | 25.95288645038168 | 2.331854415432431 | 28.41796875 | 131 |
| opp_aco_4 | stress | 288.1060855263158 | 547.0003585384404 | 1658.37109375 | 19 |
| opp_hc_2 | functional | 22.394701086956523 | 0.5528143232827556 | 24.09375 | 46 |
| opp_hc_2 | stress | 46.96961805555556 | 40.610369067931266 | 165.875 | 18 |
| opp_hc_3 | functional | 22.307291666666668 | 0.4563534414701687 | 23.390625 | 51 |
| opp_hc_3 | stress | 23.765625 | nan | 23.765625 | 1 |
| opp_hc_4 | functional | 25.892801765267176 | 2.3666318012216556 | 29.11328125 | 131 |
| opp_hc_4 | stress | 70.64576480263158 | 192.94953575412384 | 867.3828125 | 19 |
| opp_v4 | functional | 44.84375 | 0.027621358640099514 | 44.86328125 | 2 |
| opp_v5_1_mono | functional | 49.955582157258064 | 15.071321291738533 | 111.078125 | 62 |
| opp_v5_2_split | functional | 46.24993799603175 | 3.4588961996841405 | 61.02734375 | 63 |
| opp_v5_2_split | stress | 113.94314236111111 | 70.49193172715414 | 287.1484375 | 9 |

## 2.2 Nivel de servicio (% de órdenes sin tardanza, solo casos con dato)

| model | scenario | mean_sla_pct | min_sla_pct | n |
| --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 43.75 | 0.0 | 40 |
| opp_aco_2 | stress | 0.0 | 0.0 | 16 |
| opp_aco_3 | functional | 47.674418604651166 | 0.0 | 43 |
| opp_aco_3 | stress | 0.0 | 0.0 | 16 |
| opp_aco_4 | functional | 52.492211838006234 | 0.0 | 107 |
| opp_aco_4 | stress | 84.07557354925775 | 0.0 | 19 |
| opp_hc_2 | functional | 44.87179487179487 | 0.0 | 39 |
| opp_hc_2 | stress | 0.0 | 0.0 | 16 |
| opp_hc_3 | functional | 47.5609756097561 | 0.0 | 41 |
| opp_hc_3 | stress | 0.0 | 0.0 | 1 |
| opp_hc_4 | functional | 52.33644859813084 | 0.0 | 107 |
| opp_hc_4 | stress | 84.04183535762483 | 0.0 | 19 |
| opp_v4 | functional | 50.0 | 0.0 | 2 |
| opp_v5_1_mono | functional | 39.0 | 0.0 | 50 |
| opp_v5_2_split | functional | 41.0 | 0.0 | 50 |
| opp_v5_2_split | stress | 88.60398860398861 | 0.0 | 9 |

## 2.3 Iteración de convergencia (solo Hill Climbing / ACO)

| model | scenario | mean_iterations_run | mean_best_found_at_iteration | mean_convergence_pct | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 60.0 | 2.0 | 3.3333333333333335 | 40 |
| opp_aco_2 | stress | 60.0 | 37.1875 | 61.979166666666664 | 16 |
| opp_aco_3 | functional | 57.76744186046512 | 2.9302325581395348 | 5.465116279069767 | 43 |
| opp_aco_3 | stress | 60.0 | 30.25 | 50.416666666666664 | 16 |
| opp_aco_4 | functional | 60.0 | 1.0093457943925233 | 1.6822429906542056 | 107 |
| opp_aco_4 | stress | 56.94736842105263 | 27.68421052631579 | 48.68421052631579 | 19 |
| opp_hc_2 | functional | 31.128205128205128 | 1.1282051282051282 | 3.170542283445509 | 39 |
| opp_hc_2 | stress | 77.4375 | 49.125 | 39.66145522982999 | 16 |
| opp_hc_3 | functional | 32.26829268292683 | 2.268292682926829 | 5.580514668385273 | 41 |
| opp_hc_3 | stress | 104.0 | 74.0 | 71.15384615384616 | 1 |
| opp_hc_4 | functional | 33.00934579439252 | 1.6074766355140186 | 3.8791917148190813 | 107 |
| opp_hc_4 | stress | 89.47368421052632 | 36.526315789473685 | 27.72032458847794 | 19 |

## 3. Profiling del modelo exacto (opp_v4)

| scenario | mean_total_time | mean_solver_time | n | solver_ratio_pct | overhead_ratio_pct |
| --- | --- | --- | --- | --- | --- |
| functional | 0.3006782531738281 | 0.0109736919403076 | 2 | 3.6 | 96.4 |
| stress | 0.1135659217834472 | 0.0 | 1 | 0.0 | 100.0 |

## 4. Gap de optimalidad vs. opp_v4

| model | scenario | mean_gap_pct | median_gap_pct | std_gap_pct | max_gap_pct | n_matched |
| --- | --- | --- | --- | --- | --- | --- |
| opp_v5_1_mono | functional | 0.0 | 0.0 | 0.0 | 0.0 | 2 |
| opp_v5_2_split | functional | 0.0 | 0.0 | 0.0 | 0.0 | 2 |

## 4.1 Gap de optimalidad vs. opp_v5_2_split (opp_hc_4 / opp_aco_4)

| model | scenario | mean_gap_pct | median_gap_pct | std_gap_pct | max_gap_pct | n_matched |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_4 | functional | 241.67217622966777 | 0.0 | 533.4208746881704 | 1180.0 | 9 |
| opp_hc_4 | functional | 241.67217622966777 | 0.0 | 533.4208746881704 | 1180.0 | 9 |

## 5. Congestión (opp_hc_3 / opp_aco_3 vs. sus baselines v2)

### 5.1 Espera media por congestión

| model | scenario | mean_congestion_wait | std_congestion_wait | max_congestion_wait | mean_collisions | max_collisions | n | congestion_modeled |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | nan | nan | nan | nan | nan | 0 | False |
| opp_aco_2 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_aco_3 | functional | 0.11627906976744186 | 0.5437656325319977 | 3.0 | 0.046511627906976744 | 1.0 | 43 | True |
| opp_aco_3 | stress | 0.625 | 1.4083086782851737 | 4.0 | 0.3125 | 2.0 | 16 | True |
| opp_aco_4 | functional | nan | nan | nan | nan | nan | 0 | False |
| opp_aco_4 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_2 | functional | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_2 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_3 | functional | 0.17073170731707318 | 0.7714414762115869 | 4.0 | 0.07317073170731707 | 2.0 | 41 | True |
| opp_hc_3 | stress | 0.0 | nan | 0.0 | 0.0 | 0.0 | 1 | True |
| opp_hc_4 | functional | nan | nan | nan | nan | nan | 0 | False |
| opp_hc_4 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_v4 | functional | nan | nan | nan | nan | nan | 0 | False |
| opp_v4 | stress | nan | nan | nan | nan | nan | 0 | False |
| opp_v5_1_mono | functional | nan | nan | nan | nan | nan | 0 | False |
| opp_v5_2_split | functional | nan | nan | nan | nan | nan | 0 | False |
| opp_v5_2_split | stress | nan | nan | nan | nan | nan | 0 | False |

### 5.2 Sobrecosto de tiempo por modelar congestión

| scenario | mean_time_overhead_pct | n_matched | aware_model | baseline_model |
| --- | --- | --- | --- | --- |
| functional | 13.043235462638608 | 46 | opp_hc_3 | opp_hc_2 |
| stress | -37.73521738219592 | 1 | opp_hc_3 | opp_hc_2 |
| functional | 93.35940683742062 | 48 | opp_aco_3 | opp_aco_2 |
| stress | 165.43543227106733 | 17 | opp_aco_3 | opp_aco_2 |

## 6. Sensibilidad paramétrica (correlación de Pearson con total_time)

### 6.1 Nivel global (functional + estrés)

| model | N | V | B | C_v | W_c | W_pen | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | 0.5265 | 0.8371 | 0.4687 | 0.5859 | 0.532 | -0.3729 | 65 |
| opp_aco_3 | 0.6693 | 0.5885 | 0.5343 | 0.7242 | 0.5087 | -0.3299 | 68 |
| opp_aco_4 | 0.7813 | 0.9443 | 0.6485 | 0.4978 | 0.2791 | -0.1376 | 150 |
| opp_hc_2 | 0.7207 | 0.7324 | 0.4129 | 0.7272 | 0.2655 | -0.1838 | 64 |
| opp_hc_3 | 0.9646 | 0.8572 | 0.8189 | 0.1798 | 0.329 | -0.1882 | 49 |
| opp_hc_4 | 0.5481 | 0.9992 | 0.4329 | 0.2723 | 0.0522 | -0.0666 | 150 |
| opp_v4 | -0.9981 | -0.9227 | nan | -0.9981 | -0.9981 | 0.9981 | 3 |
| opp_v5_1_mono | 0.8439 | 0.4819 | 0.9209 | -0.0169 | 0.4848 | -0.4158 | 21 |
| opp_v5_2_split | 0.8516 | 0.484 | 0.9269 | -0.0326 | 0.4829 | -0.4199 | 20 |

### 6.2 Nivel escenario

| model | scenario | N | V | B | C_v | W_c | W_pen | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 0.5165 | 0.1495 | 0.1768 | -0.0908 | -0.0507 | -0.2146 | 48 |
| opp_aco_2 | stress | 0.2105 | 0.7043 | 0.0487 | 0.1807 | nan | nan | 17 |
| opp_aco_3 | functional | 0.4198 | 0.1298 | 0.1245 | -0.0603 | 0.0488 | -0.1307 | 51 |
| opp_aco_3 | stress | 0.4655 | 0.2752 | 0.2009 | 0.5211 | nan | nan | 17 |
| opp_aco_4 | functional | 0.6995 | 0.3845 | 0.4049 | -0.0009 | 0.0576 | -0.0737 | 131 |
| opp_aco_4 | stress | 0.7949 | 0.9637 | 0.6005 | 0.5572 | -0.5572 | nan | 19 |
| opp_hc_2 | functional | 0.5326 | 0.2851 | 0.1348 | 0.2305 | 0.0702 | -0.4831 | 46 |
| opp_hc_2 | stress | 0.6809 | 0.6948 | 0.3013 | 0.7059 | 0.0922 | -0.0922 | 18 |
| opp_hc_3 | functional | 0.6224 | 0.2918 | 0.2688 | -0.0146 | -0.1051 | -0.3398 | 48 |
| opp_hc_4 | functional | 0.5264 | 0.3815 | 0.3973 | -0.014 | 0.0525 | 0.0357 | 131 |
| opp_hc_4 | stress | 0.6561 | 0.9997 | 0.4498 | 0.543 | -0.543 | nan | 19 |
| opp_v4 | functional | nan | 1.0 | nan | nan | nan | nan | 2 |
| opp_v5_1_mono | functional | 0.8439 | 0.4819 | 0.9209 | -0.0169 | 0.4848 | -0.4158 | 21 |
| opp_v5_2_split | functional | 0.8516 | 0.484 | 0.9269 | -0.0326 | 0.4829 | -0.4199 | 20 |

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

- `mean_time_functional.png`
- `mean_time_stress.png`
- `profiling_exact_model.png`
- `quality_gap.png`
- `quality_gap_v5.png`
- `congestion_wait.png`
- `scatter_opp_hc_2_stress_N.png`
- `scatter_opp_aco_2_stress_V.png`
- `scatter_opp_aco_3_stress_N.png`
