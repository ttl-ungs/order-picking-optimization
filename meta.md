# Meta del Repositorio

Este archivo funciona como resumen operativo del proyecto para trabajo compartido. Su objetivo es que una IA o un desarrollador pueda entender el estado actual del repositorio sin tener que leer todo el código ni la documentación completa.

> Regla de mantenimiento: cada cambio importante debe dejarse registrado en esta página. No se borra el historial anterior; se agrega un nuevo bloque al inicio o al final y se actualiza el estado general.

---

## 1. Resumen ejecutivo

- Proyecto: Linear Picking Routing
- Tipo: Optimización / routing de picking en almacén
- Stack principal: Python, PySCIPOpt, modelos exactos y heurísticos
- Estado actual: En desarrollo (limpieza y reorganización de repo en curso)
- Última actualización: 2026-09-17
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
- [x] Riesgos conocidos documentados (`analysis/README.md`, `docs/results_outline.md`)

### Contexto activo

- Modelo base / referencia: `opp_v4` (exacto, ZIMPL+SCIP), comparado también contra `opp_v5` (exacto, descomposición en 2 etapas).
- Modelos alternativos vigentes: `opp_hc_2/3/4` (Hill Climbing), `opp_aco_2/3/4` (ACO).
- Alcance de la tesina confirmado (2026-09-17): solo `opp_v4` en adelante, incluyendo sus heurísticas. `opp`, `opp_v2`, `opp_v3`, `opp_hc`, `opp_aco` (sin numerar) son legacy — se mantienen en el repo por historial pero quedan fuera del alcance de la tesina.
- Aspecto prioritario actual: limpieza y reorganización del repo (deduplicación de tests entre familias HC/ACO, centralización de escenarios hoy dispersos entre carpetas legacy y vigentes, renombres de archivos/carpetas) antes de separar en un repo aparte lo que sí entra en la tesina (tarea futura, todavía no iniciada).
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
  - [tests/opp_v4/tests/normal](tests/opp_v4/tests/normal)
  - [tests/opp_v4/tests/stress](tests/opp_v4/tests/stress)
  - [tests/opp_v4/tests/opp_test_case_v4.py](tests/opp_v4/tests/opp_test_case_v4.py)
  - [tests/opp_hc_2/tests/normal](tests/opp_hc_2/tests/normal)
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
  - `git status --short` confirmó la reorganización del árbol de tests y la presencia de cambios relevantes en [tests/opp_v4/tests/normal](tests/opp_v4/tests/normal) y [tests/opp_v4/tests/stress](tests/opp_v4/tests/stress).
  - Verificación compilatoria del árbol v4: `NO_COMPILATION_ERRORS`.
  - Revisión del IDE en los archivos afectados: `No errors found` en los tests corregidos.

### Cambio 2026-08-18 11:15 - Ampliación de validación V4 y nuevos tests de stress
- Autor: [equipo / desarrollador actual]
- Alcance: tests / validación / infraestructura de comparación del modelo V4
- Archivos principales:
  - [tests/opp_v4/tests/normal/test_opp_v4_model_19.py](tests/opp_v4/tests/normal/test_opp_v4_model_19.py)
  - [tests/opp_v4/tests/route_assertions.py](tests/opp_v4/tests/route_assertions.py)
  - [tests/opp_v4/tests/stress/test_opp_v4_model_12.py](tests/opp_v4/tests/stress/test_opp_v4_model_12.py)
  - [tests/opp_v4/tests/stress/test_opp_v4_model_13.py](tests/opp_v4/tests/stress/test_opp_v4_model_13.py)
  - [tests/opp_v4/tests/stress/test_opp_v4_model_14.py](tests/opp_v4/tests/stress/test_opp_v4_model_14.py)
  - [tests/opp_v4/tests/stress/test_opp_v4_model_24.py](tests/opp_v4/tests/stress/test_opp_v4_model_24.py)
  - [tests/opp_v4/tests/stress/test_opp_v4_model_25.py](tests/opp_v4/tests/stress/test_opp_v4_model_25.py)
  - [tests/opp_v4/tests/stress/test_opp_v4_model_26.py](tests/opp_v4/tests/stress/test_opp_v4_model_26.py)
  - [tests/opp_v4/tests/stress/test_opp_v4_model_27.py](tests/opp_v4/tests/stress/test_opp_v4_model_27.py)
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
  - Evidencia del estado actual: `git status --short` muestra cambios en [meta.md](meta.md) y [tests/opp_v4/tests/normal/test_opp_v4_model_19.py](tests/opp_v4/tests/normal/test_opp_v4_model_19.py), además de nuevos archivos bajo [tests/opp_v4/tests/stress/](tests/opp_v4/tests/stress/) y [tests/opp_v4/scenarios/stress/](tests/opp_v4/scenarios/stress/).
  - No se afirmaron resultados de tests completos ni ejecución exitosa de la suite, porque esa verificación no se ejecutó en esta revisión.

---

### Cambio 2026-09-17 - Limpieza y reorganización del repo (en curso)
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
  - Se creó `tests/run_suite.py`, un único script parametrizado (`python -m tests.run_suite <modelo> <normal|stress> [--id NN]`) que reemplaza los ~24 `execute_tests.py`/`execute_stress_tests.py` casi idénticos, uno por modelo. Se actualizaron todas las referencias en docs (`analysis/README.md`, `analysis/run_analysis.py`, `analysis/load.py`, READMEs de `opp_hc`, `opp_hc_2`, `opp_hc_4`, `opp_aco_4`). Los legacy `opp`/`opp_v2` quedan con sus propios scripts (no usan `TestRunner`, estructura distinta).
  - Se creó `tests/family_case.py::family_case()` (mismo mecanismo que `tests/opp_v5/tests/v4_compat.py::migrated_case()`, generalizado): parchea a nivel de módulo, solo durante `setUp`/`tearDown` de cada test, los nombres de clase (modelo/DTO/output_handler) que un archivo de test de `opp_hc_2`/`opp_aco_2` resuelve en tiempo de llamada — permite que `opp_hc_3`/`opp_hc_4` y `opp_aco_3`/`opp_aco_4` reutilicen el mismo archivo base sin tocar una sola aserción. El parcheo es *scoped* a la duración de cada test (no permanente) para que dos familias que comparten el mismo módulo base no se pisen si corren juntas en el mismo proceso — verificado explícitamente corriendo las 4 familias juntas (215 tests, 0 errores).
  - Con esa factory, se convirtieron **140 archivos** de duplicado literal a una sola línea de factory, en las 4 familias (`hc_3`: 24 normal; `hc_4`: 23 normal + 9 estrés; `aco_3`: 24 normal + 17 estrés; `aco_4`: 23 normal + 20 estrés). Se dejaron sin tocar los archivos con contenido propio de cada familia (congestión, cadena de frío, tests con aserciones reescritas) y los que no tienen equivalente en la base.
  - En el camino se encontró y corrigió un bug real: `test_opp_hc_4_model_22_23.py`/`test_opp_aco_4_model_22_23.py` se habían clasificado mal como duplicados literales (su diff con la base solo mostraba líneas de import, pero importan un helper de escenario con DTO distinto que la factory no puede alcanzar) — se detectó porque las suites pasaron de 0 a 2 errores tras convertirlos, se revirtieron ambos archivos a su contenido original y quedaron excluidos de la conversión.
- Pendiente (plan completo, todavía no ejecutado):
  - Renombrar carpetas/archivos de test (`normal`→`functional`, sin nombre de modelo en el archivo, renumeración continua).
- Impacto:
  - Una sola fuente de verdad para qué modelos cubre el estudio de estabilidad de semilla; menos riesgo de que ese registro y `analysis/config.py` se desincronicen a futuro.
  - Ningún modelo (legacy ni vigente) depende ya de una carpeta `scenarios/` de otro modelo para sus propios tests — todo vive en `tests/shared_scenarios/`.
  - Un solo lugar (`tests/run_suite.py`) para correr cualquier suite, en vez de 24 scripts casi idénticos.
  - 140 archivos de test menos que mantener a mano en cada cambio futuro al comportamiento base de `opp_hc_2`/`opp_aco_2` — un fix ahí se refleja automáticamente en `hc_3`/`hc_4`/`aco_3`/`aco_4` sin tener que re-portar nada.
- Riesgo / atención:
  - El resto del plan (renombres) es un cambio grande que toca cientos de archivos — se ejecuta por fases verificables, no de una sola vez.
  - `opp_v4`, con la extensión de picker/asignación (`P`/`x`) en sus propios escenarios, NO es un duplicado del trío — se movió a `shared_scenarios/` con sufijo `_v4` sin fusionar contenido con nada.
  - Estrés de `opp_hc_3`: de los 20 archivos, solo 04/05/06 eran copias literales de `opp_hc_2` (convertidos a factory, pasan). Los otros 17 son escenarios genuinamente distintos que reusan el número de test — ej. `opp_hc_3` 12-19 son las instancias intermedias agregadas después, mientras `opp_hc_2` usa esos números para grillas gigantes; esa es la inconsistencia de numeración entre familias que resuelve la fase 3.
- Validación:
  - `python -m analysis.run_analysis` corrido antes y después: mismo conjunto de CSVs leídos, mismas filas/columnas en `analysis/output/report.md` (diferencias solo en el último dígito de punto flotante, sin relación con este cambio).
  - Suite normal de los 9 paquetes afectados por la centralización del trío corrida antes/después (vía `git stash`/`stash pop` para tener una base real): mismos conteos de test exactamente (`opp_v3` 48 con la misma 1 falla preexistente no relacionada — `test_bridge_earliness_order_size`, precisión numérica; el resto, 46-59 tests cada uno, todos OK sin cambios). Doble-verificado de forma independiente corriendo `opp_hc_2`, `opp_hc_4` y `opp_aco_3` manualmente después.
  - `opp_v4`/`opp_v5` normal y stress verificados antes/después del movimiento de sus escenarios propios: mismos conteos (`opp_v4` normal 46, `opp_v5` normal 53, `opp_v5` stress 8) — coincide con los números ya conocidos de `analysis/output/report.md`.
  - `tests/run_suite.py` verificado comparando la lógica de discovery (`start_dir`/`pattern`) contra la de los scripts originales para varios modelos y el modo `--id`: mismos test IDs encontrados en todos los casos.
  - Conversión a `family_case()`: conteos de test idénticos antes/después en las 4 familias, tier normal (`hc_3` 51, `hc_4` 51, `aco_3` 59, `aco_4` 54, todos `OK`) — verificado de forma independiente además de por el propio proceso de conversión. Tier estrés verificado por compilación (`py_compile`, 0 errores en 142 archivos) + chequeo de imports + comparación exhaustiva de imports contra el archivo base (0 discrepancias tras el fix del bug de arriba), más 2 corridas reales de punta a punta como muestra (`opp_hc_4` model_03, `opp_aco_3` model_04, ambas `OK`) — no se corrieron las 4 baterías de estrés completas por el tiempo que toman.
  - Chequeo de seguridad cruzada entre familias: las 4 familias completas (tier normal, 215 tests) corridas juntas en un solo proceso de Python — 0 errores, 0 fallas — confirma que el parcheo scoped a `setUp`/`tearDown` evita que `hc_3`/`hc_4` (o `aco_3`/`aco_4`) se pisen al compartir el mismo módulo base.

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
- [graphs/](graphs/)
- [observer/](observer/)
- [utils/](utils/)

### Testing
- [tests/](tests/)

### Modelos relevantes
- [models/opp/](models/opp/)
- [models/opp_aco/](models/opp_aco/)
- [models/opp_hc/](models/opp_hc/)
- [models/opp_aco_3/](models/opp_aco_3/)
- [models/opp_hc_3/](models/opp_hc_3/)

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
- [Riesgo 1: inconsistencia de imports entre modelos]
- [Riesgo 2: diferencias de resultados entre heurísticas y modelo exacto]
- [Riesgo 3: validación parcial de escenarios]

### Pendientes
- [ ] Revisión de modelos no consolidados
- [ ] Alinear nombres y documentación por modelo
- [ ] Completar pruebas faltantes
- [ ] Revisar performance / estabilidad de heurísticas

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
