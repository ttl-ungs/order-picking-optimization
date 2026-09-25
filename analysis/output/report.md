# Reporte de comparación de modelos

## 1. Tasa de éxito / convergencia

| model | scenario | total | ok | timeout | failed | success_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 48 | 48 | 0 | 0 | 100.0 |
| opp_aco_2 | stress | 20 | 17 | 1 | 2 | 85.0 |
| opp_aco_3 | functional | 59 | 59 | 0 | 0 | 100.0 |
| opp_aco_3 | stress | 20 | 17 | 1 | 2 | 85.0 |
| opp_aco_4 | functional | 54 | 54 | 0 | 0 | 100.0 |
| opp_aco_4 | stress | 22 | 19 | 1 | 2 | 86.4 |
| opp_hc_2 | functional | 46 | 46 | 0 | 0 | 100.0 |
| opp_hc_2 | stress | 27 | 18 | 9 | 0 | 66.7 |
| opp_hc_3 | functional | 51 | 51 | 0 | 0 | 100.0 |
| opp_hc_3 | stress | 1 | 1 | 0 | 0 | 100.0 |
| opp_hc_4 | functional | 51 | 51 | 0 | 0 | 100.0 |
| opp_hc_4 | stress | 13 | 11 | 2 | 0 | 84.6 |
| opp_v4 | functional | 2 | 2 | 0 | 0 | 100.0 |
| opp_v4 | stress | 8 | 1 | 7 | 0 | 12.5 |
| opp_v5_1_mono | functional | 62 | 60 | 1 | 1 | 96.8 |
| opp_v5_1_mono | stress | 18 | 0 | 17 | 0 | 0.0 |
| opp_v5_2_split | functional | 63 | 62 | 1 | 0 | 98.4 |
| opp_v5_2_split | stress | 19 | 9 | 10 | 0 | 47.4 |

## 2. Tiempo de ejecución (solo casos OK)

| model | scenario | mean_time | std_time | max_time | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 0.18396599094072974 | 0.2523348868312082 | 1.1211960315704346 | 48 |
| opp_aco_2 | stress | 58.91277899461634 | 56.85699358458276 | 173.91740012168884 | 17 |
| opp_aco_3 | functional | 0.31300401687622065 | 0.5325745150178871 | 2.8098819255828857 | 59 |
| opp_aco_3 | stress | 165.19943078826455 | 175.6710896237539 | 588.5939273834229 | 17 |
| opp_aco_4 | functional | 0.2124941172423186 | 0.27627083509078293 | 1.1925182342529297 | 54 |
| opp_aco_4 | stress | 60.363566875457764 | 64.0981211666289 | 195.39006304740903 | 19 |
| opp_hc_2 | functional | 0.0080522609793621 | 0.002854513253927423 | 0.0171408653259277 | 46 |
| opp_hc_2 | stress | 4.475473337703281 | 11.285555462972114 | 46.435662031173706 | 18 |
| opp_hc_3 | functional | 0.008639742346370875 | 0.0037625092452699288 | 0.0201351642608642 | 51 |
| opp_hc_3 | stress | 0.3684804439544678 | nan | 0.3684804439544678 | 1 |
| opp_hc_4 | functional | 0.010444061428892796 | 0.004429294748174813 | 0.0256180763244628 | 51 |
| opp_hc_4 | stress | 0.438485557382757 | 0.5644101767700619 | 1.7878050804138184 | 11 |
| opp_v4 | functional | 0.3006782531738281 | 0.009512712296302846 | 0.3074047565460205 | 2 |
| opp_v4 | stress | 0.1135659217834472 | nan | 0.1135659217834472 | 1 |
| opp_v5_1_mono | functional | 3.7303433179855348 | 12.706860606662243 | 70.79089069366455 | 60 |
| opp_v5_2_split | functional | 0.4943724332317229 | 0.6275034455352053 | 3.726961374282837 | 62 |
| opp_v5_2_split | stress | 489.71434656778973 | 420.33673382785366 | 1406.2133288383484 | 9 |

## 2.1 Memoria pico (RAM, MB, solo casos OK)

| model | scenario | mean_rss_mb | std_rss_mb | max_rss_mb | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 22.4951171875 | 0.5246297874062654 | 24.359375 | 48 |
| opp_aco_2 | stress | 26.748161764705884 | 8.428222768570478 | 55.59375 | 17 |
| opp_aco_3 | functional | 22.274099576271187 | 0.5197176433031622 | 23.28125 | 59 |
| opp_aco_3 | stress | 29.337316176470587 | 12.65634410992153 | 70.6875 | 17 |
| opp_aco_4 | functional | 22.780671296296298 | 0.5802204420541677 | 23.65625 | 54 |
| opp_aco_4 | stress | 25.961348684210527 | 7.938855569022324 | 55.203125 | 19 |
| opp_hc_2 | functional | 22.394701086956523 | 0.5528143232827556 | 24.09375 | 46 |
| opp_hc_2 | stress | 46.96961805555556 | 40.610369067931266 | 165.875 | 18 |
| opp_hc_3 | functional | 22.307291666666668 | 0.4563534414701687 | 23.390625 | 51 |
| opp_hc_3 | stress | 23.765625 | nan | 23.765625 | 1 |
| opp_hc_4 | functional | 22.61917892156863 | 0.8232400782331437 | 24.546875 | 51 |
| opp_hc_4 | stress | 27.789772727272727 | 16.388766523027495 | 75.96875 | 11 |
| opp_v4 | functional | 44.84375 | 0.027621358640099514 | 44.86328125 | 2 |
| opp_v5_1_mono | functional | 49.998828125 | 15.437416307100362 | 112.46484375 | 60 |
| opp_v5_2_split | functional | 46.17804939516129 | 3.4822827310504914 | 61.12109375 | 62 |
| opp_v5_2_split | stress | 145.64019097222223 | 83.64152382865088 | 342.5703125 | 9 |

## 2.2 Nivel de servicio (% de órdenes sin tardanza, solo casos con dato)

| model | scenario | mean_sla_pct | min_sla_pct | n |
| --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 43.75 | 0.0 | 40 |
| opp_aco_2 | stress | 0.0 | 0.0 | 16 |
| opp_aco_3 | functional | 47.674418604651166 | 0.0 | 43 |
| opp_aco_3 | stress | 0.0 | 0.0 | 16 |
| opp_aco_4 | functional | 50.0 | 0.0 | 45 |
| opp_aco_4 | stress | 0.0 | 0.0 | 18 |
| opp_hc_2 | functional | 44.87179487179487 | 0.0 | 39 |
| opp_hc_2 | stress | 0.0 | 0.0 | 16 |
| opp_hc_3 | functional | 47.5609756097561 | 0.0 | 41 |
| opp_hc_3 | stress | 0.0 | 0.0 | 1 |
| opp_hc_4 | functional | 50.0 | 0.0 | 43 |
| opp_hc_4 | stress | 0.0 | 0.0 | 9 |
| opp_v4 | functional | 50.0 | 0.0 | 2 |
| opp_v5_1_mono | functional | 36.458333333333336 | 0.0 | 48 |
| opp_v5_2_split | functional | 39.795918367346935 | 0.0 | 49 |
| opp_v5_2_split | stress | 60.75498575498576 | 0.0 | 9 |

## 2.3 Iteración de convergencia (solo Hill Climbing / ACO)

| model | scenario | mean_iterations_run | mean_best_found_at_iteration | mean_convergence_pct | n |
| --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 60.0 | 2.0 | 3.3333333333333335 | 40 |
| opp_aco_2 | stress | 60.0 | 37.1875 | 61.979166666666664 | 16 |
| opp_aco_3 | functional | 57.76744186046512 | 2.9302325581395348 | 5.465116279069767 | 43 |
| opp_aco_3 | stress | 60.0 | 30.25 | 50.416666666666664 | 16 |
| opp_aco_4 | functional | 60.0 | 1.9555555555555555 | 3.2592592592592595 | 45 |
| opp_aco_4 | stress | 60.0 | 35.72222222222222 | 59.53703703703704 | 18 |
| opp_hc_2 | functional | 31.128205128205128 | 1.1282051282051282 | 3.170542283445509 | 39 |
| opp_hc_2 | stress | 77.4375 | 49.125 | 39.66145522982999 | 16 |
| opp_hc_3 | functional | 32.26829268292683 | 2.268292682926829 | 5.580514668385273 | 41 |
| opp_hc_3 | stress | 104.0 | 74.0 | 71.15384615384616 | 1 |
| opp_hc_4 | functional | 33.69767441860465 | 2.302325581395349 | 4.529028449975625 | 43 |
| opp_hc_4 | stress | 65.66666666666667 | 35.666666666666664 | 27.380553895654415 | 9 |

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
| opp_aco_4 | functional | 71.2277317852233 | 0.0 | 199.87217644021445 | 472.0 | 9 |
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

| model | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | 0.5265 | 0.8371 | 0.4687 | 0.5859 | 0.532 | -0.3729 | 65 |
| opp_aco_3 | 0.6693 | 0.5885 | 0.5343 | 0.7242 | 0.5087 | -0.3299 | 68 |
| opp_aco_4 | 0.545 | 0.8118 | 0.4925 | 0.6115 | 0.5151 | -0.3046 | 73 |
| opp_hc_2 | 0.7207 | 0.7324 | 0.4129 | 0.7272 | 0.2655 | -0.1838 | 64 |
| opp_hc_3 | 0.9646 | 0.8572 | 0.8189 | 0.1798 | 0.329 | -0.1882 | 49 |
| opp_hc_4 | 0.7642 | 0.3039 | 0.4803 | 0.866 | 0.4203 | -0.2235 | 62 |
| opp_v4 | -0.9981 | -0.9227 | nan | -0.9981 | -0.9981 | 0.9981 | 3 |
| opp_v5_1_mono | 0.8429 | 0.4806 | 0.921 | -0.0181 | 0.4836 | -0.4145 | 21 |
| opp_v5_2_split | 0.8436 | 0.4784 | 0.9252 | -0.0234 | 0.4834 | -0.415 | 21 |

### 6.2 Nivel escenario

| model | scenario | N | V | B | C_v | W_full | W_ea_ta | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opp_aco_2 | functional | 0.5165 | 0.1495 | 0.1768 | -0.0908 | -0.0507 | -0.2146 | 48 |
| opp_aco_2 | stress | 0.2105 | 0.7043 | 0.0487 | 0.1807 | nan | nan | 17 |
| opp_aco_3 | functional | 0.4198 | 0.1298 | 0.1245 | -0.0603 | 0.0488 | -0.1307 | 51 |
| opp_aco_3 | stress | 0.4655 | 0.2752 | 0.2009 | 0.5211 | nan | nan | 17 |
| opp_aco_4 | functional | 0.5649 | 0.2026 | 0.2164 | -0.0617 | -0.0219 | -0.1258 | 54 |
| opp_aco_4 | stress | 0.2874 | 0.6746 | 0.151 | 0.3164 | nan | nan | 19 |
| opp_hc_2 | functional | 0.5326 | 0.2851 | 0.1348 | 0.2305 | 0.0702 | -0.4831 | 46 |
| opp_hc_2 | stress | 0.6809 | 0.6948 | 0.3013 | 0.7059 | 0.0922 | -0.0922 | 18 |
| opp_hc_3 | functional | 0.6224 | 0.2918 | 0.2688 | -0.0146 | -0.1051 | -0.3398 | 48 |
| opp_hc_4 | functional | 0.5886 | 0.2916 | 0.2454 | 0.0743 | 0.0999 | -0.4174 | 51 |
| opp_hc_4 | stress | 0.6909 | -0.071 | 0.2228 | 0.9589 | 0.115 | -0.115 | 11 |
| opp_v4 | functional | nan | 1.0 | nan | nan | nan | nan | 2 |
| opp_v5_1_mono | functional | 0.8429 | 0.4806 | 0.921 | -0.0181 | 0.4836 | -0.4145 | 21 |
| opp_v5_2_split | functional | 0.8436 | 0.4784 | 0.9252 | -0.0234 | 0.4834 | -0.415 | 21 |

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
