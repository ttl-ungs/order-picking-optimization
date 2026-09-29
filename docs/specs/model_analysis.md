NOTA (2026-09-19): documento histórico de la etapa opp_v3/opp_hc/opp_aco (hoy opp_v3/opp_hc_1/opp_aco_1). La estructura vigente de resultados (`results/<modelo>/<functional|stress>/`) y del pipeline está en `analysis/README.md`.

Especificación de Diseño de Software (SDD)

Pipeline de Análisis de Resultados - LPRP (Linear Picking Routing Problem)

Autores: Soria, Lucía; Ebertz, Ximena
Propósito: Definir de manera formal, estructurada y reproducible la metodología de extracción de datos, filtrado, cálculo de métricas estadísticas, perfilado de ejecución y correlaciones paramétricas (globales y por escenario) para evaluar el desempeño de los modelos de optimización (OPP_v3, Hill Climbing, ACO).

1. Fuentes de Datos (Data Sources)

Los datos de entrada son archivos en formato .csv ubicados en el árbol de directorios de pruebas (results/). El pipeline debe mapear dos dimensiones: Modelo y Escenario.

1.1. Mapeo de Modelos y Directorios

Exacto (OPP_v3): results/opp_v3/

Heurística (HC): results/opp_hc_1/

Metaheurística (ACO): results/opp_aco_1/

1.2. Mapeo de Escenarios y Archivos Específicos

Normal: Archivos que contengan el sufijo _normal_tests_. Se debe tomar siempre el archivo de fecha de modificación más reciente (latest).

Stress: Archivos que contengan el sufijo _stress_tests_.

Excepción (OPP_v3 Stress): Forzar la lectura estricta del archivo consolidado complete_output_v3_stress_tests.csv.

Excepción (ACO Stress): Priorizar la lectura del archivo de máxima densidad output_opp_aco_stress_tests_20260617_123001.csv.

2. Preprocesamiento y Limpieza (Data Cleansing)

Una vez consolidados los 6 DataFrames correspondientes (3 Modelos $\times$ 2 Escenarios), se deben aplicar las siguientes reglas estrictas de transformación:

Conversión de Tipos (Casting): Forzar a formato numérico (flotante/entero) las siguientes columnas paramétricas para evitar errores de cálculo por strings residuales. Valores nulos o errores deben ser coaccionados a NaN.

total_time, model_time, solver_time

N (Cantidad de Pedidos)

V (Nodos/Ubicaciones del Almacén)

B (Cantidad de Batches)

C_v (Capacidad del Vehículo)

W_c (Peso de Utilización)

W_pen (Peso de Penalización Temprano/Tarde)

Filtro de Éxito (Factibilidad Temporal):

Para el cálculo de todas las métricas de tiempo, perfilado y correlación, el dataset de análisis debe ser filtrado estrictamente donde la columna status == 'ok'.

Los estados timeout o failed se conservan únicamente para calcular la Tasa de Éxito global de cada arquitectura.

3. Motor de Cálculo de Métricas (Core Analytics)

3.1. Estadísticas Descriptivas (Por Modelo y Escenario)

El pipeline debe agrupar los datos (groupby(['model', 'scenario'])) y emitir la siguiente matriz descriptiva:

Total de Casos ($Total$): Conteo bruto de filas por grupo.

Casos Exitosos ($OK$): Conteo de filas donde status == 'ok'.

Tasa de Convergencia / Éxito: $\frac{OK}{Total} \times 100$

Tiempo Medio ($\mu$): Promedio aritmético de la columna total_time (solo casos OK).

Desvío Estándar ($\sigma$): Desviación estándar muestral de total_time (solo casos OK).

Tiempo Máximo ($Max$): Valor pico registrado en total_time (solo casos OK).

3.2. Perfilado de Ejecución (Profiling) y Poda Temprana

Exclusivo para el modelo exacto (OPP_v3):

Requiere la ingesta de las columnas accesorias model_time y solver_time.

Ratio de Modelado: $\frac{\mu(\text{model\_time})}{\mu(\text{total\_time})}$

Ratio de Solver: $\frac{\mu(\text{solver\_time})}{\mu(\text{total\_time})}$

Hipótesis a validar: El tiempo de modelado en instancias normales debe representar el $\approx 90\%$.

Análisis de Poda Lógica: Validar paramétricamente si reducir el valor de la penalidad por entrega tardía (ej. $W_{ta}=1$) provoca un incremento en el tiempo medio de ejecución al limitar la poda temprana en el árbol de SCIP.

4. Análisis de Sensibilidad Paramétrica

Para aislar matemáticamente el cuello de botella de cada algoritmo, el pipeline debe iterar sobre los casos exitosos y computar el Coeficiente de Correlación de Pearson ($r$).

Novedad Analítica: Este cálculo debe realizarse en dos niveles:

Nivel Global: Cruzando todos los datos (Normal + Stress) por modelo.

Nivel Escenario: Fragmentando el análisis de Pearson separadamente para casos Normales y casos de Estrés. Esto es vital para revelar que OPP_v3 sufre por Nodos ($V \rightarrow r=0.72$) y Lotes ($B \rightarrow r=0.87$) en la escala Normal, pero muta a sufrir por Pedidos ($N$) en Estrés.

4.1. Formulación Estadística

$$r_{x,y} = \frac{\sum (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum (x_i - \bar{x})^2 \sum (y_i - \bar{y})^2}}$$

Donde la variable dependiente $y$ es total_time, y las independientes ($x$) son: $N, V, B, C_v, W_{full}, W_{ea\_ta}$.

5. Salidas Visuales Requeridas (Data Visualization)

El pipeline de renderizado gráfico (MetaPost / D3 / Python) debe emitir las siguientes cinco visualizaciones con la paleta estricta (#003366, #e6e6e6, #d9534f, #5bc0de, #5cb85c):

Comparativa Global Normal: Barras agrupadas comparando medias de tiempo ($\mu$) entre HC, OPP_v3 y ACO en entorno normal.

Comparativa Global Estrés: Barras agrupadas comparando medias de tiempo ($\mu$) en entorno de estrés.

Barras Apiladas (100%) de Profiling: Gráfico validando el 90% de modelado de OPP_v3 frente al $\le 10\%$ de SCIP puro (mostrando casos muestra y la columna de promedio).

Dispersión Estrés (OPP_v3 vs HC): Gráficos Scatter cruzando Pedidos ($N$) vs $Tiempo Total$. El gráfico de OPP debe evidenciar asintotismo exponencial ($>900s$), mientras que el de HC debe demostrar asintotismo casi plano ($\le 177s$).

Dispersión Estrés Topológico (ACO): Gráfico Scatter cruzando Nodos de Almacén ($V$) vs $Tiempo Total$, reflejando la explosión temporal en redes $>400$ vértices.

6. Referencia de Script Base (Python Engine Actualizado)

Script base para la recuperación de toda la matriz estadística requerida por el documento LaTeX:

import pandas as pd
import glob
import os

# 1. Definición de Rutas
paths = {
    'opp_v3_normal': 'results/opp_v3/normal/*.csv',
    'opp_v3_stress': 'results/opp_v3/stress/complete_output_v3_stress_tests.csv',
    'hc_normal': 'results/opp_hc_1/normal/*.csv',
    'hc_stress': 'results/opp_hc_1/stress/*.csv',
    'aco_normal': 'results/opp_aco_1/normal/*.csv',
    'aco_stress': 'results/opp_aco_1/stress/*20260617_123001.csv',
}

# 2. Función de Recuperación Latest
def get_latest_csv(pattern):
    if 'complete_output' in pattern or '20260617_123001' in pattern:
        exact_files = glob.glob('**/' + pattern.split('/')[-1], recursive=True)
        return exact_files[0] if exact_files else pattern
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None

# 3. Ingesta y Etiquetado
all_dfs = []
for key, pattern in paths.items():
    f = get_latest_csv(pattern)
    if f and os.path.exists(f):
        df = pd.read_csv(f)
        df['model'] = key.split('_normal')[0].split('_stress')[0]
        df['scenario'] = 'normal' if 'normal' in key else 'stress'
        all_dfs.append(df)

df_master = pd.concat(all_dfs, ignore_index=True)

# 4. Transformación Numérica (Incluye Profiling vars)
numeric_cols = ['total_time', 'model_time', 'solver_time', 'N', 'V', 'B', 'C_v', 'W_c', 'W_pen']
for col in numeric_cols:
    if col in df_master.columns:
        df_master[col] = pd.to_numeric(df_master[col], errors='coerce')

# 5. Filtro de Factibilidad Analítica
df_ok = df_master[df_master['status'] == 'ok'].copy()

# 6. Estadísticas Resumen
summary = df_master.groupby(['model', 'scenario']).agg(
    total=('status', 'count'),
    ok=('status', lambda x: (x == 'ok').sum()),
    mean_time=('total_time', 'mean'),
    std_time=('total_time', 'std'),
    max_time=('total_time', 'max')
).reset_index()

# 7. Motor de Correlaciones (Matriz de Pearson Global)
correlations_global = {}
for model in df_ok['model'].unique():
    model_data = df_ok[df_ok['model'] == model]
    correlations_global[model] = model_data[['total_time', 'N', 'V', 'B', 'C_v', 'W_c', 'W_pen']].corr()['total_time'].round(4)

# 8. Motor de Correlaciones (Nivel Escenario Específico)
correlations_scenario = {}
for model in df_ok['model'].unique():
    for scenario in ['normal', 'stress']:
        subset = df_ok[(df_ok['model'] == model) & (df_ok['scenario'] == scenario)]
        if not subset.empty and len(subset) > 1:
            key = f"{model}_{scenario}"
            correlations_scenario[key] = subset[['total_time', 'N', 'V', 'B', 'C_v']].corr()['total_time'].round(4)
