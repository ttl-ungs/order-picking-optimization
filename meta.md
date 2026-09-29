# Meta del Repositorio

Este archivo funciona como resumen operativo del proyecto para trabajo compartido. Su objetivo es que una IA o un desarrollador pueda entender el estado actual del repositorio sin tener que leer todo el código ni la documentación completa.

> Regla de mantenimiento: cada cambio importante debe dejarse registrado en esta página. No se borra el historial anterior; se agrega un nuevo bloque al inicio o al final y se actualiza el estado general.

---

## 1. Resumen ejecutivo

- Proyecto: Linear Picking Routing
- Tipo: Optimización / routing de picking en almacén
- Stack principal: Python, PySCIPOpt, modelos exactos y heurísticos
- Estado actual: En desarrollo (limpieza y reorganización de repo en curso)
- Última actualización: 2026-09-19
- Responsable actual: Ebertz, Ximena; Soria, Lucía

### Objetivo del repositorio

- Resolver problemas de batching, asignación, secuenciación y routing de picking.
- Comparar modelos exactos y heurísticos bajo escenarios equivalentes.
- Mantener una estructura consistente para validación y análisis académico.

---

## 2. Estado actual del proyecto

### Estado general

- [x] Repositorio funcional en entorno local
- [x] Pruebas principales ejecutándose
- [x] Modelos comparables alineados (auditoría de código cerrada 2026-08-30/09-01, ver `analysis/README.md`)
- [ ] Documentación clave actualizada (en progreso, ver limpieza en curso más abajo)
- [x] Riesgos conocidos documentados (`analysis/README.md`, `docs/thesis/results_outline.md`)

### Contexto activo

- Modelo base / referencia: `opp_v4` (exacto, ZIMPL+SCIP), comparado también contra la familia v5: `opp_v5_1_mono` (exacto, MIP monolítico) y `opp_v5_2_split` (exacto, descomposición en 2 etapas; antes llamado `opp_v5`).
- Modelos alternativos vigentes: `opp_hc_2/3/4` (Hill Climbing), `opp_aco_2/3/4` (ACO).
- Alcance de la tesina confirmado (2026-09-17): solo `opp_v4` en adelante, incluyendo sus heurísticas. `opp`, `opp_v2`, `opp_v3`, `opp_hc`, `opp_aco` (sin numerar) son legacy — se mantienen en el repo por historial pero quedan fuera del alcance de la tesina.
- Aspecto prioritario actual: la limpieza y reorganización del repo quedó hecha (ver el bloque del 2026-09-17/19); falta la verificación a fondo de todas las suites y luego separar en un repo aparte lo que entra en la tesina (tarea futura, todavía no iniciada).
- Bloqueador actual: ninguno.

---

## 3. Cambios recientes

### Cambio 2026-08-18 09:00 - Estructura inicial de meta summary
- Autor: IA / equipo
- Alcance: documentación / colaboración
- Archivos principales: [meta.md]
- Qué se hizo:
  - Se agregó un resumen operativo para que la IA registre cambios y el contexto del repo.
  - Se define una estructura reutilizable para cambios, impacto y validación.
- Impacto:
  - Reduce la necesidad de leer todo el repositorio para entender el estado actual.
- Riesgo / atención:
  - Requiere mantener este archivo actualizado para que siga siendo útil.
- Validación:
  - Se verificó la existencia del archivo y su estructura inicial.


### Cambio 2026-08-18 - Normalización de suite opp_v4 y limpieza de tests migrados
- Autor: IA / equipo
- Alcance: tests / validación / comparación de modelos
- Archivos principales:
  - [tests/opp_v4/functional](tests/opp_v4/functional)
  - [tests/opp_v4/stress](tests/opp_v4/stress)
  - [tests/opp_v4/opp_test_case_v4.py](tests/opp_v4/opp_test_case_v4.py)
  - [tests/opp_hc_2/functional](tests/opp_hc_2/functional)
- Qué se hizo:
  - Se dejó la suite normal de opp_v4 alineada con la cobertura normal de opp_hc_2, sin mezclar casos de gran escala.
  - Se reubicaron los casos de stress grandes (12, 13, 14, y los de 24–27) al directorio de stress, manteniendo el normal más restringido a escenarios de tamaño controlado.
  - Se revisaron tests migrados que habían quedado con patrones legacy, como `if 'x' in locals()` y bloques `self.fail(... {e})` con variables indefinidas.
  - Se corrigieron archivos concretos con errores de análisis estático del IDE, especialmente en la normal 15 y en la stress 04–07.
- Impacto:
  - Mejora la coherencia entre suites de comparación y reduce los falsos positivos del IDE.
  - Deja la suite de opp_v4 más clara para distinguir normal vs stress y facilita la revisión de regresiones.
  - Aumenta la confianza en la migración entre versiones de tests y modelado.
- Riesgo / atención:
  - El conjunto de stress sigue siendo más pesado y requiere validación manual/por lote para casos de tamaño grande.
  - La comparación entre modelos exactos y heurísticos sigue dependiendo de que los escenarios representen el mismo problema y no solo el mismo nombre.
- Validación:
  - `git status --short` confirmó la reorganización del árbol de tests y la presencia de cambios relevantes en [tests/opp_v4/functional](tests/opp_v4/functional) y [tests/opp_v4/stress](tests/opp_v4/stress).
  - Verificación compilatoria del árbol v4: `NO_COMPILATION_ERRORS`.
  - Revisión del IDE en los archivos afectados: `No errors found` en los tests corregidos.

### Cambio 2026-08-18 11:15 - Ampliación de validación V4 y nuevos tests de stress
- Autor: [equipo / desarrollador actual]
- Alcance: tests / validación / infraestructura de comparación del modelo V4
- Archivos principales:
  - [tests/opp_v4/functional/test_case_22.py](tests/opp_v4/functional/test_case_22.py)
  - [tests/support/route_assertions.py](tests/support/route_assertions.py)
  - [tests/opp_v4/stress/test_case_15.py](tests/opp_v4/stress/test_case_15.py)
  - [tests/opp_v4/stress/test_case_16.py](tests/opp_v4/stress/test_case_16.py)
  - [tests/opp_v4/stress/test_case_17.py](tests/opp_v4/stress/test_case_17.py)
  - [tests/opp_v4/stress/test_case_25.py](tests/opp_v4/stress/test_case_25.py)
  - [tests/opp_v4/stress/test_case_26.py](tests/opp_v4/stress/test_case_26.py)
  - [tests/opp_v4/stress/test_case_27.py](tests/opp_v4/stress/test_case_27.py)
  - [tests/opp_v4/stress/test_case_28.py](tests/opp_v4/stress/test_case_28.py)
  - [tests/opp_v4/scenarios/stress/](tests/opp_v4/scenarios/stress/)
- Qué se hizo:
  - Se actualizó el test de ruta larga de V4 para validar un recorrido único que cubra los pedidos requeridos, en lugar de fijar una ruta concreta.
  - Se agregó un conjunto de helpers de validación de rutas para comprobar cobertura, ciclos y estructura de camino.
  - Se incorporaron nuevos tests de stress para V4, ampliando la cobertura de escenarios más complejos y con mayor cantidad de pedidos / rutas.
  - El estado del repo indica que varios archivos de scenario/test stress quedaron como nuevos y no aún consolidados en el árbol principal.
- Impacto:
  - Mejora la validación funcional del modelo V4 basados en el modelo V2, y ayuda a distinguir entre fallas reales del solver y aserciones demasiado rígidas sobre la ruta exacta.
  - Aumenta la capacidad de detectar regresiones y casos de caminos inválidos o ambigua ruta final.
- Riesgo / atención:
  - Algunos tests stress y escenarios aparecen como nuevos y pueden requerir inspección adicional para confirmar que están alineados con la convención del proyecto y con la lógica de escenarios de referencia.
  - La validación del comportamiento exacto sigue siendo sensible a la interpretación de penalizaciones por earliness/tardiness y a la estructura del grafo.
- Validación:
  - Evidencia del estado actual: `git status --short` muestra cambios en [meta.md](meta.md) y [tests/opp_v4/functional/test_case_22.py](tests/opp_v4/functional/test_case_22.py), además de nuevos archivos bajo [tests/opp_v4/stress/](tests/opp_v4/stress/) y [tests/opp_v4/scenarios/stress/](tests/opp_v4/scenarios/stress/).
  - No se afirmaron resultados de tests completos ni ejecución exitosa de la suite, porque esa verificación no se ejecutó en esta revisión.

---

### Cambio 2026-09-17/19 - Limpieza y reorganización del repo
- Autor: IA / Ximena Ebertz
- Alcance: documentación / infraestructura de análisis / tests (en curso)
- Archivos principales:
  - [analysis/config.py](analysis/config.py)
  - [analysis/run_stability_study.py](analysis/run_stability_study.py)
  - [meta.md](meta.md)
- Qué se hizo (fase 1 de varias, ver plan completo más abajo):
  - Se confirmó y documentó el alcance de la tesina: solo `opp_v4` en adelante, incluyendo sus heurísticas (`opp_hc_2/3/4`, `opp_aco_2/3/4`, `opp_v5`). Legacy (`opp`, `opp_v2`, `opp_v3`, `opp_hc`, `opp_aco`) se mantiene en el repo por historial pero queda fuera de ese alcance.
  - Se descartó usar Postgres/NoSQL para escenarios/grafos/resultados (`postgres-connection-pool` era para una fuente de datos real de empresa ya abandonada, no aplica a los escenarios generados proceduralmente que hay hoy).
  - Se unificó `analysis/run_stability_study.py::MODEL_REGISTRY`/`OUTPUTS_ROOT` para importar de `analysis/config.py` en vez de duplicar el registro, y se agregó una aserción para que ambos no se desincronicen.
  - Se eliminaron de `analysis/config.py::LATEST_FILE_OVERRIDES` las entradas huérfanas (`opp_v3`, `opp_aco` en stress) que ya no correspondían a ningún modelo en `MODEL_DIRS`.
  - Se completó el resumen ejecutivo y el contexto activo de este archivo (antes tenía placeholders de plantilla sin llenar).
  - Se centralizó el trío de escenarios realmente duplicado (`opp_v3`/`opp_aco`/`opp_hc_2`, byte-idénticos salvo la clase de DTO en `single_order_params.py`) en `tests/shared_scenarios/{common,normal,stress}/`. Se repuntaron 438 archivos de test en 9 paquetes (`opp_v3`, `opp_aco`, `opp_hc`, `opp_hc_2/3/4`, `opp_aco_2/3/4`, más las stress de `opp_v4`) — incluido `opp_hc` (legacy sin numerar), que dependía de `opp_v3/scenarios` sin estar documentado previamente. Se borraron las 39 copias duplicadas que quedaron redundantes. `single_order_params.py` no se colapsó en un solo archivo: quedó una variante por familia de DTO (`single_order_params_{opp,hc,hc4,aco,aco4}.py`) para no mezclar formas incompatibles.
  - Se movieron los escenarios propios de `opp_v4` (normal + la copia de `scenario_custom_setup` que `opp_v5` necesita) y `opp_v5` a `tests/shared_scenarios/`, con sufijo `_v4`/`_v5` en el nombre de archivo para no mezclarse con el trío compartido ni entre sí (ej. `scenario_01_v4.py`, `two_stage_scenarios_v5.py`). Ya ningún modelo tiene su propia carpeta `scenarios/`.
  - Se creó `tests/run_suite.py`, un único script parametrizado (`python -m tests.run_suite <modelo> <functional|stress> [--id NN]`) que reemplaza los ~24 `execute_tests.py`/`execute_stress_tests.py` casi idénticos, uno por modelo. Se actualizaron todas las referencias en docs (`analysis/README.md`, `analysis/run_analysis.py`, `analysis/load.py`, READMEs de `opp_hc`, `opp_hc_2`, `opp_hc_4`, `opp_aco_4`). Los legacy `opp`/`opp_v2` quedan con sus propios scripts (no usan `TestRunner`, estructura distinta).
  - Se creó `tests/support/family_case.py::family_case()` (mismo mecanismo que `tests/support/migrated_case.py::migrated_case()`, generalizado): parchea a nivel de módulo, solo durante `setUp`/`tearDown` de cada test, los nombres de clase (modelo/DTO/output_handler) que un archivo de test de `opp_hc_2`/`opp_aco_2` resuelve en tiempo de llamada — permite que `opp_hc_3`/`opp_hc_4` y `opp_aco_3`/`opp_aco_4` reutilicen el mismo archivo base sin tocar una sola aserción. El parcheo es *scoped* a la duración de cada test (no permanente) para que dos familias que comparten el mismo módulo base no se pisen si corren juntas en el mismo proceso — verificado explícitamente corriendo las 4 familias juntas (215 tests, 0 errores).
  - Con esa factory, se convirtieron **140 archivos** de duplicado literal a una sola línea de factory, en las 4 familias (`hc_3`: 24 normal; `hc_4`: 23 normal + 9 estrés; `aco_3`: 24 normal + 17 estrés; `aco_4`: 23 normal + 20 estrés). Se dejaron sin tocar los archivos con contenido propio de cada familia (congestión, cadena de frío, tests con aserciones reescritas) y los que no tienen equivalente en la base.
  - En el camino se encontró y corrigió un bug real: los tests `22_23` de `opp_hc_4` y `opp_aco_4` se habían clasificado mal como duplicados literales (su diff con la base solo mostraba líneas de import, pero importan un helper de escenario con DTO distinto que la factory no puede alcanzar) — se detectó porque las suites pasaron de 0 a 2 errores tras convertirlos, se revirtieron ambos archivos a su contenido original y quedaron excluidos de la conversión.
  - **2026-09-19** — `tests/outputs/` pasó a `results/` de primer nivel (son datos generados, no tests): `TestRunner` escribe en `results/<modelo>/<tier>/` y `analysis/config.py::OUTPUTS_ROOT` lee de ahí. Estructura plana, sin `archive/` (decisión de estructura pendiente, ver más abajo). `analysis/output/` (reporte y gráficos) no se movió.
  - **2026-09-19** — Los modelos sin sufijo de versión pasaron a llamarse como sus hermanos: `opp`→`opp_v1`, `opp_hc`→`opp_hc_1`, `opp_aco`→`opp_aco_1` (en `models/`, `tests/` y `results/`; también el módulo principal de cada paquete). `dtos/opp/` no es un modelo (DTOs del problema OPP) y conserva su nombre. La `OPPTestCase` base, que usaban ~349 tests de todos los modelos y vivía dentro del paquete legacy, ahora está en `tests/support/opp_test_case.py`.
  - **2026-09-19** — Los escenarios propios de `opp_v1`, `opp_v2` y `opp_v2_zpl` también se movieron a `tests/shared_scenarios/` con sufijo (`_v1`, `_v2`, `_v2_zpl`). Los 20 archivos de escenarios de `opp_hc_1` eran idénticos byte a byte al trío compartido (el relevamiento inicial no los había contado) y se eliminaron. Ningún modelo tiene ya carpeta `scenarios/`.
  - **2026-09-19** — Se aplanó la estructura de tests: `tests/<modelo>/tests/{normal,stress}/` → `tests/<modelo>/{functional,stress}/`, con los helpers propios de cada modelo (`opp_hc_2_test_case.py`, `route_assertions.py`, `migrated_case.py`, ...) directamente en `tests/<modelo>/`. `normal` pasó a llamarse `functional` en todos lados: tests, `shared_scenarios/functional/`, `results/<modelo>/functional/` (66 CSV renombrados, contenido intacto) y `analysis/` (`SCENARIOS`, `run_analysis.py`, `load.py`). La ruta `sys.path` de los archivos movidos se acortó un nivel para que sigan resolviendo la raíz al correrse directo.
  - **2026-09-19** — Los archivos de test pasaron a `test_case_<numero>.py` (continuo, sin huecos, por modelo y tier) o `test_case_<slug>.py` (tests propios de una familia). Sin nombre de modelo ni la palabra "model". 608 archivos renombrados; se reescribieron todas las referencias (cadenas de las factories, imports, docs `test_cases_functional.md` de cada modelo).
  - **2026-09-19 (rama `cleanup/support-and-docs`, apilada sobre `cleanup/repo-reorg`)** — La infraestructura de tests quedó agrupada en `tests/infra/`, en cuatro grupos: `execution/` (`runner.py`, `config.py`), `cases/` (`opp_test_case.py`, `route_assertions.py`, que estaba duplicado byte a byte en `opp_v2` y `opp_v4`), `factories/` (`family_case.py`, `migrated_case.py` —antes `tests/opp_v5/v4_compat.py`— y `graphs_factory.py`, antes el paquete `graphs/` de la raíz) y `zimpl/` (`zpl_utils.py` y `dat_files_builder.py`, que salió de `models/utils/`; solo lo importan tests). Con eso los modelos vigentes ya no dependen de ningún directorio legacy. Primero se había agrupado todo en un único `tests/support/`, que mezclaba cosas sin relación; se reagrupó por uso.
  - **2026-09-19** — `tests/support/runner.py` ya corre en Windows (`resource` es opcional; la memoria pico se lee con la API de Windows). Antes `python -m tests.run_suite` fallaba al importar.
  - **2026-09-19** — Los `example_usage.py` de `models/` pasaron a `examples/<modelo>_usage.py`. `.env` dejó de versionarse (estaba con `WRITE_RESULTS_CSV=1`, lo que hacía que cada corrida escribiera CSV en `results/`); se agregó `.env.example` y se borró `RUN_LARGE_TESTS`, que nadie usaba.
  - **2026-09-19** — Documentación consolidada en `docs/`: `thesis/` (tex, pdf y `results_outline.md`), `guides/`, `specs/` (antes en la raíz) y `tests/<modelo>/` (antes `tests/<modelo>/doc/`), con índice en `docs/README.md`. Se corrigieron los enlaces de los `test_cases*.md`, que seguían apuntando a `_normal`.
  - **2026-09-19 (rama `cleanup/scripts`)** — Nuevo `scripts/`: `check_repo.py` (imports, capas, nombres, factories y referencias viejas), `run_all.py` (corre las suites y las compara contra `scripts/baseline_counts.json`, la cantidad de tests de cada suite en `main` antes de la reorganización) y `new_family_tests.py` (genera los archivos `family_case` de una familia nueva). `tests/run_suite.py` ganó `--allow-timeout`, `--timeout-minutes` y varios `--id`. **Resultado: las 26 suites (14 funcionales + 12 de estrés, todos los modelos) tienen exactamente los mismos conteos de tests que en `main`** (`python -m scripts.run_all --collect-only --profile full --tier all`); además pasan los funcionales de `opp_hc_1..4` y el estrés de `opp_hc_4` (con tope de 6 s por test).
  - **2026-09-19 (rama `cleanup/ci`)** — CI en GitHub Actions. `ci.yml` (por PR): `check_repo` + conteos de todas las suites contra la base (Python 3.12 y 3.13), funcionales de los modelos HC/ACO con un reintento si falla una suite (los tests de ACO sin `Seed` son estocásticos) y el subconjunto rápido de estrés con tope de 60 s por test. `nightly.yml` (diario o manual): todos los tests de estrés HC/ACO con tope por test (los timeouts se informan sin fallar) y los funcionales de `opp_v1..v3`. `opp_v4`/`opp_v5` no se ejecutan en CI (necesitan `zimpl`). Nuevo `scripts/make_stress_smoke.py` y `run_all --smoke/--retries`; el subconjunto de estrés (`scripts/stress_smoke.json`: 56 tests entre los 6 modelos) corre completo en ~33 s y pasa. Validando el comando del nocturno se vio que `opp_v2` también tiene la falla `test_bridge_earliness_order_size` (aserción de precisión numérica, valor 1.2e+21 por un big-M, igual que `opp_v3`); se comprobó contra `main` en un worktree que falla idéntico antes de la reorganización, y quedó registrada como falla conocida en `scripts/baseline_counts.json`. Lo mismo con `opp_v1` (`test_3_orders_1_mission_1_picker`: el grafo de salida no coincide con el esperado; falla igual en `main`); su suite completa tarda ~8 min por los solves reales de SCIP, y está en el job nocturno.
- Pendiente:
  - **Verificación a fondo**: durante esta limpieza se verificó con chequeos puntuales (los 847 módulos importan, algunos tests por familia pasan, el análisis reproduce el mismo reporte). Falta correr las suites completas de cada modelo y comparar contra los conteos conocidos.
  - **Estructura de `results/`**: decidir si se archivan las corridas superadas (hoy `opp_v4/functional` tiene 44 CSV, el análisis usa 1) y cómo.
  - Regenerar `analysis/output/` (el reporte pasa a decir `functional` en vez de `normal` y los gráficos a `mean_time_functional.png`); no se tocó a propósito.
  - Los `test_case_NN` de una familia derivada ya no coinciden en número con los de su base (numeración continua por modelo). El análisis une por nombre de método e instancia, no por número de archivo, así que no le afecta.
  - Separar en un repo aparte lo que entra en la tesina (tarea futura, no iniciada).
- Impacto:
  - Una sola fuente de verdad para qué modelos cubre el estudio de estabilidad de semilla; menos riesgo de que ese registro y `analysis/config.py` se desincronicen a futuro.
  - Ningún modelo (legacy ni vigente) depende ya de una carpeta `scenarios/` de otro modelo para sus propios tests — todo vive en `tests/shared_scenarios/`.
  - Un solo lugar (`tests/run_suite.py`) para correr cualquier suite, en vez de 24 scripts casi idénticos.
  - 140 archivos de test menos que mantener a mano en cada cambio futuro al comportamiento base de `opp_hc_2`/`opp_aco_2` — un fix ahí se refleja automáticamente en `hc_3`/`hc_4`/`aco_3`/`aco_4` sin tener que re-portar nada.
- Riesgo / atención:
  - Fueron cambios grandes (cientos de archivos por fase). Cada fase quedó en su propio commit y se puede revertir de forma independiente.
  - `opp_v4`, con la extensión de picker/asignación (`P`/`x`) en sus propios escenarios, NO es un duplicado del trío — se movió a `shared_scenarios/` con sufijo `_v4` sin fusionar contenido con nada.
  - Estrés de `opp_hc_3`: de los 20 archivos, solo 04/05/06 eran copias literales de `opp_hc_2` (convertidos a factory, pasan). Los otros 17 son escenarios genuinamente distintos que reusan el número de test — ej. `opp_hc_3` 12-19 son las instancias intermedias agregadas después, mientras `opp_hc_2` usa esos números para grillas gigantes; esa es la inconsistencia de numeración entre familias que resuelve la fase 3.
- Validación:
  - `python -m analysis.run_analysis` corrido antes y después: mismo conjunto de CSVs leídos, mismas filas/columnas en `analysis/output/report.md` (diferencias solo en el último dígito de punto flotante, sin relación con este cambio).
  - Suite normal de los 9 paquetes afectados por la centralización del trío corrida antes/después (vía `git stash`/`stash pop` para tener una base real): mismos conteos de test exactamente (`opp_v3` 48 con la misma 1 falla preexistente no relacionada — `test_bridge_earliness_order_size`, precisión numérica; el resto, 46-59 tests cada uno, todos OK sin cambios). Doble-verificado de forma independiente corriendo `opp_hc_2`, `opp_hc_4` y `opp_aco_3` manualmente después.
  - `opp_v4`/`opp_v5` normal y stress verificados antes/después del movimiento de sus escenarios propios: mismos conteos (`opp_v4` normal 46, `opp_v5` normal 53, `opp_v5` stress 8) — coincide con los números ya conocidos de `analysis/output/report.md`.
  - `tests/run_suite.py` verificado comparando la lógica de discovery (`start_dir`/`pattern`) contra la de los scripts originales para varios modelos y el modo `--id`: mismos test IDs encontrados en todos los casos.
  - Conversión a `family_case()`: conteos de test idénticos antes/después en las 4 familias, tier normal (`hc_3` 51, `hc_4` 51, `aco_3` 59, `aco_4` 54, todos `OK`) — verificado de forma independiente además de por el propio proceso de conversión. Tier estrés verificado por compilación (`py_compile`, 0 errores en 142 archivos) + chequeo de imports + comparación exhaustiva de imports contra el archivo base (0 discrepancias tras el fix del bug de arriba), más 2 corridas reales de punta a punta como muestra (`opp_hc_4` model_03, `opp_aco_3` model_04, ambas `OK`) — no se corrieron las 4 baterías de estrés completas por el tiempo que toman.
  - Chequeo de seguridad cruzada entre familias: las 4 familias completas (tier normal, 215 tests) corridas juntas en un solo proceso de Python — 0 errores, 0 fallas — confirma que el parcheo scoped a `setUp`/`tearDown` evita que `hc_3`/`hc_4` (o `aco_3`/`aco_4`) se pisen al compartir el mismo módulo base.


### Cambio 2026-09-21 - `opp_v5` pasa a familia v5.x: `opp_v5_1_mono` y `opp_v5_2_split`
- Autor: IA / Ximena Ebertz
- Alcance: modelos / tests / infraestructura (rama `align/opp-v4-with-v5`, apilada sobre `feat/ci-zimpl-opp-v4-v5`)
- Archivos principales:
  - [models/opp_v5_1_mono/opp_model_v5_1_mono.zpl](models/opp_v5_1_mono/opp_model_v5_1_mono.zpl)
  - [models/opp_v5_2_split/](models/opp_v5_2_split/)
  - [tests/opp_v5_1_mono/](tests/opp_v5_1_mono/)
  - [tests/opp_v5_2_split/](tests/opp_v5_2_split/)
  - [tests/infra/factories/migrated_mono_case.py](tests/infra/factories/migrated_mono_case.py)
  - [tests/infra/zimpl/dat_files_builder.py](tests/infra/zimpl/dat_files_builder.py)
- Qué se hizo:
  - Nuevo `opp_v5_1_mono`: el mismo problema que resuelve `opp_v5` (velocidad `V_p` por picker y cadena de frío), pero como un solo MIP en vez de dos etapas. Parte de `opp_v4` y agrega `V_p` (`t_exec_pb = tiempo_fijo + R_b_time / V_p`), la cadena de frío como cota `u_pb <= T_frio_max + 1e-9`, el objetivo `Σ v_b` y las filas de tardanza/adelanto solo para `Bn = 1`. `t_exec_b` y `w_b` se eliminan y `R_b_time` pasa a ser variable. `opp_v4` no se modificó y queda como referencia sin las extensiones.
  - `opp_v5` pasó a llamarse `opp_v5_2_split` (`models/`, `tests/`, `results/`, imports, `analysis/config.py`, `scripts/`, CI, y las clases base de tests, ahora `OPPTestCaseSplit`). No se tocaron `docs/thesis/`, `analysis/output/` ni las entradas anteriores de este archivo, que siguen diciendo `opp_v5`.
  - Tests de `opp_v5_1_mono`: los mismos 34 funcionales y 8 de estrés que `opp_v5_2_split` (31 migrados de v4 con `migrated_mono_case`, 3 propios portados), sin ningún test nuevo y con las assertions intactas. Único test de v5 no portado: `test_preflight_detects_when_no_picker_is_eligible` (usa `run_pipeline(solve_stage2=False)`, y el monolítico no tiene una etapa 1 separada).
  - `opp_v5_1_mono` quedó registrado en `scripts/run_all.py` (`NEEDS_ZIMPL`), `scripts/baseline_counts.json` (52 funcionales y 8 de estrés, contados desde su propio árbol: el baseline es de `main` antes de la reorganización y este modelo no existía) y `analysis/config.py` (`MODEL_DIRS`; `load_all` avisa y sigue si un modelo no tiene CSV todavía).
  - `build_dat_files` ahora escribe `velocities.dat` (`V_p = 1` para todos) y `frio.dat` (sin límite) cuando el escenario no los define, para que los tests de v4 corran contra el monolítico sin cambios.
- Pendiente:
  - **No se corrió ningún test en este cambio.** Correr las suites de `opp_v5_1_mono` y `opp_v5_2_split`, y comparar `obj_val` entre los dos sobre los mismos escenarios.
  - Agregar `opp_v5_1_mono` al nightly de CI (`exact-zimpl`). No se hizo a propósito: sin haber corrido la suite no se sabe cuánto tarda ni cuántos tests llegan al tope por test, y con el tope por suite de ese job un `TIMEOUT` funcional deja el nightly en rojo.
  - Con la formulación monolítica, `test_case_06` de v4 falló en una corrida previa. La hipótesis es que la ruta óptima no es única (el `v_pb` puede rellenarse hasta la fecha de entrega), pero no está confirmada.
  - Regenerar `analysis/output/` y decidir qué hacer con los nombres viejos de `docs/thesis/`.
- Impacto:
  - Permite comparar un modelo exacto monolítico contra su descomposición en dos etapas sobre el mismo problema.
  - Sin tests nuevos ni assertions modificadas, la comparación de `opp_v5_2_split` contra `opp_v5_1_mono` usa exactamente las mismas suites.
- Riesgo / atención:
  - Los dos modelos son equivalentes en definición y en valor óptimo (la ruta mínima domina a cualquier otra, y los lotes no interactúan en el ruteo), pero no en el conjunto de soluciones óptimas: el monolítico puede devolver rutas no mínimas con el mismo objetivo. Es un argumento por lectura, sin verificación empírica todavía.
  - Ambos dependen de que `M` y `M_seq` (500, fijo) cubran el horizonte de tiempo.
- Validación:
  - `python -m scripts.check_repo`: pasa completo (911 módulos importan, sin referencias a rutas viejas).
  - `python -m scripts.run_all --collect-only --profile full --tier all` (lo que hace el CI): las 28 suites coinciden con el baseline.
  - Sin corridas de tests.


### Cambio 2026-09-22 - Clausura métrica por lote en la Etapa 1 de opp_v5_2_split
- Autor: IA / equipo
- Alcance: infraestructura de tests / rendimiento del modelo exacto
- Archivos principales:
  - [tests/opp_v5_2_split/metric_closure.py](tests/opp_v5_2_split/metric_closure.py) (nuevo)
  - [tests/opp_v5_2_split/stage1_decomposition.py](tests/opp_v5_2_split/stage1_decomposition.py)
- Qué se hizo:
  - La Etapa 1 indexa `z_ijb`/`f_ijb` por `E`, así que cada lote cargaba una binaria por arista de TODO el depósito aunque solo tuviera que alcanzar un puñado de ubicaciones. Ahí se resolvían dos problemas a la vez: en qué orden visitar las paradas (TSP con extremos fijos, NP-difícil) y cómo caminar entre parada y parada (camino mínimo, polinomial).
  - Se reemplaza el grafo de cada lote por su clausura métrica sobre `{depot} ∪ requeridas ∪ {final}`, con los pesos de camino mínimo calculados con `scipy.sparse.csgraph.dijkstra`. El MIP queda solo con el ordenamiento. En grilla 100×100 con ~25 requeridas por lote, las aristas pasan de ~40.000 a ~700.
  - Se descartó la fórmula Manhattan cerrada (equivalente en estas grillas, verificada) porque hornea el supuesto de grilla sin obstáculos: con estanterías devolvería distancias MENORES que las reales, en silencio.
  - **Expansión obligatoria**: un arco de la clausura no es una arista del depósito, así que `_expand_to_real_arcs` reescribe `z_ijb` sobre aristas reales. Sin esto, los consumidores que reconstruyen el recorrido reciben arcos inexistentes (test_case_04/05/08 fallaban con distancia `inf`).
  - **Fallback obligatorio**: `one_input_arc_per_node`/`one_output_arc_per_node` son `<= 1`, o sea camino simple, mientras que la clausura deja que dos tramos crucen el mismo vértice. Si la expansión repite un vértice, ese lote se rehace con el grafo completo.
- Impacto:
  - Es **opt-in** vía `OPP_STAGE1_METRIC_CLOSURE=1`; apagado no cambia absolutamente nada.
  - El `<= 1` NO se relaja: cuando la expansión no repite vértices, la solución es factible en el modelo completo y alcanza la cota inferior de la relajación, por lo tanto es óptima para el modelo completo. La reducción es exacta, no heurística.
  - No se tocó ninguna assertion ni ningún `.zpl`.
- Riesgo / atención:
  - Incompatible con `OPP_STAGE1_WORKERS>1`: la combinación lanza `ValueError` explícito en vez de calcular algo distinto en silencio (el fallback necesitaría mandarle los `.dat` pristinos a cada worker, y `a_ni.dat` tiene millones de filas en las instancias grandes).
  - Dos problemas de escala pendientes antes de correr stress grande: `_closure_context` carga `a_ni.dat` entero (|N|×|V| = 7,5M de entradas en 100×100) y `metric_closure` rearma la matriz dispersa en cada lote siendo el mismo grafo siempre.
  - La ganancia está en la Etapa 1, que NO es el cuello de botella dominante (ver medición abajo).
- Validación:
  - Oráculo de distancias: `metric_closure` coincide exactamente con Manhattan pesado en grillas 6×7, 10×10, 5×8 y 12×12, incluidos pesos asimétricos (vw=3, hw=7). Omite pares inalcanzables en grafos desconectados y no rompe con entradas degeneradas.
  - **Equivalencia end-to-end**: suite funcional completa de `opp_v5_2_split`, 53 tests, comparada contra `results/opp_v5_2_split/functional/output_opp_v5_2_split_functional_tests_20260922_122540.csv` (grafo completo): **44 `obj_val` idénticos, 9 sin `obj_val` (infactibles en ambos lados), 0 diferencias, 0 cambios de status**.
  - Antes de agregar expansión + fallback, la misma comparación daba 4 `obj_val` distintos (test_case_09: 1833 → 15) y 3 tests en falla. Eso confirma empíricamente que la clausura sola es una relajación y que ambos mecanismos son necesarios.
  - Costo en la suite funcional: +58,6% (22,0s → 35,0s). Esperado y no representativo: son instancias donde `|K| ≈ |V|`, así que hay overhead sin nada que reducir.
  - **Etapa 1 aislada sobre escenarios de stress** (`solve_stage2=False`), grafo completo vs clausura:

    | Escenario | Lotes | Pickers | Grilla | Etapa 1 completo | Etapa 1 clausura | Mejora |
    |---|---|---|---|---|---|---|
    | test_case_05 | 10 | 10 | 10×10 | 11,18s | 7,76s | −31% |
    | test_case_06 | 25 | 10 | 10×10 | 131,71s | 88,17s | −33% |
    | test_case_07 | 10 | 25 | 10×10 | 9,12s | 7,41s | −19% |
    | test_case_01 | 30 | 30 | 25×25 | (medición en curso) | | |

  - La mejora sobre la Etapa 1 es consistente (19–33%), pero **no alcanza para destrabar ni un solo test de stress**, y conviene que quede escrito para no volver a recorrer este camino:
    - `test_case_07` resuelve su Etapa 1 en **9,12s** y aun así agota el timeout de 40 min: ~2.391 de los 2.400 segundos están en la Etapa 2. La clausura le ahorra 1,7s.
    - `test_case_05` completo tarda 98,89s, de los cuales la Etapa 2 se lleva 87,73s (88,7%).
    - `test_case_06` mejora 43,5s sobre un timeout de 2.400s: sigue sin terminar.
    - Prueba estructural: `test_case_07` (10 lotes, 25 pickers) tiene una Etapa 1 IDÉNTICA a la de `test_case_05` — mismos lotes, mismas órdenes, misma grilla — y lo único que cambia son los pickers, que aparecen ÚNICAMENTE en la Etapa 2.
  - Conclusión: el cuello de botella de los timeouts de stress es el scheduling (Etapa 2), no el ruteo. La clausura se justifica por lo que mejora la Etapa 1, no como solución a los timeouts.


### Medición 2026-09-22 - Dónde está el límite de opp_v5_2_split y qué NO lo mueve
- Autor: IA / equipo
- Alcance: caracterización experimental (sin cambios de código)
- Qué se midió: se partió del único escenario de stress que resuelve (`test_case_05`: 10 lotes, 10 pickers, 100 órdenes, grilla 10×10) y se caminó por cada eje por separado, con tope de 120s por solve de Etapa 2, comparando el branching por defecto de SCIP contra pseudocosto. Órdenes y grilla fijas en 100 y 10×10.

  **Eje pickers (10 lotes fijos):**

  | Lotes/Pickers | Etapa 2 default | Nodos | Gap | Resultado |
  |---|---|---|---|---|
  | 10 / 10 | 33,0s | 24.429 | 0% | óptimo |
  | 10 / 12 | 118,5s | 104.366 | 0% | óptimo (al límite) |
  | 10 / 14 | timeout | 44.215 | 5,8% | — |
  | 10 / 16 | timeout | **20** | 213,4% | — |
  | 10 / 18 | timeout | 366 | 374,0% | — |
  | 10 / 20 | timeout | 441 | 1538,3% | — |

  **Eje lotes (10 pickers fijos):**

  | Lotes/Pickers | Etapa 1 | Etapa 2 default | Gap | Resultado |
  |---|---|---|---|---|
  | 10 / 10 | 11,1s | 33,0s | 0% | óptimo |
  | 12 / 10 | 117,0s | timeout | 54,1% | — |
  | 14 / 10 | 202,7s | timeout | 89,4% | — |
  | 16 / 10 | 152,8s | timeout | 96,3% | — |

- Conclusiones:
  - **Los bordes de resolubilidad**: entre 12 y 14 pickers (con 10 lotes), y entre 10 y 12 lotes (con 10 pickers). La franja donde el split resuelve es angosta.
  - **El branching por pseudocosto NO sirve.** En ningún tamaño terminó donde el default no terminaba, y en 10/12 pasó lo contrario: el default resolvió en 118,5s y pseudocosto agotó el tope con 3,3% de gap. El 2,2x que había dado en 10/10 (33s → 15,9s) fue casualidad de una instancia; no generaliza ni al tamaño contiguo. **No usar como resultado.**
  - **Con muchos pickers el solver se atasca en la raíz**, no busca mal: en 10/16 exploró 20 nodos en 119s (6s por nodo) con gap de 213%. Más pickers agrandan el LP (X_pb y v_pb crecen con |P|) sin aportar al óptimo, y la cota dual ni arranca.
  - **La Etapa 1 también escala mal con los lotes**, lo que matiza la conclusión anterior de que era una fracción despreciable: pasa de 11,1s (10 lotes) a 117,0s (12) y 202,7s (14). Es despreciable frente a una Etapa 2 que cuelga, no en términos absolutos.
  - Sospecha a verificar antes de diseñar escenarios nuevos: el salto de la Etapa 1 puede venir del generador, no del modelo. `scenario_custom_setup` reparte órdenes con `sorted_locations[i % len(V)]` y lotes con round-robin, así que cambiar la cantidad de lotes cambia la GEOMETRÍA de las ubicaciones de cada lote (con 10 lotes quedan espaciadas de a 10, con 12 de a 12). Si es así, una escalera de dificultad mediría ruido geométrico además de tamaño.

### Barrido de ejes 2026-09-22 - Dónde rompe cada dimensión
- Datos crudos: [experiments/opp_v5/studies/01_axis_sweep/sweep_axes_20260922.csv](experiments/opp_v5/studies/01_axis_sweep/sweep_axes_20260922.csv) y [experiments/opp_v5/studies/01_axis_sweep/sweep_orders_extended_20260922.csv](experiments/opp_v5/studies/01_axis_sweep/sweep_orders_extended_20260922.csv). Se guardan en `experiments/opp_v5/studies/` y NO en `results/<modelo>/<tier>/` a propósito: `analysis/load.py::_pick_csv` hace `glob` sobre ese patrón y levantaría estos archivos como si fueran corridas de tests.
- Método: partir de la forma del stress 09 (6 lotes, 2 pickers, 26 órdenes/lote, grilla 7×7) y mover **un eje por vez**, con tope de 300s por solve, fijando el mejor valor antes de pasar al siguiente eje. Clausura métrica activada.

| Eje | Rango probado | Dónde rompe |
|---|---|---|
| Órdenes por lote | 10 → 50 | **nunca rompió** (a 50 o/L: Etapa 1 46,5s, Etapa 2 14,1s, óptimo) |
| Lotes | 6 → 8 | **rompe en 8** (timeout a 299,6s con 518.628 nodos) |
| Pickers | 3, 4, 5 | ninguno rompe, y **no es monótono**: 12,9s / 25,4s / 7,3s |
| Tamaño del depósito | 7×7 → 10×10 | no rompe, pero cuadruplica la Etapa 1 |

- **Dos ejes rompen, y en etapas distintas**: los lotes rompen en la Etapa 2 (8 lotes, timeout con 518.628 nodos) y el depósito rompe en la Etapa 1 (15×15, 464,41s contra un tope de 300s). Órdenes por lote y pickers no rompieron en ningún valor probado.
- **Corrección a lo afirmado antes**: el tamaño del depósito NO sale casi gratis con la clausura métrica. Misma configuración (6 lotes, 2 pickers, 26 órdenes/lote), la Etapa 1 va 12,87s → 50,40s → 464,41s al pasar de 7×7 a 10×10 a 15×15.
- **Y la explicación que se dio para esa corrección tampoco alcanza.** Se atribuyó a que una grilla más grande hace colisionar menos las órdenes, así que cada lote necesita más ubicaciones distintas, y esas son la dimensión cara. Los datos no lo sostienen: hay dos caminos para llegar a una cantidad parecida de ubicaciones por lote, y cuestan órdenes de magnitud distintos.

  | Camino | ubic/lote | Etapa 1 |
  |---|---|---|
  | 7×7, 26 órdenes/lote | 18-22 | 12,9s |
  | 7×7, 50 órdenes/lote | **29-33** | **46,5s** |
  | 15×15, 26 órdenes/lote | 24-26 | **464,4s** |

  Llegar a ~31 ubicaciones por lote agrandando los pedidos cuesta 46s; llegar a ~25 agrandando el depósito cuesta 464s. Diez veces más con MENOS ubicaciones. **El tamaño de la grilla cuesta por sí mismo, por un mecanismo no identificado.** Sospecha sin verificar: en una grilla mayor las distancias son numéricamente más grandes, lo que debilitaría la relajación lineal de la Etapa 1 (`subtour_elimination_bound` y los términos con `R_b`). No usar como explicación hasta medirlo — por ejemplo, misma grilla y mismas ubicaciones por lote, escalando solo `v_weight`/`h_weight`.
- **Corrección a la saturación esperada**: se predijo que las ubicaciones por lote saturarían cerca de 25-30 en una grilla 7×7 (47 pickeables). No satura de golpe, se acerca asintóticamente: a 32 o/L da 22-25, a 50 o/L da 29-33. Es el problema del coleccionista de cupones — con 50 extracciones sobre 47 casillas el esperado de distintas es ~31, que es lo medido.

### Hipótesis 2026-09-22 - Las fechas de entrega degeneradas hacen el problema MÁS difícil
- Estado: **hipótesis, no confirmada.** El tamaño y el SLA están confundidos en los datos disponibles.
- Observación (fase 1 del barrido anterior: 6 lotes, 2 pickers, grilla 7×7, subiendo órdenes por lote):

  | Órdenes/lote | Etapa 2 | Nodos B&B | SLA a tiempo |
  |---|---|---|---|
  | 10 | **35,57s** | **153.934** | 96,7% |
  | 14 | 10,32s | 23.015 | 83,3% |
  | 18 | 6,32s | 4.059 | 75,9% |
  | 22 | 7,03s | 4.189 | 71,2% |
  | 26 | 7,98s | 4.144 | 67,9% |

- Qué llama la atención: la Etapa 2 se vuelve **más rápida al agrandar la instancia** (35,6s → 7s), en contra de lo esperable, y lo hace en paralelo con la caída del SLA (96,7% → 67,9%). El árbol de búsqueda se derrumba **37x** (153.934 → 4.144 nodos), que es evidencia estructural y no solo de reloj.
- Mecanismo propuesto: con casi todas las órdenes a tiempo, las variables `ta_n` quedan en cero y el objetivo se aplana — reordenar los lotes casi no cambia su valor, así que el solver no puede discriminar entre soluciones y le cuesta demostrar optimalidad. Con el SLA cerca del 70% hay órdenes en el límite, el secuenciamiento tiene consecuencia y el objetivo discrimina.
- Por qué importa si se confirma: las fechas degeneradas no solo dejan media función objetivo sin ejercitar (ver degeneración 3 más abajo) — **también encarecen la resolución**. Los escenarios migrados están en el extremo degenerado opuesto, `sla_on_time_pct = 0.0`, todas tarde, y todos dan timeout. Podría ser parte de la causa.
- ~~Cómo confirmarlo: fijar tamaño y variar ÚNICAMENTE la ventana de fechas de entrega.~~ **Ese experimento está mal planteado — ver la entrada siguiente.** Mover la ventana no mueve el SLA, porque el SLA no lo fijan las fechas sino la función objetivo.

### Resultado analítico 2026-09-23 - El SLA lo fija el objetivo, no las fechas de entrega
- **Enunciado**: con fechas de entrega repartidas y alcanzables, la proporción de órdenes a tiempo es
  **SLA = (N_b + W_full) / (2 · N_b)**, con N_b = órdenes por lote y W_ea = W_ta = 1.
- **Derivación**: el objetivo es `W_full·Σ v_b + W_ea_ta·(W_ea·Σ ea_n + W_ta·Σ ta_n)`. Demorar un lote una unidad de tiempo cuesta `W_full` más una unidad por cada orden suya que ya está tarde, y ahorra una unidad por cada orden que todavía llegaría temprano. Así que al óptimo el modelo **demora cada lote** mientras #tempranas > #tardías + W_full, y se detiene cuando #tempranas − #tardías ≈ W_full. Con #tempranas + #tardías = N_b, eso da #a_tiempo ≈ (N_b + W_full)/2.
- **Verificación** contra los 8 tamaños medidos (W_full = 9):

  | Órdenes/lote | SLA medido | Predicho | Error |
  |---|---|---|---|
  | 10 | 96,7% | 95,0% | +1,7 |
  | 14 | 83,3% | 82,1% | +1,2 |
  | 18 | 75,9% | 75,0% | +0,9 |
  | 22 | 71,2% | 70,5% | +0,7 |
  | 26 | 68,3% | 67,3% | +1,0 |
  | 32 | 64,6% | 64,1% | +0,5 |
  | 40 | 61,7% | 61,3% | +0,4 |
  | 50 | 59,3% | 59,0% | +0,3 |

  Ocho de ocho dentro de 1,7 puntos, y el error se achica con N_b (el sesgo positivo viene de las órdenes que caen exactamente en su fecha, que cuentan como a tiempo). Los barridos de velocidades en niveles a 26 órdenes/lote dieron 67,9–69,2%, también sobre la curva.
- **Consecuencias**:
  1. La hipótesis anterior ("las fechas degeneradas encarecen la Etapa 2") **no se puede testear moviendo la ventana de fechas**: el SLA y las órdenes por lote están atados por el objetivo. Para separarlos hay que variar `W_full`. El efecto observado (Etapa 2 más rápida con más órdenes por lote) puede deberse a N_b tanto como al SLA; queda sin atribuir.
  2. **Para diseñar escenarios no hace falta calibrar las fechas**: alcanza con que estén repartidas y sean alcanzables. El SLA sale solo, del orden del 67% con 26 órdenes por lote.
  3. El SLA de 0% de los escenarios migrados no contradice la fórmula: `Dd = 30` para todas es idéntica e inalcanzable (antes de cualquier finalización posible), así que la precondición no se cumple.
  4. **El modelo es "just-in-time"**: inserta tiempo ocioso a propósito para no entregar temprano, siempre que N_b > W_full. Eso lo convierte en un problema de scheduling con objetivo de adelanto/tardanza (no regular), una clase notoriamente difícil: `v_pb` no tiene una cota superior natural, solo la que le impone el objetivo. **Relevante para cualquier intento de optimizar la Etapa 2.**

### Medición 2026-09-23 - Los pesos uniformes de la grilla son una degeneración cara
- Datos crudos: [experiments/opp_v5/studies/02_grid_weights/asymmetric_weights_20260922_235622.csv](experiments/opp_v5/studies/02_grid_weights/asymmetric_weights_20260922_235622.csv) y [spread_speeds_20260922_235629.csv](experiments/opp_v5/studies/03_picker_speeds/spread_speeds_20260922_235629.csv).
- Comparación controlada: mismo seed (o sea ubicaciones por lote idénticas), y pesos 2/6 elegidos para que la **media siga siendo 4,00** igual que el 4/4 de la base. Lo único que cambia es la asimetría, no la magnitud.

| Órdenes/lote | Etapa 1 con 4/4 | Etapa 1 con 2/6 | Ratio |
|---|---|---|---|
| 10 | 3,66s | 2,11s | 1,7x |
| 14 | 3,04s | 1,72s | 1,8x |
| 18 | 5,79s | 2,54s | 2,3x |
| 22 | 8,32s | 3,02s | 2,8x |
| 26 | 12,87s | 5,63s | 2,3x |
| 32 | 22,67s | 7,54s | 3,0x |
| 40 | 30,81s | 10,29s | 3,0x |
| 50 | 46,46s | **12,60s** | **3,7x** |

- El mecanismo: con todas las aristas valiendo 4 hay cantidades enormes de rutas que empatan en costo exacto, y la Etapa 1 tiene que recorrer esos óptimos equivalentes para probar que no hay nada mejor. Con 2 y 6 los empates se rompen.
- **Alcance 1: es una mejora de la Etapa 1, no del sistema.** La Etapa 2 es prácticamente indiferente — sube y baja sin patrón dentro del ruido (10,32 → 11,74; 6,32 → 10,27; 14,07 → 18,16; 14,05 → 13,18). La única excepción es el punto degenerado de 10 órdenes/lote, con SLA 96,7%, donde baja de 35,57s a 16,53s y los nodos de 153.934 a 65.954.
- **Alcance 2 — y esto anula su valor como optimización: la ventaja se evapora al crecer la grilla.** Corrida controlada (mismas 26 órdenes/lote, mismos 2 pickers, mismo seed, solo cambian los pesos), archivo `experiments/opp_v5/studies/02_grid_weights/warehouse_size_weights26_20260923_001445.csv`:

  | Grilla | Etapa 1 con 4/4 | Etapa 1 con 2/6 | |
  |---|---|---|---|
  | 7×7 | 12,87s | 7,24s | 1,8x mejor |
  | 10×10 | 50,40s | 24,29s | 2,1x mejor |
  | 15×15 | 464,41s | **520,20s** | **0,9x, peor** |

  Se había proyectado que con un 2x sostenido el 15×15 caería a ~230s y correría el borde del depósito. No ocurre: a 15×15 la ventaja desaparece por completo. **Los pesos asimétricos ayudan donde no hacía falta y dejan de ayudar donde sí.**
- Hipótesis para ese desvanecimiento (sin verificar): en una grilla chica con pesos uniformes hay pocos valores de distancia distintos, así que los empates abundan y romperlos rinde. En una grilla grande los caminos mínimos ya toman muchos valores distintos aun con pesos uniformes — los empates se rompen solos por tamaño y la asimetría no agrega nada.
- **Conclusión**: sigue siendo la sexta degeneración y conviene corregirla **por cobertura**, porque una grilla uniforme no representa un depósito real. Pero **no sirve como optimización de rendimiento**.

### Corrección 2026-09-23 - Las velocidades heterogéneas NO son inherentemente caras
- Lo registrado antes: "con velocidades distintas el mismo escenario pasa de 33s a más de 600s, o sea que el caso que v5 vino a modelar es MÁS duro". Eso se midió sobre `test_case_05` y **no generaliza**.
- Barrido controlado (6 lotes / 2 pickers, velocidades repartidas en [0,7 , 1,3], seis tamaños): la Etapa 2 queda prácticamente igual que con velocidades uniformes — a 26 órdenes/lote, 8,41s contra 7,98s, y 3.819 nodos contra 4.144. La Etapa 1 replica la base casi exactamente, que es el control correcto porque `V_p` solo entra en la Etapa 2.
- El único punto donde empeoran es a 10 órdenes/lote, justo donde el SLA es 96,7% y el objetivo está aplanado.
- Explicación: `test_case_05` es 10 lotes / 10 pickers con `sla_on_time_pct = 0.0` — régimen de asignación pura con fechas degeneradas. Aquel 18x era una **interacción con esa degeneración**, no una propiedad de la heterogeneidad de velocidades. Sigue valiendo que ningún escenario de stress ejercita `V_p` heterogéneo, que es el hueco de cobertura real.

### Medición 2026-09-23 - Velocidades en niveles: lo realista es caro
- Datos crudos: [experiments/opp_v5/studies/03_picker_speeds/speed_tiers_20260923_003241.csv](experiments/opp_v5/studies/03_picker_speeds/speed_tiers_20260923_003241.csv).
- Motivo: la parametrización anterior repartía `V_p` en abanico continuo, una velocidad distinta por picker. Una cuadrilla real no es así — se contrata en un grupo etario parecido y todos empujan el mismo carro, así que hay dos o tres bandas. Se agregó `speed_tiers` a `designed_stress_scenario` para reproducir eso: los pickers de una misma banda quedan intercambiables.
- Instancia fija: 6 lotes, 26 órdenes/lote, grilla 7×7, pesos 4/4. Solo varía cuántas velocidades distintas hay (spread 0,3, o sea bandas en [0,7, 1,3]). Tope de 300s por solve de Etapa 2.

| Pickers | Uniformes | 2 niveles | 3 niveles | Todas distintas |
|---|---|---|---|---|
| 3 | 17,73s | 134,16s | 113,51s | 112,67s |
| 4 | 26,29s | timeout (549.456 nodos) | timeout (204.217) | timeout (347.556) |
| 6 | 7,22s | 110,38s | **3079,24s**, 499 nodos | no se midió |

- **El escalón está en pasar de 1 a 2 velocidades.** Cualquier heterogeneidad cuesta ~7x con 3 pickers; agregar más niveles no suma. Con 4 pickers ya no resuelve ninguna configuración heterogénea en 5 minutos.
- **Consecuencia central: con 6 lotes y 4 pickers —una configuración chica y perfectamente realista— basta con dos categorías de velocidad para que la Etapa 2 no termine en 5 minutos.** Todos los bordes mapeados antes (8 lotes, 15×15) se midieron con velocidades uniformes, o sea sobre el caso artificialmente fácil. Con velocidades realistas el alcance del modelo es bastante menor.
- Excepción que conviene entender: con 6 pickers para 6 lotes (`|B| = |P|`), 2 niveles resuelve en 110s. Es el régimen de asignación pura — cada lote toma su picker y no hay secuenciamiento — y ahí la heterogeneidad se tolera mejor. Pero `|B| = |P|` es justamente una de las degeneraciones de cobertura, así que no sirve como escenario de stress.
- Control de ruido: con 3 pickers, "3 niveles" y "todas distintas" resultan la MISMA configuración (ambas dan 0,7 / 1,0 / 1,3). Dieron **exactamente los mismos 250.037 nodos** y tiempos a 0,7% (113,51 vs 112,67s). SCIP es determinista dado el mismo input: el ruido de medición sobre una misma instancia es ~1%. La variabilidad grande que se vio durante el día (pseudocosto ganando en 10/10 y perdiendo en 10/12) es ENTRE instancias distintas, no entre corridas. O sea: comparar sobre la misma instancia es confiable, y las conclusiones no se transfieren a la instancia de al lado.

### Cambio 2026-09-24 - Matemática en línea de los documentos ConTeXt; generadores de los reportes al repo
- **Matemática en línea rota**: en ConTeXt `\(…\)` no abre modo matemático; se imprime como texto (`(Rt_b)` con el guion bajo literal, `\ne` desaparece, `10^-9` con el circunflejo). Afectaba 56 fórmulas en [docs/thesis/opp_v5_models.tex](docs/thesis/opp_v5_models.tex) (49), [opp_v5_1_mono_vs_opp_v5_2_split_comparison.tex](docs/thesis/opp_v5_1_mono_vs_opp_v5_2_split_comparison.tex) (6) y [opp_v4_vs_opp_v5_comparision.tex](docs/thesis/opp_v4_vs_opp_v5_comparision.tex) (1). Se reemplazó por `$…$` (pares verificados balanceados y sin `$` adentro), se recompilaron los tres PDF sin errores y se revisó una página renderizada. **Usar siempre `$…$` o `\startformula`.**
- **Generadores de los reportes**: pasaron de la carpeta temporal de la sesión a [experiments/opp_v5/reports/](experiments/opp_v5/reports/) (`charts.py`, `build_split_exploration.py`, `build_mono_exploration.py` y sus plantillas). Rutas relativas, imports absolutos, y los gráficos se arman dentro de `build_figures()`, así que importar los módulos no hace nada. Verificado: los dos `.tex` que generan son idénticos byte a byte a los que ya estaban. **Los documentos se editan en las plantillas, no en el `.tex` generado.**
- Traducción a inglés de `experiments/`: los 5 scripts copiados (comentarios, columnas y mensajes; columnas verificadas iguales a los encabezados de sus CSV) y `stress_test_design.md` (con una nota arriba sobre lo que cambió después: numeración, clausura, alcance del `<= 1`, flags).

### Cambio 2026-09-24 - Limpieza de corridas de opp_v5 (split y mono)
- **Stress de split**: la corrida unificada es `results/opp_v5_2_split/stress/output_opp_v5_2_split_stress_tests_20260923_181823.csv` (tests 01–15). El usuario le agregó 01–03 desde la corrida del 22-09 (`…_20260922_123359`, numeración vieja); se completó la fila del 03, que venía del formato de agosto con 6 columnas, y se corrigieron los nombres de clase a los actuales. **01–03 salen de otra corrida (22-09, en secuencia, código de ese momento); 04–15, de la del 23-09 con `OPP_STAGE1_WORKERS=6`.** `…_20260923_142920.csv` y `…_152436.csv` (en secuencia, numeración vieja) también se borraron después: comparar corridas distintas no demuestra nada sobre el paralelismo (la Etapa 2, idéntica, variaba ×0,58–×2,01 entre corridas). La evidencia del paralelismo es el estudio 12; la sección de validación del documento de split usa ahora la corrida unificada (6 procesos).
- **Stress de mono**: la corrida unificada es `results/opp_v5_1_mono/stress/output_opp_v5_1_mono_stress_tests_20260923_230313.csv`: 04–07 (timeout) más el 01, tomado de la corrida del 22-09 (`…_20260922_123450`; allí era el 02, `no_result`). Los otros dos tests de esa corrida (viejos 01 y 03) ya no existen. 02, 03 y 08–19 de mono no se corrieron.
- **Borradas** (siguen en git): funcionales de mono `…_20260921_213334` y de split `…_20260921_214130`, `…_20260922_122540`, `…_20260922_195835` (el usuario vuelve a correr las suites funcionales, ahora con los tests 35–38); stress de split `…_20260922_123359` y de mono `…_20260922_123450`.

### Cambio 2026-09-24 - 10 tests funcionales nuevos en opp_v5 (split y mono): frío, velocidad, demora a propósito, `<= 1`
- Archivos: `tests/opp_v5_2_split/functional/test_case_35..38.py` y los mismos en `tests/opp_v5_1_mono/functional/`; escenarios nuevos en [tests/shared_scenarios/functional/two_stage_scenarios_v5.py](tests/shared_scenarios/functional/two_stage_scenarios_v5.py); conteos del baseline funcional 53 → 63 (split) y 52 → 62 (mono).
- Qué cubren (todos con valores exactos calculados a mano sobre la geometría de los escenarios v5):
  - **35, cadena de frío**: la parte fija cuenta para el límite (límite 8 entre la ruta, 7, y el total, 9 → infactible); el límite es por lote y no por turno (dos lotes solo elegibles para el rápido: terminan en 9 y 18, el segundo después del límite, objetivo 27); la tolerancia 1e-9 mantiene elegible a un picker a 5e-10 del borde.
  - **36, velocidad**: V = 4 → el rápido hace los dos lotes (5,5 y 11, objetivo 16,5); V = 2 → uno a cada picker (9 y 16, objetivo 25); con V = 0,5 el atraso usa el tiempo escalado (termina en 30, atraso 10, objetivo 310); velocidades 0 y −1 se rechazan antes de resolver nombrando al picker.
  - **37, demora a propósito**: 3 órdenes, fecha 20, lo antes posible 9. Con W_full = 1 el modelo demora el lote hasta 20 (objetivo 20); con W_full = 5 no lo demora (termina en 9, adelanto 11 por orden, objetivo 78). Fija el comportamiento detrás de la fórmula del SLA.
  - **38, límite del `<= 1`**: un centro con dos pasillos sin salida no tiene ruta (hay que pasar tres veces por el centro) → infactible. Documenta la limitación; si se saca el `<= 1`, la expectativa cambia.
- **Bug encontrado por el test de velocidad 0 (split)**: `run_pipeline` validaba las velocidades después de `build_dat_files`, cuyo cálculo de `M_seq` divide por la velocidad mínima → con V = 0 reventaba con `ZeroDivisionError` antes de la validación. Se movió la validación al principio (mono ya la tenía primero). Ninguna aserción se tocó.
- **Clases base**: `eligible_pairs` (split y mono) no aplicaba la tolerancia 1e-9 que usan los dos modelos y el chequeo previo; ahora usa `COLD_CHAIN_TOLERANCE`. Sin efecto en los tests existentes (sus valores son exactos). Nueva ayuda `objective_value()`.
- **Diferencia de tolerancias entre modelos, documentada y sin test**: en split la elegibilidad de frío es un filtro exacto (+1e-9); en mono es una restricción que SCIP respeta con su tolerancia de factibilidad (~1e-6, y más con big-M), así que muy cerca del borde (entre 1e-9 y ~1e-6 por encima del límite) mono podría aceptar un par que split rechaza. Por eso el test de tolerancia solo prueba el lado de "entra".
- Validación: los 10 tests pasan en los dos modelos con los mismos valores.

### Medición 2026-09-24 - Paralelismo de la Etapa 1: divide el tiempo por ~2 (A/B controlado, estudio 12)
- **Medición controlada** ([experiments/opp_v5/studies/12_stage1_parallel/](experiments/opp_v5/studies/12_stage1_parallel/)): solo la Etapa 1 de las instancias exactas de los tests 05 (13×13) y 06 (14×14), máquina sola (la suite de mono se frenó para esto), orden ABBA (sec–par–par–sec) contra el calentamiento. 13×13: 241,8 / 243,8 s secuencial contra 110,1 / 110,8 s con 6 procesos → **×2,2**. 14×14: 401,4 / 405,6 s contra 209,5 / 215,9 s → **×1,9**. Repeticiones a menos de 3% entre sí; rutas idénticas. Nueva clave de punto en `exploration.py`: `stage1_workers`.
- Por qué no ×6: el tiempo paralelo queda atado al lote más lento, y la CPU tiene 4 núcleos de rendimiento + 8 de eficiencia (~mitad de velocidad). Efecto sobre el test completo: 13×13 de ~6 a ~4 min; 15×15 de ~28 a ~15 min; nada en instancias dominadas por la Etapa 2. En paralelo, `peak_rss_mb` solo cuenta el proceso principal.
- **El primer intento, comparar corridas distintas de la suite, no servía**:
- Datos: la suite de stress del split con `OPP_STAGE1_WORKERS=6` (`results/opp_v5_2_split/stress/output_opp_v5_2_split_stress_tests_20260923_181823.csv`, tests 04–15) contra las corridas en secuencia de los mismos tests (`..._20260923_142920.csv` y `..._152436.csv`, numeración vieja). Seis tests están en las dos: 04, 05, 06, 07, 09, 11. Todos con el mismo objetivo. Esos seis corrieron antes de que arrancara cualquier exploración.
- Etapa 1 (tiempo total menos Etapa 2) más rápida en paralelo en los seis: ×1,61 (7×7, 6 s → 4 s), ×1,82 (13×13), ×1,26 (14×14), ×1,15 (15×15), ×1,15 (8×21), ×1,74 (frío).
- Pero la **Etapa 2, que no se paraleliza y es idéntica en las dos corridas**, varió entre ×0,58 y ×2,01: ruido de la máquina entre corridas, del mismo tamaño que la mejora. **No se puede atribuir la mejora al paralelismo.**
- Techo estimado: el tiempo paralelo queda atado al lote más lento, y la CPU tiene 4 núcleos de rendimiento + 8 de eficiencia (~mitad de velocidad): difícilmente pase de ~3×. Para medirlo hace falta un A/B controlado: solo la Etapa 1 de una misma instancia (13×13 o 15×15), alternando secuencial y paralelo, con la máquina sola.
- Agregado como sección preliminar a [docs/thesis/opp_v5_2_split_exploration.tex](docs/thesis/opp_v5_2_split_exploration.tex).

### Verificación 2026-09-24 - Los tests funcionales sí ejercitan adelanto y atraso
- Pregunta pendiente desde el 2026-09-22: si el stress heredado tenía todas las órdenes tarde (`Dd = 30`), ¿los funcionales validan de verdad la mitad de adelanto del objetivo?
- Método: sin correr nada. Del CSV funcional del split (`results/opp_v5_2_split/functional/output_opp_v5_2_split_functional_tests_20260922_195835.csv`) se leyeron los valores de `ea_n` y `ta_n` de la salida de depuración de cada test. Los valores ≥ 1e19 son variables libres (su término tiene peso cero en ese test) y se descartaron.
- Resultado, sobre los 42 tests con solución: **7 mezclan órdenes a tiempo y atrasadas** (20, 24, 25 ×3, 26 `shared_locations`, 34), 5 tienen solo adelanto (entre ellos el de adelanto del 22), 19 solo atraso (casi todos los migrados de v4: todas las órdenes tarde, la misma degeneración del stress heredado) y 11 ninguno (terminan justo en fecha o el término pesa cero). Los 11 restantes son de infactibilidad o el timeout conocido del 30.
- Conclusión: **la rama de adelanto está validada en los funcionales**; solo los migrados de v4 son degenerados en este eje. Los modelos son equivalentes, así que vale también para mono. Pendiente cerrado en la memoria.

### Medición 2026-09-23/24 - Estudios 08 a 11: dónde deja de cerrar opp_v5_1_mono
- Datos: [experiments/opp_v5/studies/08_mono_frontier/](experiments/opp_v5/studies/08_mono_frontier/) y [experiments/opp_v5/studies/09_shared_with_split/](experiments/opp_v5/studies/09_shared_with_split/). Documento: [docs/thesis/opp_v5_1_mono_exploration.tex](docs/thesis/opp_v5_1_mono_exploration.tex) (versión parcial; faltan los estudios 10 y 11).
- Método: puntos `pair` (la misma instancia por split y por mono; el óptimo del split es la referencia). 08: lotes {1,2,3,4,6} × grilla {3..7}, perfil realista, tope de 10 min por modelo. 09: las 15 instancias de los estudios 01/02/03 del split, límite de SCIP 300 s. **Corrieron en paralelo con la suite de stress del split** (unos 2 núcleos): tiempos absolutos inflados, proporciones split/mono comparables.
- Frontera del mono a 10 min: 3 lotes hasta 6×6 (139 s; split 5 s), 4 lotes hasta 5×5 (47 s; split 7 s), 6 lotes solo 3×3 (192 s; split 177 s). Primeras fallas: 3 lotes 7×7 (brecha 11,4%), 4 lotes 6×6 (13,2%), 6 lotes 5×5 (3,0%).
- **Encontrar no es el problema, demostrar sí**: en esas tres fallas el mono tenía una solución a menos del 1% del óptimo antes de los 75 s (en 6 lotes 5×5, el óptimo exacto a los 85 s), con la cota dual estancada entre 88% y 97% del óptimo.
- Cota raíz parecida a la de la Etapa 2 del split en casi todas las instancias (el secuenciamiento big-M es común a los dos). Excepciones con cota raíz del mono mucho peor: grilla 10×10 (39% vs 81%), velocidades en bandas (41–53% vs 76–87%), 6 lotes 5×5 (48% vs 87%).
- 09: las 15 instancias dieron **exactamente los mismos óptimos del split** que los estudios originales (confirma que son las mismas). El mono no demostró ninguna en 300 s y en 7 de 15 no encontró ni una solución factible; cuando encontró, quedó a 0,3–1,9% del óptimo (4,9% en una).
- Tamaño y memoria no son el límite: modelos de hasta 4.695 variables, memoria pico ≤ 302 MB, ZIMPL < 1 s.
- **Control de equivalencia**: en 15 puntos donde ambos probaron el óptimo, 14 dieron el mismo objetivo; en 3 lotes 6×6 el mono reportó 26.709,36 contra 26.709,60 del split (−0,0009%), los dos "optimal". Hipótesis sin verificar: tolerancia de integralidad con `M = 10^6` (misma clase que las fallas de precisión big-M de opp_v2/opp_v3).
- **Estudio 10** ([experiments/opp_v5/studies/10_mono_scale_axes/](experiments/opp_v5/studies/10_mono_scale_axes/)): las preguntas de 01/02/03/07 a escala de mono (base 4 lotes, 2 pickers, 26 órd./lote, 5×5, pesos 4/4; split 7 s, mono 17 s), un factor por vez, 10 min por modelo. Lo que más castiga al mono: la grilla (1,1× en 3×3 → 33× en 6×6 → no cierra en 7×7), las velocidades en bandas con 3 pickers (52×; con 3 bandas no cierra; el split no se inmuta a esta escala) y pocas órdenes por lote (188× con 10). Lotes y pickers pesan menos (1,2–8×); pesos 2/6 sin efecto sistemático; sin `<= 1`, mono 2× más lento en 5×5 y 2,4× más rápido en 6×6. Los 25 óptimos del mono coinciden exacto con los del split (también sin `<= 1`).
- **Estudio 11** ([experiments/opp_v5/studies/11_mono_long_cap/](experiments/opp_v5/studies/11_mono_long_cap/)): los tres puntos de falla del 08 y la instancia exacta del test 04, con tope de 40 min (en paralelo con la suite de stress del mono). **De 10 a 40 min la cota dual casi no se mueve**: 3 lotes 7×7 90,1% → 90,1% (brecha 11,4% → 11,0%, mejor solución a 0,05% del óptimo); 4 lotes 6×6 88,5% → 90,6% (13,2% → 10,4%; encontró el óptimo a los 972 s sin demostrarlo). Solo 6 lotes 5×5 cerró: óptimo demostrado a los 32 min (split: 3,9 min). **Test 04**: solución a 0,66% del óptimo, brecha 143,5%, cota dual 41% (39% en la raíz); igual que M0 a 25 min. Memoria pico a 40 min: hasta 636 MB.
- Predicción registrada antes de conocer la suite de stress del mono (lanzada por el usuario con los tests 04–19 mientras corría el estudio 10): **ninguno termina en 40 min**; test 04 (misma instancia que M0: brecha 144% a 25 min) con buena solución y brecha grande; en varios de los más grandes puede no haber solución que reportar.
- Incidente: un script de espera del estudio 08 que se creía detenido sobrevivió al TaskStop y relanzó el 08 a las 23:03, durante unos minutos en paralelo con la suite de mono del usuario. Se cortó y se borró su salida.

### Cambio 2026-09-23 - Resultados de exploración movidos a `experiments/opp_v5/studies/`
- Autor: IA / equipo
- Alcance: experimentos (no afecta tests ni análisis)
- Qué se hizo: `results/exploration/` ya no existe. Cada estudio tiene su directorio en `experiments/opp_v5/studies/NN_name/`, con los puntos o scripts que se corrieron y los CSV que dieron (01 barrido de ejes, 02 pesos de grilla, 03 velocidades, 04 validación del corte duro, 05 calibración realista, 06 clausura, 07 restricción `<= 1`). Directorios, archivos, encabezados de los CSV y claves de los JSON quedaron en inglés, como pide `conventions.md`; en los CSV solo se tradujeron encabezados y etiquetas, ningún número cambió (verificado celda por celda). Los `.json` de puntos se movieron de `experiments/opp_v5/` a su estudio. Se copiaron del scratchpad de la sesión los scripts que generaron 01, 03, 04, 06 y 07; si no, se perdían y esos CSV quedaban sin procedencia. El índice, con cómo se corrió cada uno, está en [experiments/opp_v5/README.md](experiments/opp_v5/README.md).
- Herramienta: `exploration.py` ahora exige `--study NN_name` y escribe ahí. Flags y claves de puntos en inglés (`--points`, `--hard-cap`, `batches`, `orders_per_batch`, `hard_cap_s`, ...). Suma el modelo `pair` (misma instancia por split y mono, con el óptimo del split como referencia para medir al mono), el registro de cada solución mejorada, cota dual raíz y final, tamaño del modelo y memoria pico, y el modo `--frontier` (grilla lotes × lado que se corta en la primera falla del mono).
- `scripts/check_repo.py`: `experiments/opp_v5/studies/` se agregó a `IMPORT_SKIP_PREFIXES`. Los scripts de los estudios se guardaron tal como se corrieron y la mayoría ejecuta el experimento al importarse, así que el chequeo de imports no debe tocarlos.
- Rutas actualizadas en meta.md, `stress_test_design.md` y la memoria. Único cambio en los scripts copiados: `speed_tiers.py` escribía en `results/exploration/`, que ya no existe, y ahora escribe en su propio directorio.
- El análisis de la tesis no cambia: solo lee `results/<modelo>/<tier>/`.

### Cambio 2026-09-23 - Clausura métrica eliminada del código
- Autor: IA / equipo
- Alcance: Etapa 1 de `opp_v5_2_split`, herramienta de exploración
- Archivos:
  - `tests/opp_v5_2_split/metric_closure.py`: borrado (nunca se commiteó).
  - [tests/opp_v5_2_split/stage1_decomposition.py](tests/opp_v5_2_split/stage1_decomposition.py): vuelve a la versión commiteada, más un único cambio que se conserva: la Etapa 1 corre **secuencial por defecto** (`OPP_STAGE1_WORKERS`, ver `.env.example`). Se sacaron `_closure_context`, `_narrow_to_batch`, `_expand_to_real_arcs`, `_solve_batch` y el chequeo clausura+paralelo.
  - [experiments/opp_v5/exploration.py](experiments/opp_v5/exploration.py): sin opción `--closure` ni clave `clausura` (que además estaba **encendida por defecto**). La columna `variante` sigue existiendo y vale `grafo`. Los `.json` de puntos viejos que tienen `"clausura": "0"` se siguen pudiendo correr: la clave se ignora.
  - `experiments/opp_v5/clausura_realista.json`: borrado (era la comparación con/sin clausura; ya no se puede reproducir).
- Por qué: era exacta (53/53 funcionales con el mismo objetivo), pero solo ahorra tiempo cuando el lote tiene pocas ubicaciones frente a la grilla y la ruta no repite vértices. En las grillas realistas el 67–100% de los lotes tuvo que volver a resolverse con el grafo completo, así que en los tests de stress no aportó. La entrada del 2026-09-22 ("Clausura métrica por lote en la Etapa 1") y las mediciones siguen valiendo como registro. El código borrado quedó sin commitear, así que no se puede recuperar de git.
- Impacto: ninguno en los tests, que ya corrían sin clausura (era opt-in con `OPP_STAGE1_METRIC_CLOSURE=1`, que no estaba seteada). Los CSV de `experiments/opp_v5/studies/` con `variante=clausura` quedan como datos históricos.
- Validación: `python -m scripts.check_repo` pasa; split funcional 01 y 09 pasan (`WRITE_RESULTS_CSV=0`, sin generar CSV); `exploration.py` compila.

### Cambio 2026-09-23 - Stress de opp_v5 depurado y renumerado: 23 → 19 tests (split y mono)
- Autor: IA / equipo
- Alcance: tests de stress de `opp_v5_2_split` y `opp_v5_1_mono` (los dos con la misma numeración y las mismas instancias)
- Archivos: `tests/opp_v5_2_split/stress/test_case_01..19.py`, `tests/opp_v5_1_mono/stress/test_case_01..19.py`, [scripts/baseline_counts.json](scripts/baseline_counts.json) (stress 8 → 19 en los dos).
- Qué se hizo:
  - **Eliminados** (heredados de v4, no suman): viejo 01 (30/30, 750 órdenes, 25×25), 03 (20/20, 600, 100×100), 04 (25/25, 100, 10×10), 06 (25 lotes/10 pickers, 100, 10×10). Todos con las degeneraciones documentadas (`|P| ≥ |B|`, velocidades uniformes, fechas imposibles) y sin eje propio frente a los que quedan.
  - **Conservados de los heredados**: viejo 02 (100×100, el más grande), 05 (10/10 en 10×10) y 08 (40 lotes, 1 picker, 7×7).
  - **Reemplazado**: viejo 07 (10 lotes/25 pickers, todo uniforme — qué pickers quedaban ociosos daba igual) → nuevo 15, ola sobredotada con perfil realista: `realistic_crew_scenario(10, batches=6, pickers=9)`, 5 pickers lentos y 4 rápidos, fechas 371–866.
  - **Renumeración** (nuevo ← viejo), agrupada por eje:

    | Nuevo | Viejo | Instancia |
    |---|---|---|
    | 01 | 02 | heredado 30/30, 750 órdenes, 100×100 |
    | 02 | 05 | heredado 10/10, 100 órdenes, 10×10 |
    | 03 | 08 | heredado 40 lotes/1 picker, 320 órdenes, 7×7 |
    | 04 | 09 | realista 7×7 |
    | 05 | 10 | realista 13×13 |
    | 06 | 12 | realista 14×14 |
    | 07 | 11 | realista 15×15 |
    | 08 | 16 | realista 16×16 |
    | 09 | 14 | realista rectangular 8×21 |
    | 10 | 13 | realista 7×7, 4 pickers (carga en Etapa 2) |
    | 11 | 15 | realista 13×13, 4 pickers, cadena de frío (`T_frio_max=280`) |
    | 12 | 17 | escalera de dotación: 8 lotes/4 pickers, 7×7 |
    | 13 | 18 | 10 lotes/5 pickers, 7×7 |
    | 14 | 19 | 12 lotes/6 pickers, 7×7 |
    | 15 | 07 (reemplazado) | ola sobredotada 6 lotes/9 pickers, 10×10 |
    | 16 | 20 | dotación grande: 12 lotes/12 pickers, 10×10 |
    | 17 | 21 | 15 lotes/12 pickers |
    | 18 | 22 | 18 lotes/12 pickers |
    | 19 | 23 | 24 lotes/12 pickers |

  - Se actualizaron los nombres de clase (`TestOPPSplitStressNN` / `TestOPPMonoStressNN`) y las referencias cruzadas por número en los docstrings. Los docstrings de 05, 06 y 07 dicen ahora los tiempos medidos (≈6, ≈7 y ≈28 min en split) en lugar de los objetivos de diseño.
- Impacto: **los CSV de stress anteriores a este cambio usan la numeración vieja** (p. ej. `..._20260923_142920.csv` tiene 09-11 = nuevos 04, 05, 07; `..._20260923_152436.csv` tiene 12, 14, 15 = nuevos 06, 09, 11). Ningún test de stress v5 había pasado completo antes, así que la corrida de referencia es la próxima.
- Riesgo / atención: el nuevo 15 y las escaleras 12-14 y 16-19 no se corrieron nunca completos; su dificultad es desconocida. La paridad split/mono es por construcción (misma llamada), verificada textualmente para los 19.
- Validación: descubrimiento carga 19/19 en cada modelo sin errores; para cada número, split y mono hacen exactamente la misma llamada; `python -m scripts.check_repo` pasa. No se corrió ningún solve.

### Cambio 2026-09-23 - Tests de stress 09-11 con perfil realista (split corrido, mono pendiente)
> ⚠ Renumerados en la entrada anterior: 09 → 04, 10 → 05, 11 → 07.
- Autor: IA / equipo
- Alcance: tests de stress / escenarios
- Archivos principales:
  - [tests/shared_scenarios/stress/stress_scenarios_v5_designed.py](tests/shared_scenarios/stress/stress_scenarios_v5_designed.py): `realistic_crew_scenario(side)` y `speed_tiers` en `designed_stress_scenario`.
  - `tests/opp_v5_2_split/stress/test_case_09.py`, `_10.py`, `_11.py` y los mismos en `tests/opp_v5_1_mono/stress/`.
  - [experiments/opp_v5/stress_test_design.md](experiments/opp_v5/stress_test_design.md): análisis, calibración y resultados.
  - [experiments/opp_v5/exploration.py](experiments/opp_v5/exploration.py): herramienta de calibración con kill duro por proceso.
- Qué se hizo: tres tests de stress con un único eje variable (tamaño del depósito: 7×7, 13×13, 15×15) y perfil realista fijo — 6 lotes sobre 3 pickers, 156 órdenes, pesos 4/5, velocidades en dos bandas (0,8 y 1,2), sin clausura. Reemplazan la versión del 2026-09-22 de esos mismos números, que usaba todo uniforme. Split y mono llaman a la misma función, así que apuntan a instancias idénticas.
- Impacto: primeros tests de stress que ejercitan a la vez secuenciamiento real (`|B| > |P|`), velocidades diferenciadas y pesos no uniformes, sin ninguna de las seis degeneraciones documentadas.
- Riesgo / atención: los tiempos dependen de la instancia exacta; si se cambia el generador (seed, pesos, bandas) hay que recalibrar. En esta notebook los tiempos absolutos varían ~2x entre corridas.
- Validación:
  - Las tres instancias de los tests son **idénticas campo por campo** a las calibradas.
  - Corrida split (`results/opp_v5_2_split/stress/output_opp_v5_2_split_stress_tests_20260923_142920.csv`): **3/3 ok, 0 timeouts** — 7×7 **2,0 min**, 13×13 **5,9 min**, 15×15 **28,5 min**. Objetivos idénticos a la calibración en 7×7 y 13×13. SLA 67,9% en los tres.
  - `python -m scripts.check_repo`: pasa.
  - Mono: no corrido todavía.

### ⚠ Hallazgo 2026-09-23 - El `<= 1` SÍ cambia respuestas cuando un lote satura una grilla chica (acota la entrada siguiente)
- Qué pasó: en la frontera del estudio 08 (perfil realista, 26 órdenes por lote), el punto de 2 lotes / 1 picker en **4×4 dio infactible en los dos modelos**. Resuelto solo la Etapa 1 del split, el mismo punto es infactible con el `<= 1` y factible sin él (copia temporal del modelo, `relax_le1`; `models/` sin tocar).
- Por qué: el lote 2 tiene que pasar por 13 de las 14 ubicaciones pickeables, y el depot (V1) y el final (V16) están en esquinas opuestas. La grilla es bipartita y esas dos esquinas tienen el mismo color, así que un camino simple entre ellas no puede cubrir tantos vértices. Un picker real lo resuelve pasando dos veces por el mismo cruce; el `<= 1` lo prohíbe.
- Alcance: la conclusión de la entrada siguiente ("el `<= 1` no cambia las respuestas") vale para lotes que cubren una parte de la grilla, que es lo medido ahí (7×7 y 13×13 con 18–26 ubicaciones por lote). **En grillas chicas casi llenas vuelve infactible un caso físicamente posible.** Afecta igual a split y a mono (misma restricción), así que la equivalencia entre modelos se mantiene.
- Impacto en la herramienta: `--frontier` ya no cuenta un punto infactible en los dos modelos como falla del mono (antes podaba todos los tamaños desde ese punto).
- Pendiente de decisión del usuario: si el `<= 1` se mantiene como parte de la definición del problema, las instancias con lotes que saturan la grilla hay que evitarlas en los escenarios; si se quita, es un cambio de modelo en ambos.

### ⚠ Corrección 2026-09-23 - La entrada siguiente atribuye al `<= 1` más de lo que los datos sostienen
- Prueba directa (solo split, `models/` sin tocar: se reemplazó la copia temporal del `.zpl` de Etapa 1 por una sin `one_input_arc_per_node`/`one_output_arc_per_node`): los **11 funcionales que verifican la ruta exacta** (01–06, 08–11, 17) **pasan todos, con exactamente el mismo objetivo**, con y sin el `<= 1`. Sin él corren algo más rápido (0,10–0,17s contra 0,16–0,43s).
- **Lo que era falso**: se dijo que en el funcional `test_case_09` el `<= 1` inflaba la ruta 13x (26 contra 2). Da 1833 en las dos versiones. La ruta del pickeador, `L1 → L3 → L4 → L2 → L4`, pasa por **L4, que es el nodo final**, y `no_outflow_final` prohíbe salir del final. Ese es el bloqueo, no el `<= 1`.
- **Lo que queda en duda**: la "tasa de respaldo" de la clausura (67–100% de lotes con vértices repetidos) contó cualquier repetición como culpa del `<= 1`. Pero pasar por el depot o por el final, o recorrer el mismo arco dos veces en el mismo sentido (`z_ijb` es binaria), sigue prohibido sin él. Esa tasa es una cota superior del efecto del `<= 1`, no una medición de él.
- **Medido y cerrado** (Etapa 1 sola, grafo completo, 6 lotes, pesos 4/5; archivo `experiments/opp_v5/studies/07_le1_constraint/le1_stage1_*.csv`):

  | Grilla | Con `<= 1` | Sin `<= 1` | Tiempos de ruta |
  |---|---|---|---|
  | 7×7, 26 órd./lote | 11,6s | 7,8s | **idénticos** (64..75) |
  | 13×13, 26 órd./lote | 433s | 537s | **idénticos** (142..154) |

- **Conclusión: el `<= 1` no cambia las respuestas del modelo y no es una palanca de rendimiento.** Mismas rutas en los 11 funcionales de ruta y en las dos escalas de stress; la velocidad mejora en una escala y empeora en la otra. No hace falta ninguna decisión de alcance sobre él.
- **Por qué entonces la clausura repetía vértices en 67–100% de los lotes** (hipótesis, consistente con todo lo medido): en una grilla hay muchísimos caminos mínimos del mismo largo. Dijkstra elige uno cualquiera por tramo, y a veces dos tramos elegidos se cruzan; pero casi siempre existe otro camino igual de corto que no se cruza. Por eso el modelo con `<= 1` llega al mismo tiempo de ruta. **El respaldo de la clausura es evitable**: una expansión que eligiera caminos mínimos que no se crucen lo eliminaría. Es un arreglo técnico, no una decisión de modelado.
- Lo que limita la Etapa 1 en depósitos grandes sigue **sin identificar**.

### Hallazgo 2026-09-23 - En un depósito real la ruta óptima repite pasillos, y el `<= 1` lo prohíbe (VER CORRECCIÓN ANTERIOR)
- Datos crudos: [experiments/opp_v5/studies/06_metric_closure/closure_realistic_grids_20260923_130954.csv](experiments/opp_v5/studies/06_metric_closure/closure_realistic_grids_20260923_130954.csv) y el diagnóstico de tasa de respaldo ([experiments/opp_v5/studies/06_metric_closure/fallback_rate.py](experiments/opp_v5/studies/06_metric_closure/fallback_rate.py)).
- Pregunta: ¿la clausura métrica sirve en proporciones de depósito real (layout grande, listas cortas)? La regla de los arcos (ayuda cuando las ubicaciones por lote son menos que ~2× el lado de la grilla) predecía que sí.
- Resultado directo: con 6 lotes, **ninguna** de estas configuraciones terminó la Etapa 1 en 15 minutos, **ni con ni sin clausura**: 25×25 con 12 y 20 órdenes/lote, 35×35 con 12. (Medido con 6 procesos en paralelo, ver nota sobre la CPU híbrida más abajo.)
- Diagnóstico — cuántos lotes caen en el respaldo al grafo completo:

  | Grilla | Órdenes/lote | Respaldo | Solve sobre la clausura | Vértices repetidos por ruta |
  |---|---|---|---|---|
  | 25×25 | 12 | **4 de 6** | 0,16–0,22s | 2, 5, 2, 5 |
  | 13×13 | 26 | **6 de 6** | 0,62–30,9s | 2, 7, 1, 1, 4, 3 |
  | 7×7 | 26 | **5 de 6** | 0,25–3,03s | 2, 1, 3, 1, 1 |

- **La clausura hace lo que prometía** (0,2s por lote en un depósito de 625 ubicaciones), pero **en 67–100% de los lotes la ruta óptima pisa algún vértice más de una vez**. `one_input_arc_per_node`/`one_output_arc_per_node` (`<= 1`) lo prohíben, así que el lote se re-resuelve con el grafo completo y ahí se va todo el tiempo. La regla de los arcos no alcanza: lo que decide si la clausura sirve es la tasa de respaldo.
- **Lo que revela, más allá de la clausura**: en una grilla de depósito la ruta óptima recorre naturalmente el mismo pasillo dos veces — entra y sale por donde vino —, exactamente como lo haría un pickeador. El `<= 1` exige un camino simple. En consecuencia:
  1. Es **físicamente irreal**.
  2. **Infla los tiempos de ruta**: en `test_case_09` funcional el modelo pagaba 26 contra 2 de la ruta real (13x).
  3. Es **la razón por la que la Etapa 1 no escala** a depósitos realistas: sin él, la clausura sería exacta siempre y la Etapa 1 del depósito 25×25 con 6 lotes tardaría del orden de 1 segundo en vez de no terminar en 15 minutos.
- **Decisión pendiente del usuario, no aplicada.** Relajar el `<= 1` cambia la definición del problema en **ambos** modelos y en la línea base, así que es una decisión de alcance de tesis. Aplicado a los dos, la equivalencia entre mono y split se mantiene. Es la pregunta que quedó abierta el 2026-09-22 ("opción 2"), ahora con evidencia cuantitativa.

### Hallazgo operativo 2026-09-23 - La CPU es híbrida: los tiempos en paralelo no sirven como absolutos
- Máquina: Intel i7-1360P de notebook. **4 núcleos de rendimiento con hyperthreading + 8 de eficiencia** (~mitad de velocidad), 16 procesadores lógicos, y baja la frecuencia con todos los núcleos cargados.
- Evidencia: la Etapa 1 de 6 lotes / 26 órdenes / 15×15 tardó 464s con pocos procesos y **no terminó en 1500s** con 16 procesos en paralelo. A1 y A1nc (mismo escenario, con y sin clausura, corriendo juntos) dieron 314.331 nodos exactos en ambos, pero la Etapa 2 tardó 452s y 490s: ~8% de ruido entre dos corridas simultáneas.
- Regla: en paralelo, **solo comparaciones relativas lado a lado y conteos de nodos**. Cualquier objetivo de tiempo absoluto ("este test resuelve en 10-20 min") se calibra **de a una medición por vez**, porque el runner corre los tests en serie.

### Hallazgo operativo 2026-09-23 - `limits/time` de SCIP NO es un tope duro
- El caso de 6 pickers con 3 niveles tenía `limits/time = 300` y terminó a los **3079,24s**, diez veces más, con apenas 499 nodos (~6s por nodo). SCIP solo chequea el límite entre operaciones; un LP enorme en un nodo puede pasarse de largo sin enterarse. El mismo patrón de "atascado en la raíz" ya se había visto con muchos pickers (10 lotes / 16 pickers: 20 nodos en 119s).
- Además el proceso siguiente quedó colgado ~10 horas con 3,7% de uso de CPU, probablemente por suspensión de la máquina.
- Implicancias:
  - En experimentos, **no confiar en `limits/time` para acotar la duración**. Hay que envolver cada solve en un proceso aparte y matarlo desde afuera, como ya hace `TestRunner` con `p.terminate()` + `_kill_process_tree`.
  - Los tests de la suite **sí** están protegidos, porque el timeout lo aplica el runner matando el árbol de procesos, no SCIP.
  - `experiments/opp_v5/exploration.py` resuelve la Etapa 2 dentro del mismo proceso, así que hereda este problema — y la Etapa 1 ni siquiera tiene límite.

### Degeneraciones detectadas en los escenarios de stress (2026-09-22/23)

**Resumen, ordenado por lo que cuesta cada una:**

| # | Degeneración | Efecto medido | Tipo |
|---|---|---|---|
| 6 | Pesos uniformes de la grilla (`v_weight = h_weight = 4`) | Etapa 1 hasta **3,7x más lenta** (46,5s → 12,6s al romper los empates) | rendimiento |
| 3 | Fechas de entrega degeneradas (`Dd = 30` para todas) | Etapa 2 hasta **8x más lenta**, **37x más nodos** (153.934 → 4.144) | rendimiento |
| 2 | `\|B\| = \|P\|` en 5 de 8 escenarios | el secuenciamiento nunca se activa; la Etapa 2 degenera en asignación | cobertura |
| 1 | `\|P\| > \|B\|` (test_case_07) | pickers que por construcción no pueden hacer nada | cobertura |
| 5 | Lotes vacíos (funcional 30: 10 de 12) | permutaciones indistinguibles entre sí | cobertura |
| 4 | `V_p` uniforme en todos los escenarios | la característica que distingue v5 de v4 queda sin ejercitar | cobertura |

Las dos primeras son de rendimiento puro y están medidas. Las otras cuatro son de cobertura: no encarecen necesariamente la resolución, pero dejan partes del modelo sin validar. La 4 estaba clasificada como de rendimiento hasta la corrección del 2026-09-23.

**Detalle de cada una.** Todas inflan la dificultad o reducen la cobertura sin representar nada de un depósito real. A tener en cuenta al diseñar escenarios nuevos:
1. **`|P| > |B|`** (`test_case_07`: 10 lotes, 25 pickers). Cada lote va a exactamente un picker, así que como mucho se usan `|B|`; los 15 restantes son costo combinatorio puro. Verificado: 10/10 y 10/12 dan el MISMO objetivo (29034).
2. **`|B| = |P|` en 5 de los 8 escenarios** (01, 02, 03, 04, 05). Cada lote toma su propio picker, ninguna restricción de no-solapamiento se activa y la Etapa 2 degenera en un problema de asignación. **El secuenciamiento —la razón de ser de la Etapa 2— solo se ejercita en el 06 (25/10) y el 08 (40/1).**
3. **Fechas de entrega imposibles**: `migrated_stress_scenario` fija `Dd = 30` para todas las órdenes, pero el tiempo fijo por lote ya es 101 y la ruta suma 64–72. Resultado: `sla_on_time_pct = 0.0`, las 100 órdenes llegan tarde, el término de adelanto es siempre cero y la estructura earliness/tardiness no se ejercita.
4. **Todas las velocidades en 1.0**, o sea que ningún escenario de stress ejercita `V_p` heterogéneo, que es lo que distingue v5 de v4. Medido aparte: con velocidades distintas el mismo escenario pasa de 33s a más de 600s, o sea que el caso que v5 vino a modelar es MÁS duro, no menos.
5. **Lotes vacíos**: el funcional `test_case_30` (vía `multigrid_5x5_3x3_five_pickers_twelve_batches`) define 12 lotes y solo carga órdenes en 2. Los 10 vacíos son idénticos entre sí (mismo `tiempo_fijo`, misma ruta depot→final), o sea 10! permutaciones indistinguibles. Da timeout a los 5 minutos **con 4 órdenes y 34 nodos** — la prueba más clara de que la dificultad de la Etapa 2 la gobierna la relación lotes/pickers y no el tamaño.

### Cambio 2026-09-24 - Corridas funcionales de opp_v5 y comparación mono vs split regenerada
- Alcance: resultados / documentación
- Archivos principales:
  - [results/opp_v5_2_split/functional/](results/opp_v5_2_split/functional/), [results/opp_v5_1_mono/functional/](results/opp_v5_1_mono/functional/)
  - [experiments/opp_v5/reports/build_functional_comparison.py](experiments/opp_v5/reports/build_functional_comparison.py), [functional_comparison_template.tex](experiments/opp_v5/reports/functional_comparison_template.tex)
  - [docs/thesis/opp_v5_1_mono_vs_opp_v5_2_split_comparison.tex](docs/thesis/opp_v5_1_mono_vs_opp_v5_2_split_comparison.tex)
- Qué se hizo:
  - Se corrieron las suites funcionales completas (incluidos los tests 35–38). Split: 63 tests, 62 ok y 1 timeout. Mono: 62 tests, 60 ok, 1 falla conocida (test_case_06) y 1 timeout.
  - El test_case_30 de los dos modelos se corrió aparte, en paralelo con la suite de mono, y sus filas se agregaron al CSV de cada modelo. La variante factible da timeout (25 min) en los dos; la infactible pasa. Los tiempos de mono pueden estar algo inflados por esa concurrencia.
  - La comparación mono vs split ahora sale de un generador, como los documentos de exploración (el `.tex` de docs/thesis no se edita a mano). Figuras en MetaPost en vez de los PDF externos.
- Resultado: 48 pares factibles con el mismo objetivo (diferencia máxima 3,83e-6, casos 13 y 14). En la suma de todos los tests, mono tarda 8,5× lo que split; en la mediana, mono es más rápido (0,342 s contra 0,408 s) y gana en 18 de los 48 pares, todos chicos; en las grillas llega a tardar 36,5× lo que split.
- Validación: el generador corre sin errores; el documento compila con `context` (0 errores) y se revisaron las páginas renderizadas.

### Cambio 2026-09-24 - Suite de stress de opp_v5 cerrada, CSV con nombre fijo y documentos finales
- Alcance: resultados / documentación / análisis
- Archivos principales:
  - `results/opp_v5_2_split/stress/output_opp_v5_2_split_stress_tests_parallel.csv`, `results/opp_v5_1_mono/stress/output_opp_v5_1_mono_stress_tests.csv`, `results/opp_v5_{2_split,1_mono}/functional/output_opp_v5_*_functional_tests.csv`
  - [experiments/opp_v5/reports/stress_suite.py](experiments/opp_v5/reports/stress_suite.py) (nuevo), los generadores de exploración y de comparación
  - [analysis/config.py](analysis/config.py) (`LATEST_FILE_OVERRIDES`)
- Qué se hizo:
  - Nightly: el job `exact-zimpl` corre también la suite funcional de `opp_v5_1_mono` (el timeout del test 30 no hace fallar la suite y el 06 es `known_failure`). Comentarios de `nightly.yml`/`ci.yml` y `scripts/README.md` actualizados. Falta ver cuánto tarda en el runner.
  - Stress 02 del split vuelto a correr con 6 procesos: 54,6 s (antes 98,9 s en secuencia, corrida del 22-09), mismo objetivo (29.034); su fila reemplaza la vieja.
  - Stress 16–19 del split (Etapa 1 con 6 procesos): los cuatro dan timeout a 40 min. El CSV del split tiene los 19 tests: 9 resueltos (02, 04–07, 09–11, 15) y 10 timeouts.
  - Stress del mono: medidos 01 (sin resultado), 02 (timeout: la corrida se canceló pasados los 40 min sin terminar; la fila se cargó a mano) y 03–07 (timeout). 08–19 figuran como timeout: el test más chico de la suite (04) ya no cierra en 40 min y el resto lo domina en tamaño (estudios 08 y 11). La corrida de 08–19 se lanzó el 24-09 a la noche y el usuario la cortó por el tiempo que llevaba: ningún test terminó. No dejó CSV; las filas del CSV fijo se mantienen. Tema cerrado. Las etiquetas de timeout de los dos CSV de stress quedaron unificadas en "- 40".
  - Los CSV de opp_v5 pasan a nombre fijo, sin fecha: son la versión que cuenta. `_parallel` marca la corrida de stress del split con la Etapa 1 en paralelo. `LATEST_FILE_OVERRIDES` los fija para que el análisis no elija una corrida nueva que se escriba al lado.
  - La exploración del mono cierra la sección de predicción con la tabla de la suite (0 de 19 contra 9 del split) y pierde la sección de pendientes. La comparación mono vs split suma una sección de stress con la misma tabla.
  - Nombres de test duplicados: en `tests/opp_v4/functional/test_case_23.py` y `test_case_24.py`, `test_grid_multi_location_orders` y `test_bridge_disconnected_required_location` pasan a `..._with_capacities` (cuerpo idéntico al de 20/21; solo registran también las capacidades). Los opp_v5 que los heredan (25/26) toman el nombre nuevo y se renombraron sus filas en los CSV funcionales. El análisis ya no reporta esas colisiones.
- Riesgo / atención: la notebook entró en suspensión durante las corridas de stress del 23-09 y del 24-09. Los timeouts valen (el tope cuenta solo tiempo despierto), pero la duración de los tests resueltos incluye el tiempo suspendido: los tiempos del split son un techo. Los documentos lo dicen.
- Validación: los tres generadores corren; los tres documentos compilan con `context` (0 errores) y se revisaron las páginas nuevas.

### Cambio 2026-09-28 - Verificador de soluciones heurísticas contra opp_v5_1_mono
- Alcance: infraestructura de tests / verificación / resultados
- Archivos principales:
  - [verification/](verification/) (nuevo): `solution_store.py`, `mono_compliance.py`, `run_compliance.py`
  - [dtos/opp/solution_record_dto.py](dtos/opp/solution_record_dto.py), [dtos/verification/compliance_report_dto.py](dtos/verification/compliance_report_dto.py) (nuevos); [dtos/opp/solve_result.py](dtos/opp/solve_result.py)
  - [models/opp_hc_4/opp_hc_4.py](models/opp_hc_4/opp_hc_4.py), [models/opp_aco_4/opp_aco_4.py](models/opp_aco_4/opp_aco_4.py): adjuntan un `SolutionRecordDTO` al `SolveResult` (solo referencias, no cambia la búsqueda ni los tiempos)
  - [tests/infra/execution/runner.py](tests/infra/execution/runner.py), [config.py](tests/infra/execution/config.py), [tests/run_suite.py](tests/run_suite.py), `.env.example`: variable `WRITE_SOLUTIONS`
  - Resultados: `results/opp_{hc,aco}_4/functional/output_*_20260928_{202021,205341}.csv`, sus carpetas `solutions/<corrida>/` y `results/compliance/opp_{hc,aco}_4/functional/`
- Qué se hizo:
  - Con `WRITE_SOLUTIONS=1`, el runner guarda cada solución de HC-4/ACO-4 (instancia + solución) como un JSON en `results/<modelo>/<tier>/solutions/<corrida>/`, enlazado desde la columna `solution_file` del CSV. Se serializa después de medir `total_time`. Cada corrida conserva sus JSON, igual que su CSV.
  - `python -m verification.run_compliance --model <m> --tier <t>` lee esos JSON (no vuelve a correr tests) y verifica cada solución contra mono en tres capas: chequeos en Python (arcos en E, sin revisitas, locaciones requeridas, un picker por lote, cadena de frío, tiempos y objetivo recalculados, validez de big-M); nivel 1 en SCIP (rutas, asignación y secuencia fijas, tiempos libres); nivel 2 (también los tiempos de completitud fijos, exactos). Las variables se fijan por nombre sobre el LP compilado: no se copia ni edita ninguna restricción del `.zpl`. Escribe una fila por test apenas la verifica; `--resume` saltea las filas que ya tienen veredicto y `--test` reemplaza solo las filas que vuelve a revisar.
  - Lotes vacíos (decisión de la usuaria): mono obliga a rutear, asignar y cobrar en el objetivo todo lote de `B` aunque no tenga órdenes, y las heurísticas los ignoran. El verificador saca de `B` los lotes sin órdenes que la solución no usa (queda en `notes`); ninguna restricción cambia.
- Resultado: funcionales de HC-4 y ACO-4, 63 tests cada uno: 51 `compliant`, 0 `violations`, 12 `skipped` (los que esperan infactibilidad, no hay solución que verificar).
  - 2026-09-29: esas dos corridas funcionales (CSV, JSON y reportes de compliance) se borraron porque el PR #17 cambió la suite funcional de HC-4 y ACO-4: sumó los 67 tests `test_v5eq__*` (los datos exactos de v5) y dejó los 63 anteriores como no comparables con v5 (corren con un picker, v5 con dos). Hay que volver a correrlas con `WRITE_SOLUTIONS=1` y verificarlas. El resultado de arriba queda como registro de lo que dieron.
- Stress (misma fecha):
  - HC-4, suite completa (32 tests, todos `ok`; `output_opp_hc_4_stress_tests_20260928_210210.csv` + soluciones). Verificados 31: 29 `compliant`, 2 `skipped`, 0 `violations`; incluye 10 de las 11 instancias donde split y mono dan timeout. Sin espera voluntaria en stress (`W_full` = 27). Falta el 100x100: compilar mono para esa instancia llevó a ZIMPL a ~5 GB sin terminar; queda para el final.
  - 2026-09-29, 100x100: el verificador corre los niveles de SCIP sobre el subgrafo de las rutas fijas (E = unión de sus arcos, V = sus nodos + depot y final), exactamente equivalente con las rutas fijas; solo se aplica si todos los lotes quedaron fijos y sin problemas de ruta, y queda en `notes`. `A_ni` se mantiene disperso hasta compilar. Validación: las 248 soluciones ya verificadas dan idéntico veredicto, estados y objetivos, con y sin recorte, que los reportes commiteados. Con eso el 100x100 de HC-4 da `compliant` (862.656, 218 s; 1.425 de 10.000 nodos, 2.900 de 39.600 arcos): HC-4 queda con los 19 stress v5 verificados.
  - 2026-09-29, 100x100 de ACO-4 (`output_opp_aco_4_stress_tests_20260929_120151.csv` + solución): `compliant` (988.252; 1.499 nodos, 3.160 arcos; 318 s). La notebook se suspendió 4 min (12:11–12:15) durante la corrida y `Max_time` de ACO cuenta tiempo de reloj, así que el objetivo quedó 6,9 % arriba de la referencia del 28-09 (924.536): vale como prueba de factibilidad, no como resultado de calidad o tiempo. Una corrida previa con ~33 min de suspensión (objetivo 1.051.288) se descartó y no se commiteó. Con esto las dos heurísticas tienen los 19 stress v5 verificados.
  - 2026-09-29, unificación (como en opp_v5): un CSV por modelo y tier con nombre fijo, `results/opp_{hc,aco}_4/{functional,stress}/output_opp_{hc,aco}_4_{tier}_tests.csv`, y su reporte en `results/compliance/opp_{hc,aco}_4/{tier}/compliance_output_…_tests.csv`. Cada fila sale de una corrida con soluciones guardadas, así que enlaza a su JSON y a su fila de compliance (verificado: 0 diferencias). ACO-4 stress combina tres corridas (8 + 10 + 100x100). Las corridas viejas sin JSON eran apenas mejores en algunos stress (0,001–0,11 %), salvo el 100x100 de ACO-4 (924.536 contra 988.252). Se borraron los 21 CSV con fecha de HC-4/ACO-4 (incluidos los del #17) y los 6 reportes por corrida; `analysis/config.py` fija los 4 CSV unificados. Registro de comparabilidad regenerado: la clasificación no cambió, `results_v5_vs_heuristics.csv` toma los resultados unificados.
  - 2026-09-29, tras mergear el PR #19 (borrado de los stress legacy y renumeración de los v5 a `test_case_NN`): los CSV de stress de HC-4 y ACO-4 de esta rama, sus JSON y el reporte de compliance de HC-4 se alinearon con esa convención. Se sacaron las 13 filas legacy de HC-4 (y sus 11 JSON) y las filas v5 tomaron el número nuevo, con el mismo mapeo del PR. Solo cambiaron las columnas `test`/`solution_file` y el campo `test` de cada JSON. Quedan 19 filas en HC-4 (18 `compliant`, falta el 100x100) y 8 en ACO-4.
  - ACO-4, solo los 18 tests `v5_*` sin el 100x100: la corrida se cortó a pedido con 8 terminados (todos `ok`, con solución guardada; `output_opp_aco_4_stress_tests_20260928_225205.csv`). Faltan `8_orders_7x7_320`, `overstaffed` y los 8 `realistic_crew`, y verificar lo corrido.
  - Los 22 stress legacy de ACO-4 (01–20, `cold_chain`, `picker_speed`) quedan fuera por ahora. Son las mismas instancias que la corrida del 2026-09-11 (cuerpos, escenarios y `graphs_factory` idénticos); cambió el código del modelo.
  - Los JSON se nombran `<módulo>.<método>.json` (sin la clase): el id completo superaba el límite de 260 caracteres de ruta de Windows y git no lo indexaba. El id completo queda dentro del JSON.
- Hallazgos:
  - En 7 de los 51 casos (los mismos en los dos modelos) el nivel 1 baja el objetivo entre 7,9 % y 93,6 % con las mismas rutas, asignación y secuencia: mono espera para no terminar antes del due date y las heurísticas nunca esperan (la espera voluntaria de v5). No es una violación.
  - `test_fractional_and_zero_capacities_feasible` (timeout en split y mono) tiene 10 de 12 lotes vacíos: sin ellos se verifica en 0,13 s; con ellos libres SCIP no cerraba en 600 s. Probable causa del timeout de los modelos lineales.
- Riesgo / atención: los CSV funcionales nuevos de HC-4/ACO-4 pasan a ser los más recientes, así que el análisis los toma (sin override); traen la columna extra `solution_file`. El 2026-09-28 se perdió el primer reporte de compliance de HC-4 funcional al volver a correr el verificador con `--test` (bug ya corregido); se regeneró completo desde los JSON.
- Validación: prueba de mutaciones sobre una solución chica (arco inexistente, completitud solapada, cadena de frío, objetivo mal reportado): las cuatro se detectan. Reportes de compliance completos de los dos funcionales, 63 filas cada uno sin duplicados.


### Cambio 2026-09-29 - Funcionales de opp_v5 (split y mono) corridos de nuevo
- Alcance: resultados
- Archivos: `results/opp_v5_2_split/functional/output_opp_v5_2_split_functional_tests.csv`, `results/opp_v5_1_mono/functional/output_opp_v5_1_mono_functional_tests.csv`
- Qué se hizo: se volvieron a correr las suites funcionales con el código actual (el PR #16 cambió `stage1_decomposition.py`, `zpl_utils.py` y los escenarios de stress después de las corridas del 24-09), salteando `test_fractional_and_zero_capacities_feasible`, que da timeout (25 min) en los dos modelos. Split en secuencia (`OPP_STAGE1_WORKERS=1`): con 6 procesos tardaba más (51 s contra 46 s) porque en instancias chicas levantar los procesos cuesta más de lo que ahorra. Cada CSV de nombre fijo queda con las filas nuevas más la fila del timeout de la corrida anterior.
- Resultado: split 62/62 `ok`; mono 60 `ok` y la falla conocida del 06. Ningún test cambió de status ni de objetivo respecto de las corridas del 24-09; solo cambian los tiempos.
- Validación: comparación fila por fila contra los CSV anteriores; el análisis carga los dos CSV (63 y 62 filas).

### Cambio 2026-09-29 - Stress de opp_v5_2_split corrido de nuevo y unificado
- Alcance: resultados / análisis
- Archivos: `results/opp_v5_2_split/stress/output_opp_v5_2_split_stress_tests_parallel.csv`, [analysis/config.py](analysis/config.py)
- Qué se hizo: se volvieron a correr los 9 stress que resuelven (02, 04–07, 09–11, 15) con el código actual y la Etapa 1 en 6 procesos; los 10 que dan timeout a 40 min no se corrieron. Todo queda en un solo CSV (el `_parallel`, que es el que leen los generadores de `experiments/opp_v5/reports/`): los 9 nuevos, 01 y 03 de la corrida del 24-09 y 08, 12–19 de la del 26-09 (`W_full` = 27). Se borró `…_20260926_225549.csv`; `analysis/config.py` apunta al archivo único.
- Resultado: los 9 objetivos son idénticos a los anteriores. Los tiempos bajan a cerca de la mitad (15×15: 1.949 s → 888 s), salvo `scheduling_heavy` (86 s → 365 s), probablemente inflado por suspensiones de la notebook durante la corrida (14:26, 14:31–14:36, 14:41).
- Riesgo / atención: los reportes y documentos generados desde ese CSV se armaron con su contenido anterior (04–19 con `W_full` = 9); si se regeneran, cambian.
- Validación: el análisis carga 19 filas (9 `ok`, 10 `timeout`); `check_repo` pasa.

### Cambio 2026-09-29 - Reportes de opp_v5 regenerados con las corridas nuevas
- Alcance: documentación
- Archivos: [experiments/opp_v5/reports/split_exploration_template.tex](experiments/opp_v5/reports/split_exploration_template.tex), [functional_comparison_template.tex](experiments/opp_v5/reports/functional_comparison_template.tex); los tres `.tex`/`.pdf` de `docs/thesis/` (exploración de split, exploración de mono, comparación mono vs split)
- Qué se hizo: se regeneraron los tres reportes con los CSV nuevos. En la exploración de split, la sección de validación (tabla de tiempos por etapa escrita a mano) describía la corrida del 23-09 con `W_full` = 9: ahora describe la del 29-09 (`W_full` = 27) y deja dicho el contraste (Etapa 2 de 86–203 s a menos de 10 s, SLA de 68 % a 100 %); se ajustaron los tres puntos de esa sección (8×21 ahora tarda más que 14×14 en la Etapa 1) y cuatro frases de la síntesis y las limitaciones (15×15 ≈ 15 min, SLA según `W_full`, la confusión objetivo plano / $N_b$ en parte resuelta, franja de 10–20 min cubierta). En la comparación, la introducción describe las corridas funcionales del 29-09. La exploración de mono no tenía texto fijo desactualizado.
- Validación: los tres compilan con `context` (0 errores); se revisó la página de la sección de validación renderizada.

### Cambio 2026-09-29 - Soluciones de opp_v5 (split y mono) guardadas
- Alcance: infraestructura de tests / resultados
- Archivos: [dtos/opp/zimpl_solution_record_dto.py](dtos/opp/zimpl_solution_record_dto.py) (nuevo), [tests/infra/zimpl/dat_files_builder.py](tests/infra/zimpl/dat_files_builder.py), [zpl_utils.py](tests/infra/zimpl/zpl_utils.py), [tests/opp_v5_2_split/opp_test_case_v5_2_split.py](tests/opp_v5_2_split/opp_test_case_v5_2_split.py), [tests/infra/factories/migrated_case.py](tests/infra/factories/migrated_case.py), [verification/solution_store.py](verification/solution_store.py); los CSV fijos de split (funcional y stress) y de mono (funcional) y sus carpetas `solutions/`
- Qué se hizo: `WRITE_SOLUTIONS` ahora también guarda las soluciones de los modelos exactos. `build_dat_files` guarda una referencia al escenario y `solve_zpl` adjunta un `ZimplSolutionRecordDTO` (escenario + valores de SCIP + estado) a su `SolveResult`; en split, los dos flujos que encadenan las etapas le agregan los valores de la Etapa 1 (las rutas) después de la Etapa 2. El JSON (kind `zimpl`) guarda la instancia tal como se escribieron los `.dat` y las variables distintas de cero. No se tocó ninguna aserción, modelo ni `.zpl`.
- Se volvieron a correr, salteando los timeouts: funcionales de split (en secuencia) y mono, y los 9 stress de split que resuelven (Etapa 1 en 6 procesos). Cada CSV fijo queda con las filas nuevas (con `solution_file`) más las filas de timeout anteriores.
- Resultado: split funcional 62/62 `ok` (57 soluciones), mono 60 `ok` + la falla conocida del 06 (53), split stress 9/9 (9). Ningún test cambió de estado ni de objetivo; 119 JSON, ningún enlace roto.
- Validación: prueba con 3 tests por modelo y con el stress 04 de split en 6 procesos (rutas de los 6 lotes + cronograma); el análisis carga los CSV; `check_repo` pasa.

### Cambio 2026-09-29 - Comparación split contra mono y registro de infactibles de split
- Alcance: verificación / tests / resultados
- Archivos: [verification/compare_v5.py](verification/compare_v5.py) (nuevo), `results/comparability/compare_v5_split_vs_mono.csv`, [tests/opp_v5_2_split/opp_test_case_v5_2_split.py](tests/opp_v5_2_split/opp_test_case_v5_2_split.py), el CSV funcional fijo de split
- Qué se hizo: `python -m verification.compare_v5` compara split con mono desde los CSV fijos y los JSON guardados (no resuelve nada): estado, objetivo (tolerancia relativa 1e-6) y, si coinciden, rutas, asignación y orden por picker; agrupa migrados de v4 / propios de v5 / stress. `--verify-split-stress` (a pedido) verifica además cada solución de stress de split contra mono con el verificador. Termina con error solo si algún objetivo difiere.
- Resultado: ningún desacuerdo. Funcionales migrados: 15 misma solución, 20 óptimos alternativos (mismo objetivo), 8 infactibles en los dos, 1 timeout en los dos, y el 06 (falla conocida de mono, mismo objetivo). Propios: 12 misma solución, 4 infactibles en los dos, 1 solo de split. Stress: mono no resuelve ninguno; con `--verify-split-stress` las 9 soluciones de split dan `compliant`.
- Corrección: cuando ningún picker es elegible por la cadena de frío, `run_pipeline` de split cortaba antes de la Etapa 2 sin registrar nada, y el CSV mostraba como objetivo el tiempo de ruta de la Etapa 1 (14). Ahora registra un resultado `infeasible` sin objetivo, como `solve_zpl` y las heurísticas al rechazar una entrada. Se volvieron a correr `test_case_24`, `34` y `35` de split: 2 filas pasan de 14 a vacío (las demás, mismo objetivo) y se borraron los 8 JSON viejos que quedaron sin referencia. `test_preflight_detects_when_no_picker_is_eligible` conserva su 14: ese test corre solo la Etapa 1 a propósito.

### Cambio 2026-09-29 - Stress de mono unificado en un solo CSV
- Alcance: resultados / análisis
- Archivos: `results/opp_v5_1_mono/stress/output_opp_v5_1_mono_stress_tests.csv`, [analysis/config.py](analysis/config.py)
- Qué se hizo: la fila del test 04 de la corrida del 27-09 (`W_full` = 27) reemplaza a la vieja en el CSV fijo y se borró `…_20260927_124455.csv`. Las filas 01–03 y 05–19 quedan sin tocar (05–19 como registro de `W_full` = 9, nunca corridas con 27). El override lee del archivo único solo 01–04, así que el análisis ve lo mismo que antes (01 sin resultado, 02–04 timeout).
- Validación: solo cambió la fila del 04 respecto del archivo commiteado; el análisis carga las mismas 4 filas; `check_repo` pasa. Con esto los cuatro modelos actuales tienen un solo CSV por tier en funcional y stress.
---


## 4. Formato recomendado para cada cambio

### Cambio [YYYY-MM-DD] - [Título breve]
- Autor: [nombre]
- Alcance: [modelo / tests / docs / infraestructura]
- Archivos principales: [ruta1, ruta2, ...]
- Qué se hizo:
  - [Resumen claro en 2-4 bullets]
- Impacto:
  - [Qué cambia para el proyecto]
- Riesgo / atención:
  - [Punto crítico, dependencia, posible regresión]
- Validación:
  - [comandos ejecutados / pruebas / evidencia]

### Ejemplo de entrada real

#### Cambio 2026-08-18 09:00 - Estructura inicial de meta summary
- Autor: IA / equipo
- Alcance: documentación / colaboración
- Archivos principales: [meta.md]
- Qué se hizo:
  - Se agregó un resumen operativo para que la IA registre cambios y el contexto del repo.
  - Se define una estructura reutilizable para cambios, impacto y validación.
- Impacto:
  - Reduce la necesidad de leer todo el repositorio para entender el estado actual.
- Riesgo / atención:
  - Requiere mantener este archivo actualizado para que siga siendo útil.
- Validación:
  - Se verificó la existencia del archivo y su estructura inicial.

## 5. Archivos clave del repositorio

### Documentación principal
- [README.md](README.md)
- [conventions.md](conventions.md)
- [meta.md](meta.md)

### Estructura de modelos
- [models/](models/)
- [dtos/](dtos/)
- [observer/](observer/)
- [utils/](utils/)

### Testing
- [tests/](tests/)

### Modelos vigentes para la tesina
- Exactos: [models/opp_v4/](models/opp_v4/), [models/opp_v5_1_mono/](models/opp_v5_1_mono/), [models/opp_v5_2_split/](models/opp_v5_2_split/)
- Hill Climbing: [models/opp_hc_2/](models/opp_hc_2/), [models/opp_hc_3/](models/opp_hc_3/), [models/opp_hc_4/](models/opp_hc_4/)
- ACO: [models/opp_aco_2/](models/opp_aco_2/), [models/opp_aco_3/](models/opp_aco_3/), [models/opp_aco_4/](models/opp_aco_4/)
- Legacy (fuera de la tesina, se conservan): `opp_v1`, `opp_v2`, `opp_v3`, `opp_hc_1`, `opp_aco_1`

### Documentación y ejemplos
- [docs/](docs/) — índice en [docs/README.md](docs/README.md): `thesis/`, `guides/`, `specs/`, `tests/<modelo>/`
- [examples/](examples/) — scripts de uso de los modelos heurísticos

### Datos y resultados
- [tests/shared_scenarios/](tests/shared_scenarios/) — todos los escenarios de prueba
- [results/](results/) — CSV de resultados por modelo y tier
- [analysis/](analysis/) — pipeline de comparación (lee `results/`)

### Notas

- La estructura exacta puede variar por modelo.
- Para cambios funcionales, revisar primero la carpeta del modelo afectado y sus tests.

---

## 6. Dependencias y entorno

### Requisitos
- Python
- PySCIPOpt
- Entorno virtual recomendado

### Comandos frecuentes

```bash
# Activar entorno
source .venv/bin/activate
# o en Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar tests
python -m unittest discover -s tests
```

### Observaciones del entorno
- [ej. se usa entorno local `.venv`]
- [ej. hay modelos con imports específicos por nivel de carpeta]
- [ej. ciertos tests esperan ejecutarse desde la raíz del proyecto]

---

## 7. Riesgos, deuda y pendientes

### Riesgos conocidos
- `opp_v5_2_split` en estrés: 0/8, con un fallo por nombres de variables truncados/corruptos en el `.lp` que genera ZIMPL para instancias grandes (ver `analysis/README.md`).
- Las heurísticas HC no tienen retroceso en la construcción de rutas y no resuelven instancias con ~25 ubicaciones requeridas por lote, aunque SCIP las resuelva en segundos (limitación documentada en `docs/thesis/results_outline.md`).
- La comparación heurístico vs. exacto sólo es válida si la instancia es la misma: se une por nombre de método y forma de la instancia, no por número de archivo.

### Pendientes
- [ ] Verificación a fondo de todas las suites tras la reorganización
- [ ] Estructura definitiva de `results/` (archivar corridas superadas)
- [ ] Regenerar `analysis/output/`
- [ ] Separar en un repo aparte lo que entra en la tesina

---

## 8. Criterios para actualizar este archivo

Cuando se haga un cambio, la IA o el desarrollador debe actualizar esta página con el siguiente mínimo:

1. Fecha del cambio.
2. Título breve.
3. Archivos afectados.
4. Qué se modificó.
5. Impacto funcional o técnico.
6. Riesgos / dependencias relevantes.
7. Evidencia de validación.

### Regla importante

No se debe escribir un resumen genérico como “se arregló el código”. Debe dejarse información accionable:

- qué cambió,
- en qué archivos,
- por qué importa,
- y cómo se validó.

---

## 9. Instrucción directa para la IA

La IA encargada de modificar este repositorio debe seguir esta secuencia:

1. Leer este archivo antes de empezar.
2. Identificar si el cambio afecta arquitectura, modelos, tests o documentación.
3. Actualizar la sección de cambios recientes con un bloque nuevo.
4. Actualizar el resumen ejecutivo si hubo un cambio de estado.
5. Revisar y ajustar riesgos / pendientes si corresponde.
6. Dejar evidencia de validación en el bloque del cambio.
7. Si cambió la lógica del modelo, verificar si también hay impacto en tests comparativos.

> En pocas palabras: este archivo es el “resumen ejecutivo compartido” del repo. Debe mantenerse vivo y útil para todos los que entren después.
