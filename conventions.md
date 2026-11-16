# Convenciones de Código
## Repositorio: Linear Picking Routing (Tesis de Grado)

Este documento sirve como guía estricta y vinculante para cualquier agente autónomo o sistema de generación de código que interactúe con este repositorio. El objetivo principal es mantener la coherencia arquitectónica, garantizar la paridad en la comparación de modelos y evitar regresiones en los tests existentes.

---

### 1. Convenciones de Nomenclatura (Naming Conventions)

* **Archivos y Módulos (.py):** Siempre en `snake_case`. Los nombres deben ser descriptivos del modelo o su función.
    * *Ejemplos:* `opp_hc.py`, `constraints_validator.py`, `route_evaluator.py`.
* **Clases:** Siempre en `PascalCase`.
    * *Ejemplos:* `OPPHillClimbing`, `OPPAntColonyOptimization`, `ConstraintsValidator`, `OutputHandler`.
* **Métodos y Funciones:** Siempre en `snake_case`. Los métodos públicos deben comenzar con verbos de acción.
    * *Ejemplos:* `solve()`, `validate_constraints()`, `calculate_objective()`.
* **Variables y Atributos:** Siempre en `snake_case`. Evitar abreviaturas crípticas a menos que correspondan exactamente a los parámetros matemáticos del modelo (ej. `W_c`, `W_pen`, `T_setup`, `V_p`).
    * *Ejemplos:* `current_route`, `is_feasible`, `active_arcs`.
* **Constantes:** Siempre en `UPPER_SNAKE_CASE`.
    * *Ejemplos:* `MAX_ITERATIONS`, `BIG_M`, `DEFAULT_TIMEOUT`.
* **Archivos de Test:** Llevan siempre el prefijo `test_case_` seguido de un identificador descriptivo en `snake_case`; los casos compartidos son `case_NN.py` (dos dígitos, continuos, sin huecos). No repiten el nombre del modelo ni el del tier: ya los da el directorio.
    * *Casos compartidos:* `tests/functional_cases/case_24.py`, `tests/stress_cases/case_04.py`.
    * *Tests propios de un modelo:* `tests/opp_hc/functional/test_case_invalid_speed_rejected.py`.
* **Data Transfer Objects (DTOs):** Siempre deben finalizar con el sufijo `DTO`.
    * *Ejemplos:* `ModelDTO`, `SolveModelDTO`, `SolveHCModelDTO`, `SolveAcoModelDTO`.

El código se debe escribir en inglés.

---

### 2. Convenciones de Estructura de Directorios (Dirs Conventions)

El repositorio contiene los cuatro modelos de la tesis (OPP-Split, OPP-Mono, OPP-HC y OPP-ACO) y lo que los ejecuta y verifica. No se deben mezclar lógicas de distintas naturalezas dentro de un mismo directorio.

```text
raiz-del-proyecto/
├── dtos/                        # DTOs compartidos
│   ├── opp/                     # DTOs del problema OPP (compartidos por todos los modelos)
│   ├── hc/  aco/                # Parámetros de las heurísticas
│   └── verification/            # DTO del reporte de cumplimiento
├── models/
│   ├── base/                    # Clase abstracta Model (patrón Observer) y grafo de locaciones
│   ├── utils/                   # Código compartido por los modelos (validaciones previas, rutas, SLA)
│   ├── opp_split/  opp_mono/    # Modelos exactos (ZIMPL + SCIP)
│   └── opp_hc/  opp_aco/        # Heurísticas (Hill Climbing, Ant Colony Optimization)
├── observer/                    # Infraestructura del patrón Observer
├── tests/
│   ├── run_suite.py             # Punto de entrada único: python -m tests.run_suite <modelo> functional|stress
│   ├── functional_cases/        # Los casos funcionales, escritos una vez (case_NN.py)
│   ├── stress_cases/            # Los escenarios de estrés, escritos una vez (case_NN.py)
│   ├── infra/                   # Infraestructura de tests (no son tests): execution/, cases/, factories/, zimpl/
│   ├── shared_scenarios/        # Grafos y escenarios compartidos: common/, functional/, stress/
│   └── opp_split/ ...           # Un directorio por modelo: enlaza el modelo con los casos compartidos
│       ├── functional/          #   test_functional_cases.py + tests propios
│       └── stress/              #   test_stress_cases.py + adaptador
├── results/                     # CSV de resultados: results/<modelo>/<functional|stress>/, compliance/, comparability/, equal_time/
├── verification/                # Verifica soluciones de las heurísticas contra opp_mono; compara opp_split con opp_mono
├── experiments/                 # Lo que no es un test y lee o produce results/, según para quién es
│   ├── common/                  #   todos los modelos: qué archivos de resultados cuentan
│   ├── comparison/              #   los modelos entre sí: comparabilidad y tiempo igual
│   ├── exact/                   #   OPP-Split y OPP-Mono: exploraciones e informes
│   └── heuristics/              #   OPP-HC y OPP-ACO: estudios (hc/, aco/)
├── scripts/                     # check_repo, run_all, make_stress_smoke (ver scripts/README.md)
├── .github/workflows/           # CI: ci.yml (por PR) y nightly.yml (programado)
└── docs/                        # Especificaciones, guía de estilo e informes generados (ver README.md)
```

Los escenarios no viven dentro de cada modelo: están todos en `tests/shared_scenarios/`.


### 3. Resolución Dinámica de Rutas (sys.path.insert)
Para asegurar que cualquier test o script sea ejecutable de forma directa desde la terminal o el IDE sin fallas de importación (ModuleNotFoundError), se utiliza un hack estricto de resolución dinámica del path de ejecución.

* El Snippet Obligatorio: En la cabecera de todo archivo ejecutable principal (test, script de estrés, ejemplo de uso), se DEBE incluir exactamente el siguiente bloque de código antes de cualquier importación local:

```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

    (Nota: El número de saltos de directorio ".." debe ajustarse exactamente según la profundidad del archivo respecto a la raíz del proyecto para que el path apunte siempre al root).

* ¿Para qué se usa? Permite que Python reconozca la raíz del proyecto como el directorio de búsqueda de módulos prioritario, garantizando que los entornos virtuales y entornos de CI/CD funcionen de manera idéntica.

* Prohibición Absoluta: NO se permite el uso de variables de entorno manuales, manipulación con sys.path.append(), inicializaciones con pathlib para alterar el sys path, ni ninguna otra variante sintáctica. Tampoco se admiten imports relativos en archivos ejecutables. Todos los imports deben ser absolutos a partir del root del proyecto (from models.opp_hc import ...).

### 4. Convenciones para la Creación de Tests
El marco de validación científica de la tesis exige que los cuatro modelos resuelvan los mismos casos bajo las mismas condiciones.

* **Un caso, una vez:** Cada caso funcional vive en `tests/functional_cases/case_NN.py` y cada escenario de estrés en `tests/stress_cases/case_NN.py`. Un caso no sabe qué modelo lo resuelve: llama a `self.solve(...)`, `self.run_pipeline(...)` o `self.assert_stress_pipeline(...)`, que implementa el adaptador de cada modelo. `bind_cases` genera las clases de test de cada modelo.
* **Etiquetas:** Cada método de test de un caso funcional lleva en su docstring la etiqueta del anexo de la tesis (por ejemplo `Case 24a`); las letras siguen el orden alfabético de los métodos del caso.
* **Heurísticas:** OPP-HC y OPP-ACO ejecutan las mismas instancias de los casos funcionales (capturadas de las corridas de OPP-Split) y se contrasta el estado, no el objetivo exacto.
* **Inmutabilidad de Aserciones:** BAJO NINGUNA CIRCUNSTANCIA el agente debe relajar, comentar o eliminar un assertEqual, assertTrue o validación matemática de un caso, a menos que el usuario lo autorice explícitamente. Lo que el test valida a nivel de negocio debe preservarse idéntico.
* **No agregar tests sin pedido:** No se agregan tests nuevos que no correspondan a un caso de la tesis o que no sumen cobertura de lógica del modelo.
* **Uso de Helpers:** Es obligatorio usar los métodos de conveniencia heredados o importados para manipulación de parámetros de test, tales como:
  * OPPTestCase.normalize_due_dates()
  * OPPTestCase.apply_weight_overrides()
  * OPPTestCase.sum_vars_with_prefix()

### 5. Convenciones de Documentación (Docs Conventions)

#### 5.1. Código Fuente (Módulos, Clases y Métodos)
Los comentarios deben ser en inglés.
Se debe utilizar obligatoriamente el formato de Docstrings de Google (PEP 257) para documentar:
1.  **Propósito:** Breve descripción del objetivo del componente.
2.  **Argumentos (`Args`):** Enumeración de parámetros indicando nombre, tipo y descripción.
3.  **Retornos (`Returns`):** Tipo de dato devuelto y significado.

*Ejemplo en código:*
```python
def validate_vehicle_capacity(self, route: list, batch_id: int) -> bool:
    """Comprueba que la carga total de las órdenes asignadas al lote no exceda la capacidad del vehículo.

    Args:
        route (list): Lista ordenada de nodos visitados en el viaje.
        batch_id (int): Identificador del lote bajo evaluación.

    Returns:
        bool: True si la ruta es factible a nivel de capacidad, False en caso contrario.
    """
```

#### 5.2. Documentación de Tests
Los métodos de prueba no deben documentar la mecánica del código, sino la **intención del negocio o restricción matemática** bajo prueba.
* *Formato Correcto:* `"""Verifica el comportamiento de penalización por tardanza (tardiness) aislando la función objetivo con W_c=0 y W_pen=1 en un grafo desconectado."""`
* *Formato Incorrecto:* `"""Prueba que da falso con dto y weights."""`

---

### 6. Convenciones de Arquitectura: Herencia, DTOs y Patrón Observer

* **Herencia de Modelos:** Todo solver debe heredar de la clase base abstracta `Model` (`models/base/model.py`). Esto obliga a implementar la firma unificada del método `solve()` y hereda los mecanismos para interactuar con observadores.
* **Encapsulamiento mediante DTOs:** Queda estrictamente **prohibido** el paso de parámetros primitivos sueltos en las firmas de los métodos principales de inicialización o resolución. Toda la información de entrada debe viajar encapsulada en objetos contenedores (`ModelDTO`, `SolveModelDTO`).
* **Patrón Observer para Salidas (Output):** La lógica de cálculo matemática está desacoplada al 100% de la lógica de visualización o guardado de resultados.
    * Un modelo **NUNCA** debe contener sentencias `print()` de resultados intermedios, ni guardar archivos CSV o logs de solución dentro de su algoritmo principal.
    * Al finalizar el cálculo, el modelo debe invocar obligatoriamente a `self.notify(result_data)`.
    * Cada modelo debe tener asignado su propio `utils/output_handler.py` que herede de `Observer` (`observer/observer.py`). Este handler se acopla dinámicamente en tiempo de ejecución (normalmente en los métodos de configuración de los tests) mediante `model.attach(handler)`.

---

### 7. Directrices de Comportamiento del Agente Autónomo

1.  **Consulta Obligatoria ante Ambigüedades:** Si un requerimiento técnico o fórmula matemática de penalización genera dudas de interpretación, el agente tiene prohibido tomar decisiones autónomas de diseño. Debe pausar la ejecución y consultar al usuario.
2.  **Los modelos exactos son la verdad de negocio:** Si una heurística produce resultados lógicamente inconsistentes con los casos, el error reside en la implementación de la heurística y no en el caso de prueba. No se permite alterar los casos para forzar su aprobación ("pasar en verde").
3.  **Sin referencias a versiones anteriores:** Ningún archivo menciona versiones anteriores de los modelos (`check_repo` lo verifica).
