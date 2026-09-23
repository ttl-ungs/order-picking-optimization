# Experimentos sobre opp_v5

Exploración que no son tests: barridos y calibraciones para entender dónde y por qué se rompe cada etapa del modelo, y para diseñar los tests de stress. Los tests responden "¿esta instancia resuelve?"; estos estudios dan la curva.

- `exploration.py` — herramienta para barridos y listas de puntos. Cada punto corre en su propio proceso y se mata desde afuera al agotar `tope_duro`: el `limits/time` de SCIP no es un tope duro. Escribe en el estudio que se le indica:

  ```
  python -m experiments.opp_v5.exploration --estudio 08_nombre --puntos experiments/opp_v5/estudios/08_nombre/puntos.json
  ```

- `propuesta_tests_stress.md` — el diseño de los tests de stress, que sintetiza los estudios 01–07. Usa la numeración vieja de los tests (ver aviso al principio del documento).
- `estudios/NN_nombre/` — un directorio por pregunta, con los puntos o scripts que se corrieron y los CSV que dieron. Los CSV conservan fecha y hora de la corrida en el nombre.

Los resultados viven acá y no en `results/<modelo>/<tier>/` a propósito: `analysis/load.py` hace glob sobre ese patrón y los tomaría como corridas de tests.

Las conclusiones completas están en `meta.md`; este índice solo resume y apunta.

## Estudios

| # | Pregunta | Conclusión | Entrada de `meta.md` |
|---|---|---|---|
| 01 | ¿Qué dimensión rompe primero? | Los lotes rompen la Etapa 2 (en 8); el tamaño del depósito rompe la Etapa 1 (15×15). Órdenes por lote y pickers no rompieron. | "Barrido de ejes 2026-09-22" |
| 02 | ¿Los pesos uniformes de la grilla son una degeneración? | Sí, por cobertura. Los pesos 2/6 aceleran la Etapa 1 hasta 3,7x en 7×7, pero la ventaja desaparece en 15×15: no es una optimización. | "Los pesos uniformes de la grilla son una degeneración cara" |
| 03 | ¿Las velocidades distintas encarecen el problema? | Todas distintas sobre un escenario sano: no. En bandas, como una cuadrilla real: el salto de 1 a 2 velocidades cuesta ~7x en la Etapa 2, y con 4 pickers no resuelve en 5 min. | "Las velocidades heterogéneas NO son inherentemente caras" y "Velocidades en niveles" |
| 04 | ¿El corte forzado por tiempo de la herramienta funciona? | Sí: mata el árbol de procesos y guarda la etapa en la que murió cada punto. | "`limits/time` de SCIP NO es un tope duro" |
| 05 | ¿Qué perfil realista cae en 10–20 min? | Solo, sin clausura: 7×7 3,6 min, 13×13 11,8 min, 15×15 > 25 min (Etapa 1). Mono en 7×7: brecha de 144% a los 25 min. De acá salieron los tests de stress 04–07. | "Tests de stress 09-11 con perfil realista" y `propuesta_tests_stress.md` §4 |
| 06 | ¿La clausura métrica sirve en depósitos realistas? | No: el 67–100% de los lotes vuelve a resolverse con el grafo completo. Se sacó del código. | "En un depósito real la ruta óptima repite pasillos" (y su corrección) y "Clausura métrica eliminada del código" |
| 07 | ¿El `<= 1` por vértice cambia las respuestas o el tiempo? | No cambia las rutas (11 funcionales de ruta y dos escalas de stress idénticas). En tiempo gana en una escala y pierde en la otra. | "⚠ Corrección 2026-09-23 - La entrada siguiente atribuye al `<= 1`…" |

## Cómo se corrió cada uno

Los scripts `.py` dentro de `estudios/` se guardaron **tal como se corrieron**. Varios ejecutan el experimento al importarse, así que `scripts/check_repo.py` no los importa. Todos, salvo el de 07, ponen `OPP_STAGE1_METRIC_CLOSURE=1`: la clausura ya no existe, así que si se vuelven a correr lo hacen con el grafo completo. Los objetivos dan igual, porque la clausura era exacta; los tiempos de la Etapa 1, no.

- **01** — `sweep.py`: 6 lotes / 2 pickers / 26 órdenes por lote / 7×7, un eje por vez, 300 s por solve; da `sweep_axes_*.csv`. `sweep_orders_50.py` extiende las órdenes por lote de 32 a 50 y da `sweep_orders_extended_*.csv`. `exploration.py` nació de estos dos scripts y hace el mismo tipo de barrido desde la misma base, pero sus rangos no coinciden exactamente (por ejemplo, lleva las órdenes por lote hasta 50 en una sola pasada). Para reproducir el CSV tal cual, hay que usar estos scripts.
- **02** — `exploration.py --pesos 2,6` da `pesos_asimetricos_*.csv`. `exploration.py --axes deposito --base 6,2,26,7 --pesos 2,6` da `deposito_controlado_pesos26_*.csv`.
- **03** — `exploration.py --velocidades 0.3` da `velocidades_dispares_*.csv`. `speed_tiers.py` da `niveles_velocidad_*.csv`.
- **04** — `exploration.py --puntos validar_kill.json --paralelo 3` da `validacion_kill_duro.csv`; con `validar_kill2.json` da `validacion_kill_duro_etapa1.csv`.
- **05** — `exploration.py --puntos` con `calibracion_ronda1.json` (4 en paralelo), `calibracion_ronda1b.json` (8 en paralelo) y `calibracion_solo.json` (de a uno). Solo los tiempos de `calibracion_solo` sirven como absolutos: los de las rondas en paralelo están inflados 2–3x por la CPU híbrida.
- **06** — `exploration.py --puntos clausura_realista.json --paralelo 6` da `clausura_realista_*.csv`; el archivo de puntos se borró junto con la clausura. `tasa_respaldo.py` midió cuántos lotes caían en el respaldo; depende del código de la clausura y ya no corre.
- **07** — `exploration.py --puntos prueba_le1_etapa1.json --paralelo 6` da `prueba_le1_etapa1_*.csv`: solo la Etapa 1, con y sin `<= 1`. `prueba_sin_le1.py` corrió los 11 funcionales de ruta con y sin `<= 1` e imprimió los resultados sin guardar CSV.
