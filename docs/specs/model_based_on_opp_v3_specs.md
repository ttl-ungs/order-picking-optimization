# Especificación de Diseño de Software (SDD)
## Creación de Modelos Heurísticos / Metaheurísticos basados en `opp_v3`

### 1. Propósito y Alcance
El presente documento establece las especificaciones estrictas para la creación de nuevos modelos de resolución (heurísticos o metaheurísticos) derivados del modelo de programación lineal exacta `opp_v3`. El objetivo principal es garantizar que los nuevos modelos sean arquitectónica y lógicamente compatibles con `opp_v3` para permitir una comparación científica rigurosa y justa en el marco de la tesis de grado.

### 2. Principios Fundamentales y Flujo de Trabajo
* **Tipo de heurística:** La elección del algoritmo (ej. Hill Climbing, Simulated Annealing, Algoritmos Genéticos, Ant Colony Optimization, etc.) será **definida exclusivamente por el usuario**.
* **Consulta obligatoria:** **SIEMPRE** se debe consultar al usuario antes de tomar cualquier decisión de diseño, arquitectura o implementación. Bajo ninguna circunstancia se deben tomar decisiones autónomas que alteren el flujo, la lógica o las convenciones sin validación explícita.
* **Convenciones del Repositorio:** El desarrollador/agente debe consultar y adherirse estrictamente a las convenciones de código, nombrado y estructura de directorios del repositorio existente.

### 3. Especificaciones del Dominio y Modelo
Para asegurar una comparación 1 a 1 entre el modelo exacto (`opp_v3`) y las nuevas heurísticas, se aplican las siguientes reglas inquebrantables:

#### 3.1. Restricciones y Parámetros
* **Preservación absoluta:** Las restricciones, los parámetros, las variables de decisión (en su representación lógica) y **cualquier** característica particular del modelo `opp_v3` se deben mantener intactas en la lógica de evaluación y factibilidad de la heurística.
* **Prohibición de alteraciones:**
  * **NO** se debe agregar ninguna restricción nueva.
  * **NO** se debe eliminar ninguna restricción existente.
  * **NO** se debe modificar el comportamiento o los límites de las restricciones actuales.
* Toda solución generada por la heurística debe ser factible según las reglas exactas definidas en `opp_v3`. En caso de usar heurísticas con penalizaciones por infactibilidad, las funciones de penalización deben reflejar matemáticamente las restricciones duras de `opp_v3`.

#### 3.2. Formato de Entrada (Input)
* El formato de entrada para la inicialización y ejecución del modelo debe mantenerse **idéntico** al de `opp_v3` (mismos DTOs, diccionarios, o firmas de métodos). Esto garantiza que los mismos escenarios de prueba alimenten sin fricción a cualquier modelo.

#### 3.3. Formato de Salida (Output)
* Se permite modificar el formato y las estructuras de datos del output de ser estrictamente necesario por la naturaleza del modelo heurístico.
* **Condición de similitud:** A pesar de los cambios de formato, la *información* devuelta debe ser análoga y comparable a la del modelo original (ej. valor de la función objetivo, rutas de picking, asignaciones de órdenes a vehículos/pickers, tiempos de procesamiento, métricas de rendimiento).
* **Manejo aislado:** Cada nuevo modelo debe implementar obligatoriamente su propio módulo `output_handler` para procesar, formatear y exportar sus resultados de forma independiente.

### 4. Especificaciones de Testing (QA)
La validación de los nuevos modelos se basará íntegramente en la batería de pruebas existente para `opp_v3`.

* **Clonación de Tests:** Al generar un nuevo modelo, se deben generar sus respectivos tests copiando los casos de prueba normales y de estrés (stress tests) de `opp_v3`.
* **Adaptación permitida:** Los tests copiados deben adaptarse únicamente en cuestiones técnicas y de "plomería":
  * Modificación de *imports* para apuntar al nuevo modelo y su *output_handler*.
  * Adaptaciones menores en el mapeo de *inputs* y *outputs* para ajustarse a las particularidades permitidas en la sección 3.3.
* **Inmutabilidad de las aserciones:** **NUNCA** se debe modificar la aserción lógica o matemática de lo que prueba el caso de test (ej. si el test valida que la capacidad máxima no se excede, esa validación debe permanecer idéntica). Solo se podrán relajar o alterar estas aserciones si existe una aceptación explícita previa por parte del usuario.

### 5. Resumen del Checklist de Implementación
1. [ ] Consultar al usuario qué heurística se va a implementar.
2. [ ] Revisar la estructura de `opp_v3` y las convenciones del repositorio.
3. [ ] Diseñar el modelo preservando 100% las restricciones y parámetros de `opp_v3`.
4. [ ] Mantener el input idéntico.
5. [ ] Crear un `output_handler` propio para el nuevo modelo garantizando paridad de información.
6. [ ] Clonar tests de `opp_v3` y adaptarlos a nivel infraestructura (imports/outputs).
7. [ ] Mantener aserciones lógicas intactas.
8. [ ] **Validar cada uno de estos pasos con el usuario antes de darlo por cerrado.**
