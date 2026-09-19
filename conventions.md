# Convenciones de Código
## Repositorio: Linear Picking Routing (Tesis de Grado)

Este documento sirve como guía estricta y vinculante para cualquier agente autónomo o sistema de generación de código que interactúe con este repositorio. El objetivo principal es mantener la coherencia arquitectónica, garantizar la paridad en la comparación de modelos y evitar regresiones en los tests existentes.

---

### 1. Convenciones de Nomenclatura (Naming Conventions)

* **Archivos y Módulos (.py):** Siempre en `snake_case`. Los nombres deben ser descriptivos del modelo o su función.
    * *Ejemplos:* `opp_model_v3.py`, `constraints_validator.py`, `route_evaluator.py`.
* **Clases:** Siempre en `PascalCase`. 
    * *Ejemplos:* `OPPModelV3`, `OPPHillClimbingV3`, `ConstraintsValidator`, `OutputHandler`.
* **Métodos y Funciones:** Siempre en `snake_case`. Los métodos públicos deben comenzar con verbos de acción.
    * *Ejemplos:* `solve()`, `validate_constraints()`, `calculate_objective()`.
* **Variables y Atributos:** Siempre en `snake_case`. Evitar abreviaturas crípticas a menos que correspondan exactamente a los parámetros matemáticos del modelo original (ej. `w1`, `w2`, `gamma`, `delta`).
    * *Ejemplos:* `current_route`, `is_feasible`, `active_arcs`.
* **Constantes:** Siempre en `UPPER_SNAKE_CASE`.
    * *Ejemplos:* `MAX_ITERATIONS`, `BIG_M`, `DEFAULT_TIMEOUT`.
* **Archivos de Test:** Llevan siempre el prefijo `test_case_` seguido de un número de dos dígitos o de un identificador descriptivo en `snake_case`. No repiten el nombre del modelo ni el del tier: ya los da el directorio (`tests/<modelo>/<tier>/`).
    * *Numerados* (continuos, sin huecos, dentro de cada modelo y tier): `tests/opp_hc_2/functional/test_case_02.py`, `tests/opp_hc_2/stress/test_case_11.py`.
    * *Descriptivos* (tests propios de una familia, sin equivalente en su base): `tests/opp_hc_3/functional/test_case_congestion.py`.
* **Data Transfer Objects (DTOs):** Siempre deben finalizar con el sufijo `DTO`.
    * *Ejemplos:* `ModelDTO`, `SolveModelDTO`, `SolveHCModelDTO`.

El código se debe escribir en inglés.

---

### 2. Convenciones de Estructura de Directorios (Dirs Conventions)

El repositorio sigue un patrón modular estricto por modelo. No se deben mezclar lógicas de distintas naturalezas dentro de un mismo directorio.

```text
raiz-del-proyecto/
├── dtos/                        # DTOs globales compartidos por los modelos
│   ├── opp/                     # DTOs del problema OPP (compartidos por todos los modelos)
│   ├── hc/                      # DTOs de la heurística Hill Climbing
│   └── aco/                     # DTOs de Ant Colony Optimization
├── models/                      # Todos los resolvedores (exactos e heurísticos)
│   ├── base/                    # Clases base abstractas compartidas
│   │   ├── model.py             # Clase abstracta Model (base del patrón Observer)
│   │   └── opp_location_graph.py# Grafo base de locaciones
│   ├── opp_v1 ... opp_v5/       # Modelos exactos (v1-v3 PySCIPOpt, v4-v5 ZIMPL+SCIP)
│   ├── opp_hc_1 ... opp_hc_4/   # Heurísticas Hill Climbing
│   └── opp_aco_1 ... opp_aco_4/ # Metaheurísticas ACO
├── observer/                    # Infraestructura del patrón de diseño Observer
│   └── observer.py              # Clase abstracta Observer
├── tests/                       # Suite de testing organizada por modelo
│   ├── opp_test_case.py         # TestCase base compartida (OPPTestCase)
│   ├── family_case.py           # Fábrica que adapta los tests de opp_hc_2/opp_aco_2 a sus familias
│   ├── run_suite.py             # Punto de entrada único: python -m tests.run_suite <modelo> functional|stress
│   ├── test_runner.py           # Ejecuta cada test aislado, con timeout, y escribe el CSV en results/
│   ├── shared_scenarios/        # Todos los escenarios (grafos y parámetros); los propios de un modelo llevan sufijo _vN
│   │   ├── common/  functional/  stress/
│   └── opp_hc_2/                # Un directorio por modelo
│       ├── doc/                 # Documentación técnica de los casos de prueba (si existe)
│       ├── functional/          # Pruebas funcionales regulares: test_case_01.py, test_case_02.py, ...
│       └── stress/              # Pruebas de estrés
└── results/                     # CSV de resultados (datos generados): results/<modelo>/<functional|stress|stability>/
```

Los escenarios ya no viven dentro de cada modelo: están todos en `tests/shared_scenarios/`. Un escenario compartido por varios modelos no lleva sufijo; uno propio de un modelo lleva su sufijo (`scenario_01_v4.py`, `single_order_params_hc4.py`).


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

* Prohibición Absoluta: NO se permite el uso de variables de entorno manuales, manipulación con sys.path.append(), inicializaciones con pathlib para alterar el sys path, ni ninguna otra variante sintáctica. Tampoco se admiten imports relativos en archivos ejecutables. Todos los imports deben ser absolutos a partir del root del proyecto (from models.opp_v3...).

### 4. Convenciones para la Creación de Tests
El marco de validación científica de la tesis exige comparar modelos exactos contra heurísticas bajo las mismas condiciones.

* Clonación Estricta: Al desarrollar un nuevo modelo heurístico, su batería de pruebas debe ser una copia exacta de los escenarios lógicos de opp_v3.
* Adaptación Técnica Permitida: Solo se permite modificar lo estrictamente necesario para que el test compile y ejecute:
  * Mapeos de imports (para apuntar al nuevo modelo heurístico y a sus DTOs correspondientes).
  * Instanciación del modelo y su respectivo output_handler.
* Inmutabilidad de Aserciones: BAJO NINGUNA CIRCUNSTANCIA el agente debe relajar, comentar o eliminar un assertEqual, assertTrue o validación matemática del test original, a menos que el usuario lo autorice explícitamente (ej. debido a la tolerancia decimal aceptada en heurísticas). Lo que el test valida a nivel de negocio debe preservarse idéntico.
* Uso de Helpers: Es obligatorio usar los métodos de conveniencia heredados o importados para manipulación de parámetros de test, tales como:
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
Los métodos de prueba dentro de los archivos de test no deben documentar la mecánica del código, sino la **intención del negocio o restricción matemática** bajo prueba.
* *Formato Correcto:* `"""Verifica el comportamiento de penalización por tardanza (tardiness) aislando la función objetivo con w1=0 y w2=1 en un grafo desconectado."""`
* *Formato Incorrecto:* `"""Prueba que da falso con dto y weights."""`

#### 5.3. Estructura de Documentos de Escenarios (`test_cases.md`)
Cada modelo debe incluir en su carpeta `doc/` archivos markdown que documenten detalladamente cada escenario de prueba utilizando la siguiente estructura fija:
* **ID de Escenario:** Coincidente con el número de archivo (ej. Escenario 1).
* **Descripción del Grafo:** Layout de depósito, pasillos, nodos finales y distancias.
* **Configuración de Órdenes:** Lista de órdenes, locaciones requeridas, volúmenes (`cap_n`) y ventanas de tiempo (`due_date`).
* **Resultado Esperado:** Factibilidad, valor óptimo teórico de la función objetivo, arcos activos esperados.

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

1.  **Validación Previa:** Antes de escribir una sola línea de código para un nuevo modelo heurístico, el agente debe leer las especificaciones del archivo de requerimientos particulares (ej. `model_based_on_opp_v3_specs.md`).
2.  **Consulta Obligatoria ante Ambigüedades:** Si un requerimiento técnico o fórmula matemática de penalización genera dudas de interpretación, el agente tiene prohibido tomar decisiones autónomas de diseño. Debe pausar la ejecución y consultar al usuario.
3.  **Fidelidad al Legado:** El código exacto (por ejemplo, `opp_v3` en `model_based_on_opp_v3_specs.md`) es la verdad absoluta de negocio. Si una heurística produce resultados lógicamente inconsistentes con los tests clonados del modelo, el error reside en la implementación de la heurística y no en el caso de prueba. No se permite alterar los tests para forzar su aprobación ("pasar en verde").