"""
CLI entrypoint for the model-comparison analysis pipeline.

Usage:
    python -m analysis.run_analysis

Reads the latest CSVs under tests/outputs/<model>/<normal|stress>/ for every
model in analysis.config.MODEL_DIRS, computes the six metric tables, saves
the charts under analysis/output/, and writes a consolidated
analysis/output/report.md.

This does NOT run the test suites itself -- generate the CSVs first with
each model's execute_tests.py (see each tests/<model>/execute_tests.py),
then run this script.
"""

import os

import pandas as pd

from analysis.config import ANALYSIS_OUTPUT_DIR, EXACT_MODEL
from analysis.load import load_all
from analysis.metrics import (
    congestion_reduction_table,
    congestion_table,
    correlation_table,
    memory_table,
    profiling_table,
    quality_gap_table,
    sla_table,
    success_rate_table,
    time_stats_table,
)
from analysis.plots import (
    plot_congestion_wait,
    plot_mean_time_by_scenario,
    plot_profiling_stacked,
    plot_quality_gap,
    plot_scatter_time_vs_param,
)


def _md_table(df: pd.DataFrame) -> str:
    """Minimal GFM table writer -- avoids depending on the optional `tabulate`
    package just for this."""
    if df.empty:
        return "_(sin datos)_\n"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def main():
    df = load_all()
    if df.empty:
        print("No se encontró ningún CSV en tests/outputs/. Corré primero los "
              "execute_tests.py de cada modelo (opp_v4, opp_hc_2, opp_aco_2, "
              "opp_hc_3, opp_aco_3).")
        return

    success = success_rate_table(df)
    times = time_stats_table(df)
    memory = memory_table(df)
    sla = sla_table(df)
    profiling = profiling_table(df, exact_model=EXACT_MODEL)
    quality_gap = quality_gap_table(df, exact_model=EXACT_MODEL)
    congestion = congestion_table(df)
    congestion_overhead = congestion_reduction_table(df)
    corr_global = correlation_table(df, level="global")
    corr_scenario = correlation_table(df, level="scenario")

    charts = []
    for scenario in ("normal", "stress"):
        charts.append(plot_mean_time_by_scenario(times, scenario))
    charts.append(plot_profiling_stacked(profiling))
    charts.append(plot_quality_gap(quality_gap))
    charts.append(plot_congestion_wait(congestion))
    # opp_v4 stress isn't included here: it only ever has 1 OK point (see
    # analysis/README.md), and plot_scatter_time_vs_param already skips
    # anything under 3 points rather than draw a one-dot "scatter".
    charts.append(plot_scatter_time_vs_param(df, model="opp_hc_2", scenario="stress", param="N"))
    charts.append(plot_scatter_time_vs_param(df, model="opp_aco_2", scenario="stress", param="V"))
    charts.append(plot_scatter_time_vs_param(df, model="opp_hc_3", scenario="stress", param="V"))
    charts.append(plot_scatter_time_vs_param(df, model="opp_aco_3", scenario="stress", param="N"))
    charts = [c for c in charts if c]

    os.makedirs(ANALYSIS_OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(ANALYSIS_OUTPUT_DIR, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Reporte de comparación de modelos\n\n")

        f.write("## 1. Tasa de éxito / convergencia\n\n")
        f.write(_md_table(success))

        f.write("\n## 2. Tiempo de ejecución (solo casos OK)\n\n")
        f.write(_md_table(times))

        f.write("\n## 2.1 Memoria pico (RAM, MB, solo casos OK)\n\n")
        f.write(_md_table(memory))

        f.write("\n## 2.2 Nivel de servicio (% de órdenes sin tardanza, solo casos con dato)\n\n")
        f.write(_md_table(sla))

        f.write("\n## 3. Profiling del modelo exacto (opp_v4)\n\n")
        f.write(_md_table(profiling))

        f.write("\n## 4. Gap de optimalidad vs. opp_v4\n\n")
        f.write(_md_table(quality_gap))

        f.write("\n## 5. Congestión (opp_hc_3 / opp_aco_3 vs. sus baselines v2)\n\n")
        f.write("### 5.1 Espera media por congestión\n\n")
        f.write(_md_table(congestion))
        f.write("\n### 5.2 Sobrecosto de tiempo por modelar congestión\n\n")
        f.write(_md_table(congestion_overhead))

        f.write("\n## 6. Sensibilidad paramétrica (correlación de Pearson con total_time)\n\n")
        f.write("### 6.1 Nivel global (normal + estrés)\n\n")
        f.write(_md_table(corr_global))
        f.write("\n### 6.2 Nivel escenario\n\n")
        f.write(_md_table(corr_scenario))

        f.write("\n## Gráficos generados\n\n")
        for c in charts:
            f.write(f"- `{os.path.relpath(c, ANALYSIS_OUTPUT_DIR)}`\n")

    print(f"Reporte escrito en {report_path}")
    print(f"{len(charts)} gráficos guardados en {ANALYSIS_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
