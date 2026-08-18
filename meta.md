# Meta del Repositorio

Este archivo funciona como resumen operativo del proyecto para trabajo compartido. Su objetivo es que una IA o un desarrollador pueda entender el estado actual del repositorio sin tener que leer todo el código ni la documentación completa.

> Regla de mantenimiento: cada cambio importante debe dejarse registrado en esta página. No se borra el historial anterior; se agrega un nuevo bloque al inicio o al final y se actualiza el estado general.

---

## 1. Resumen ejecutivo

- Proyecto: Linear Picking Routing
- Tipo: Optimización / routing de picking en almacén
- Stack principal: Python, PySCIPOpt, modelos exactos y heurísticos
- Estado actual: [En desarrollo / estable / bloqueado / en revisión]
- Última actualización: [YYYY-MM-DD]
- Responsable actual: [Nombre / equipo]

### Objetivo del repositorio

- Resolver problemas de batching, asignación, secuenciación y routing de picking.
- Comparar modelos exactos y heurísticos bajo escenarios equivalentes.
- Mantener una estructura consistente para validación y análisis académico.

---

## 2. Estado actual del proyecto

### Estado general

- [ ] Repositorio funcional en entorno local
- [ ] Pruebas principales ejecutándose
- [ ] Modelos comparables alineados
- [ ] Documentación clave actualizada
- [ ] Riesgos conocidos documentados

### Contexto activo

- Modelo base / referencia: [ej. opp_v3]
- Modelos alternativos: [opp_aco, opp_hc, opp_aco_3, opp_hc_3, etc.]
- Aspecto prioritario actual: [ej. validación de heurística, reproducción de resultados, estabilización de lectura de datos, etc.]
- Bloqueador actual: [si aplica]

---

## 3. Cambios recientes

### Formato recomendado para cada cambio

#### Cambio [YYYY-MM-DD] - [Título breve]
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

#### Cambio 2026-08-18 11:15 - Ampliación de validación V4 y nuevos tests de stress
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

## 4. Archivos clave del repositorio

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

## 5. Dependencias y entorno

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

## 6. Riesgos, deuda y pendientes

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

## 7. Criterios para actualizar este archivo

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

## 8. Instrucción directa para la IA

La IA encargada de modificar este repositorio debe seguir esta secuencia:

1. Leer este archivo antes de empezar.
2. Identificar si el cambio afecta arquitectura, modelos, tests o documentación.
3. Actualizar la sección de cambios recientes con un bloque nuevo.
4. Actualizar el resumen ejecutivo si hubo un cambio de estado.
5. Revisar y ajustar riesgos / pendientes si corresponde.
6. Dejar evidencia de validación en el bloque del cambio.
7. Si cambió la lógica del modelo, verificar si también hay impacto en tests comparativos.

> En pocas palabras: este archivo es el “resumen ejecutivo compartido” del repo. Debe mantenerse vivo y útil para todos los que entren después.
