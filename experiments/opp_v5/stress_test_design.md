# Propuesta de tests de stress para opp_v5 (mono y split)

> Estado: **implementada el 2026-09-23 y corrida en split** (mono pendiente). Resultados en la sección 0. El resto del documento es la propuesta original con su calibración.

> ⚠ **Numeración vieja.** El 2026-09-23 el stress de opp_v5 se depuró y renumeró a 19 tests (tabla completa en `meta.md`). Los 09, 10 y 11 de este documento son hoy **04, 05 y 07**; los 12-23 que se mencionen siguen la tabla de `meta.md`.

## 0. Resultados de la corrida (split, 2026-09-23)

`python -m tests.run_suite opp_v5_2_split stress --id 09 10 11 --timeout-minutes 40`, en serie y con la máquina sola. CSV: `results/opp_v5_2_split/stress/output_opp_v5_2_split_stress_tests_20260923_142920.csv`.

| Test | Depósito | Estado | **Total** | Etapa 1 | Etapa 2 | Objetivo | SLA | RAM pico |
|---|---|---|---|---|---|---|---|---|
| 09 | 7×7 | ok | **2,0 min** | 6 s | 117 s | 79.046,86 | 67,9% | 148 MB |
| 10 | 13×13 | ok | **5,9 min** | 224 s | 128 s | 127.210,11 | 67,9% | 261 MB |
| 11 | 15×15 | ok | **28,5 min** | 1485 s | 222 s | 143.318,61 | 67,9% | 261 MB |

- **Los tres pasan, sin timeouts.** El 15×15 **no resultó ser el techo**: resuelve dentro de los 40 min del runner, así que ocupa el escalón de 40 minutos previsto para la fase siguiente.
- **Ninguno cae en la franja de 10-20 min**: el salto 13×13 → 15×15 la saltea. Candidato para cubrirla: **14×14**, no medido.
- **La Etapa 1 es la que crece** (6 → 224 → 1485 s); la Etapa 2 se mantiene casi estable (117 → 128 → 222 s). Con este perfil, en depósitos grandes el costo es del ruteo — la etapa que el split descompone por lote.
- **Mismo objetivo exacto que la calibración** en 7×7 y 13×13, pero las dos etapas corrieron casi exactamente al doble de velocidad. La calibración "en solitario" arrancó tras media hora de 16 procesos en paralelo, con la notebook caliente. **En esta máquina los tiempos absolutos pueden variar ~2x entre corridas**; para citarlos en la tesis conviene repetir y reportar condiciones.
- SLA 67,9% en los tres, sobre la fórmula de la sección 2.2.

## 1. Resumen

**Tres tests de stress nuevos (09, 10, 11), en split y en mono, con perfil realista y un solo eje que varía: el tamaño del depósito.**

| Test | Depósito | Split, medido solo | Rol |
|---|---|---|---|
| 09 | 7×7 | 3,6 min | régimen cómodo; comparación directa con el mono |
| **10** | **13×13** | **11,8 min** | **el test de la franja 10-20 min** |
| 11 | 15×15 | Etapa 1 > 25 min | el techo |

Perfil común: 6 lotes sobre 3 pickers, 156 órdenes, pesos de grilla 4/5, velocidades en dos bandas (0,8 y 1,2), sin clausura.

Tres cosas que conviene saber antes de confirmar:

1. **Solo un tamaño cae en la franja 10-20.** Con velocidades realistas, la Etapa 2 no tolera más de dos lotes por picker, así que el tamaño tiene que venir del depósito; y la Etapa 1 salta de 11,8 min en 13×13 a más de 25 en 15×15. El 14×14 no está medido y es el candidato si querés un segundo test en la franja.
2. **El mono, medido en la misma instancia del 7×7, no llegó al óptimo en 25 minutos** (brecha 144%). El split la resolvió. Es la comparación 1:1 que respalda la tesis; los otros dos tamaños la confirmarán al correr la suite.
3. **"Grande" acá es relativo**: 156 órdenes y 169 ubicaciones es más grande y mucho más realista que los dos únicos stress que hoy pasan (100 órdenes en 10×10 y 60 en 7×7, ambos con todo uniforme), pero es lo que permite el modelo exacto con cuadrillas y pasillos realistas.

---

## 2. Qué sabemos

Todo lo de esta sección está medido. Donde algo es hipótesis se dice explícitamente.

### 2.1 Qué gobierna cada etapa

Las dos etapas del split tienen motores de dificultad **distintos e independientes**, y eso es lo que hace posible diseñar escenarios grandes que igual resuelvan.

**Etapa 1 (ruteo, un MIP por lote)**

| Depende de | No depende de |
|---|---|
| ubicaciones distintas por lote (≈ órdenes por lote menos colisiones) | cantidad de pickers |
| tamaño de la grilla, **por sí mismo** | velocidades de los pickers |
| cantidad de lotes (lineal: un solve por lote) | fechas de entrega |

Escalado medido el 2026-09-22 con 6 lotes y 26 órdenes por lote, **pesos 4/4, con clausura, dos procesos en paralelo**:

| Grilla | Nodos | Ubic./lote | Etapa 1 |
|---|---|---|---|
| 7×7 | 49 | 18-22 | 12,9 s |
| 10×10 | 100 | 21-26 | 50,4 s |
| 15×15 | 225 | 24-26 | 464,4 s |

Con el perfil de esta propuesta (pesos 4/5, sin clausura, medido solo) el 15×15 **no terminó la Etapa 1 en 25 minutos** — ver sección 4. Son tres diferencias a la vez y no está identificado cuál produce el salto; es la advertencia de la sección 2.5 en acción.

La grilla cuesta por sí misma, no solo a través de las ubicaciones: llegar a ~31 ubicaciones por lote agrandando los pedidos (7×7, 50 órdenes/lote) cuesta 46 s, y llegar a ~25 agrandando la grilla (15×15) cuesta 464 s. El mecanismo no está identificado.

**Etapa 2 (asignación y secuenciamiento)**

| Depende de | No depende de |
|---|---|
| relación lotes/pickers | tamaño de la grilla (salvo vía los tiempos de ruta) |
| heterogeneidad de velocidades | pesos de las aristas |
| cantidad de pickers (no monótono) | |

- Con `|B| = |P|` cada lote toma su picker y el secuenciamiento no se activa: es un problema de asignación.
- Con `|B| > |P|` el secuenciamiento se activa. Con velocidades uniformes: 6 lotes/2 pickers 8 s, 6/3 17,7 s, 6/4 26,3 s; **8 lotes/2 pickers no termina en 5 min**.
- La dificultad hace pico en relaciones intermedias, no en los extremos (6 lotes: 2P 14,5 s → 3P 31,2 s → 4P 43,1 s → 5P 37,4 s → 6P 17,1 s, a 50 órdenes/lote).

**Qué eje rompe dónde** (barrido de un eje por vez desde 6 lotes / 2 pickers / 26 órd. / 7×7):

| Eje | Rango | Rompe | Etapa |
|---|---|---|---|
| Órdenes por lote | 10 → 50 | nunca | — |
| Pickers | 2 → 6 | nunca (no monótono) | — |
| **Lotes** | 6 → 8 | **en 8** | 2 |
| **Grilla** | 7×7 → 15×15 | **en 15×15** | 1 |

### 2.2 El SLA lo fija la función objetivo, no las fechas de entrega

Con fechas repartidas y alcanzables:

**SLA = (N_b + W_full) / (2 · N_b)**, con N_b = órdenes por lote.

Demorar un lote cuesta `W_full` por unidad de tiempo y ahorra una unidad por cada orden que todavía llegaría temprano, así que el modelo demora cada lote hasta que #tempranas − #tardías ≈ W_full. Verificado en 8 tamaños (10 a 50 órdenes por lote), todos dentro de 1,7 puntos.

Consecuencias para el diseño:
- **Las fechas no necesitan calibración**: alcanza con que estén repartidas y sean alcanzables. Con 26 órdenes por lote el SLA sale ~67%.
- El modelo es **just-in-time**: inserta tiempo ocioso a propósito. Es un objetivo de adelanto/tardanza, una clase de scheduling notoriamente difícil. Relevante para optimizar la Etapa 2.

### 2.3 Las velocidades realistas cambian el dimensionamiento

Una cuadrilla real tiene dos o tres bandas de velocidad, no una por persona. Instancia fija (6 lotes, 26 órdenes/lote, 7×7), variando solo cuántas velocidades distintas hay:

| Pickers | Uniformes | 2 niveles | 3 niveles |
|---|---|---|---|
| 3 | 17,7 s | 134,2 s | 113,5 s |
| 4 | 26,3 s | > 300 s | > 300 s |
| 6 (= lotes) | 7,2 s | 110,4 s | > 3000 s |

- El escalón está en pasar de 1 a 2 velocidades; más niveles no suman.
- **Todos los bordes medidos antes (8 lotes, 15×15) se midieron con velocidades uniformes**, o sea sobre el caso artificialmente fácil. Con velocidades realistas la Etapa 2 alcanza bastante menos.

### 2.4 Estado actual de la suite de stress

| Test | Configuración | split | mono |
|---|---|---|---|
| 01 | 30L/30P, 750 órd., 25×25 | timeout | timeout |
| 02 | 30L/30P, 750 órd., 100×100 | timeout | sin memoria |
| 03 | 20L/20P, 600 órd., 100×100 | timeout | ZIMPL sin memoria |
| 04 | 25L/25P, 100 órd., 10×10 | timeout | — |
| 05 | 10L/10P, 100 órd., 10×10 | **ok (~45 s)** | — |
| 06 | 25L/10P, 100 órd., 10×10 | timeout | — |
| 07 | 10L/25P, 100 órd., 10×10 | timeout | — |
| 08 | 40L/1P, 320 órd., 7×7 | timeout | — |
| 09* | 6L/2P, 60 órd., 7×7 | **ok (39 s)** | — |

\* versión de la escalera diseñada el 2026-09-22, con velocidades y pesos uniformes.

Seis degeneraciones detectadas en esos escenarios (detalle en `meta.md`):

| # | Degeneración | Tipo |
|---|---|---|
| 3 | Fechas de entrega idénticas e inalcanzables (`Dd = 30`) | rendimiento |
| 1 | `\|P\| > \|B\|` (test 07) | cobertura |
| 2 | `\|B\| = \|P\|` en 5 de 8 | cobertura |
| 4 | `V_p` uniforme en todos | cobertura |
| 5 | Lotes vacíos (funcional 30) | cobertura |
| 6 | Pesos de grilla uniformes | cobertura |

### 2.5 Disciplina de medición

- **Misma instancia → mismo árbol.** SCIP es determinista: dos corridas de una misma configuración dieron exactamente 250.037 nodos y tiempos a 0,7%.
- **Las conclusiones no se transfieren** ni a la instancia de al lado. Cada vez que se generalizó un resultado de un punto a otro, una corrida controlada lo refutó (branching por pseudocosto, velocidades "neutras", pesos asimétricos corriendo el borde de la grilla). **Por eso cada test propuesto acá está medido sobre su propia instancia**, no extrapolado.
- **`limits/time` de SCIP no es un tope duro** (300 s terminaron en 3079 s). La suite de tests está protegida porque el runner mata el árbol de procesos; la herramienta de calibración ahora también.

---

## 3. Principios de diseño

Cada principio sale de una medición de la sección 2.

1. **Perfil realista fijo en todos los tests.** Pesos de grilla 4/5 (los pasillos no varían mucho), velocidades en **2 bandas** (0,8 y 1,2: cuadrilla de edad parecida, mismo carro, pero no idéntica), 26 órdenes por lote. Ninguna de las seis degeneraciones: `|B| > |P|`, sin lotes vacíos, fechas repartidas y alcanzables.

2. **Variar un solo eje entre tests.** Así el test donde cada modelo deja de resolver es directamente comparable, y la diferencia se puede atribuir. El eje elegido es el **tamaño del depósito**.

3. **El tamaño sale de la Etapa 1, no de la Etapa 2.** Con velocidades realistas, la Etapa 2 no tolera más de ~2 lotes por picker: 6 lotes/3 pickers resuelve, pero 6/4, 7/3 y 8/3 se pasan de 25 minutos. La Etapa 1, en cambio, escala de forma más predecible con la grilla, y es donde la descomposición del split tiene ventaja estructural sobre el mono.

4. **La forma del scheduling queda fija: 6 lotes sobre 3 pickers.** Su Etapa 2 mostró una dificultad estable frente al tamaño de la grilla (321.137 nodos en 7×7, 314.331 en 13×13), así que el costo de cada test queda gobernado por la grilla, que es lo que se quiere variar.

5. **Sin clausura métrica.** En estos tamaños la clausura cae al respaldo en 67–100% de los lotes y termina siendo más lenta (7×7: +75%; 13×13: +9%). Además es el default actual del `.env`. El respaldo parece venir de qué camino mínimo elige Dijkstra entre muchos empatados, así que podría arreglarse técnicamente; mientras tanto, afuera.

6. **Fechas de entrega sin calibrar.** El SLA lo fija el objetivo: con 26 órdenes por lote sale ~67%, dentro del rango donde adelanto y tardanza se ejercitan los dos.

7. **Tiempos calibrados de a una medición por vez.** La CPU es híbrida y de notebook: en paralelo los tiempos se inflan 2-3x. Los tiempos de la sección 5 se midieron con la máquina sola, que es como corre el runner.

## 4. Calibración

Herramienta: `python -m experiments.opp_v5.exploration --puntos <archivo>.json`. Cada configuración corre en su propio proceso con un kill duro de 25 min que cubre el árbol completo de procesos. Puntos y resultados en `experiments/opp_v5/studies/05_realistic_calibration/` (índice en `experiments/opp_v5/README.md`).

**Tiempos absolutos (de a una medición por vez, sin clausura)** — `solo_20260923_*.csv`:

| Depósito | Ubic./lote | Etapa 1 | Etapa 2 | **Total** | Nodos Etapa 2 | SLA |
|---|---|---|---|---|---|---|
| 7×7 | 18-22 | 9,6 s | 204,2 s | **3,6 min** | 321.137 | 67,9% |
| 13×13 | 23-26 | 445,3 s | 263,8 s | **11,8 min** | 314.331 | 67,9% |
| 15×15 | 24-26 | > 1500 s | — | **Etapa 1 > 25 min** | — | — |

**Mono sobre la misma instancia del 7×7** (en paralelo, así que su tiempo está inflado; la brecha no): a los 25 min, `timelimit` con **brecha de 144,3%**. El split la resolvió al óptimo.

**Formas de scheduling descartadas** (7×7, en paralelo, 25 min): 6 lotes/**4** pickers → brecha 1,09%; **7** lotes/3 → 2,6%; **8** lotes/3 → 9,48%. Ninguna terminó.

**Controles que validan las mediciones:**
- Con y sin clausura, la Etapa 2 dio exactamente el mismo conteo de nodos (321.137 en 7×7, 314.331 en 13×13): la clausura es exacta y la diferencia está toda en la Etapa 1.
- La misma instancia medida sola y en paralelo dio el mismo árbol exacto, 2,3x más rápido sola: la contención infla el reloj, no cambia el problema.
- El SLA dio 67,9% en todas, sobre la fórmula (67,3%).

## 5. Tests propuestos

**Perfil común a los tres** (lo único que varía es el depósito):

| Parámetro | Valor | Por qué |
|---|---|---|
| Lotes / pickers | 6 / 3 | 2 lotes por picker: el secuenciamiento se activa; más que eso no resuelve con velocidades realistas |
| Órdenes | 156 (26 por lote) | SLA ~67%: adelanto y tardanza se ejercitan los dos |
| Pesos de grilla | vertical 4, horizontal 5 | pasillos parecidos, no idénticos |
| Velocidades | 2 bandas: 0,8 y 1,2 | cuadrilla realista |
| Clausura | apagada | es el default y en estos tamaños es más lenta |

**Llamada al generador** (idéntica en split y mono, cambia solo `lado`):

```python
designed_stress_scenario(6, 3, 156, lado, lado,
                         speed_spread=0.2, speed_tiers=2,
                         vertical_weight=4, horizontal_weight=5)
```

| Test | Depósito | Split (medido solo) | Qué muestra |
|---|---|---|---|
| **09** | 7×7 (49 ubic.) | 3,6 min | Régimen cómodo. Comparación directa: el split resuelve rápido; el mono, medido, no llega en 25 min. |
| **10** | 13×13 (169 ubic.) | **11,8 min** | **El test de la franja 10-20 min.** Instancia realista y resoluble. |
| **11** | 15×15 (225 ubic.) | Etapa 1 > 25 min | **El techo.** Probablemente agota los 40 min del runner; marca dónde deja de alcanzar el enfoque exacto con este perfil. |

Aserciones: las mismas de hoy (`assert_stress_pipeline`): estado óptimo o factible, rutas que cubren las ubicaciones requeridas, todo lote con picker, sin solapamiento. No se agrega ni se quita ninguna.

**Para la fase siguiente (40 minutos o el tope):**
- **6 lotes / 4 pickers en 7×7** con el mismo perfil: quedó a 1,09% de brecha a los 25 min medidos en paralelo. Corrido solo podría entrar en 40. Es un test dominado por la Etapa 2, así que además sirve de referencia para cualquier intento de optimizarla.
- **14×14** con el mismo perfil: no medido. Queda entre 11,8 min y más de 25; si se quiere un segundo test en la franja, es el candidato.

## 6. Qué hacer con los tests existentes

| Tests | Propuesta | Por qué |
|---|---|---|
| 01–06, 08 (migrados) | **Dejarlos como están** | Comparan contra v4 con los mismos tamaños y tienen historia en `results/`. Sus degeneraciones quedan documentadas en `meta.md`; no se usan como evidencia de escalabilidad realista. |
| 07 (10 lotes, 25 pickers) | **Dejarlo con una nota** en el docstring y excluirlo de las comparaciones | Es el caso degenerado `\|P\| > \|B\|`. Borrarlo tira evidencia y rompe la numeración continua. |
| 09, 10, 11 (versión del 2026-09-22) | **Reemplazar su escenario** por el de la sección 5 | Usan velocidades y pesos uniformes. Existen en el repo pero sin commitear; el cambio es solo la llamada a `designed_stress_scenario` y el docstring, en split y en mono. |

Ya implementado (sin commitear), porque lo pediste explícitamente: `speed_tiers` en `designed_stress_scenario` y la herramienta de calibración con kill duro.

## 7. Riesgos y qué no sabemos

- **La Etapa 2 es muy sensible a la instancia.** Cambiar el seed, los pesos o la separación entre bandas mueve su costo mucho (0,7/1,3 con pesos 4/4 dio 134 s; 0,8/1,2 con pesos 4/5 dio 486 s, en el mismo tamaño). **Si se cambia el generador, estos tiempos hay que recalibrarlos.** Por eso cada test propuesto está medido sobre su propia instancia.
- **Los tiempos son de esta notebook.** En otra máquina los absolutos cambian; los conteos de nodos se mantienen para la misma versión de SCIP.
- **El mono no está medido en los tamaños propuestos corriendo solo.** Lo único medido: en 7×7, corriendo en paralelo, a los 25 min tenía brecha de 144%; el split encuentra ese mismo óptimo en 3,6 min solo (8,3 en paralelo). Que el mono no resuelva los tamaños mayores es inferencia; lo confirma la corrida de la suite.
- **Si se habilita la clausura** (`OPP_STAGE1_METRIC_CLOSURE=1`), la Etapa 1 cambia: +9% en 13×13, +75% en 7×7. No hace falta recalibrar para decidir, pero los tiempos de la sección 5 son sin clausura.
- **El `<= 1` no afecta esta propuesta.** Se probó sacarlo (solo en el split, sobre copias temporales): mismos objetivos en los 11 funcionales de ruta y mismos tiempos de ruta en 7×7 y 13×13, con velocidad que mejora en un tamaño y empeora en el otro. No es una palanca de rendimiento ni cambia respuestas.
- **Lo que limita la Etapa 1 en depósitos grandes no está identificado.** El salto de 13×13 (445 s) a 15×15 (más de 1500 s) es mucho más empinado de lo que sugiere el crecimiento de ubicaciones por lote (23-26 → 24-26). Si se quisiera agrandar la escalera, primero habría que entender eso.
- **Escalón de 40 minutos, para después.** El mejor candidato medido es 6 lotes / **4** pickers en 7×7: a los 25 min (en paralelo) tenía brecha de solo 1,09%. Corrido solo, podría terminar dentro de 40. Es además un test dominado por la Etapa 2, útil como referencia si se intenta optimizarla.
