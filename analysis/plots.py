"""
Visualizations for the model-comparison report. Each function saves a PNG
under analysis/output/ and returns the path, so run_analysis.py can list
what it produced (and skip / warn on what it couldn't, e.g. no data yet).
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analysis.config import ANALYSIS_OUTPUT_DIR

PALETTE = ["#003366", "#5bc0de", "#5cb85c", "#d9534f", "#e6a817"]


def _save(fig, name: str) -> str:
    os.makedirs(ANALYSIS_OUTPUT_DIR, exist_ok=True)
    path = os.path.join(ANALYSIS_OUTPUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_mean_time_by_scenario(time_stats_df, scenario: str) -> "str | None":
    """Grouped bar: mean total_time per model, for one scenario."""
    sub = time_stats_df[time_stats_df["scenario"] == scenario]
    if sub.empty:
        print(f"[plots] no time_stats data for scenario={scenario}, skipping bar chart.")
        return None

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(sub["model"], sub["mean_time"], yerr=sub["std_time"].fillna(0),
           color=PALETTE[: len(sub)], capsize=4)
    ax.set_ylabel("Tiempo medio (s)")
    ax.set_title(f"Tiempo de ejecución medio -- escenario {scenario}")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    return _save(fig, f"mean_time_{scenario}.png")


def plot_profiling_stacked(profiling_df) -> "str | None":
    """100% stacked bar: solver time vs overhead, per scenario, exact model."""
    if profiling_df.empty:
        print("[plots] no profiling data, skipping stacked bar chart.")
        return None

    fig, ax = plt.subplots(figsize=(6, 4))
    scenarios = profiling_df["scenario"]
    ax.bar(scenarios, profiling_df["solver_ratio_pct"], label="Solver (SCIP optimize)",
           color=PALETTE[0])
    ax.bar(scenarios, profiling_df["overhead_ratio_pct"],
           bottom=profiling_df["solver_ratio_pct"],
           label="Overhead (ZIMPL compile + subprocess/python)", color=PALETTE[3])
    ax.set_ylabel("% de total_time")
    ax.set_title("Profiling del modelo exacto (opp_v4)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return _save(fig, "profiling_exact_model.png")


def plot_quality_gap(quality_gap_df) -> "str | None":
    """Grouped bar: mean optimality gap (%) per model x scenario."""
    if quality_gap_df.empty:
        print("[plots] no quality-gap data yet (need matching opp_v4 + heuristic OK "
              "runs on the same instances), skipping chart.")
        return None

    fig, ax = plt.subplots(figsize=(7, 4.5))
    pivot = quality_gap_df.pivot(index="model", columns="scenario", values="mean_gap_pct")
    pivot.plot.bar(ax=ax, color=PALETTE[: len(pivot.columns)])
    ax.set_ylabel("Gap vs. opp_v4 (%)")
    ax.set_title("Gap de optimalidad de cada heurística vs. el modelo exacto")
    ax.axhline(0, color="black", linewidth=0.8)
    fig.tight_layout()
    return _save(fig, "quality_gap.png")


def plot_congestion_wait(congestion_df) -> "str | None":
    """Bar of mean congestion wait, flagging models that don't model it."""
    if congestion_df.empty:
        print("[plots] no congestion data, skipping chart.")
        return None

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for i, scenario in enumerate(congestion_df["scenario"].unique()):
        sub = congestion_df[congestion_df["scenario"] == scenario]
        offset = (i - 0.5) * 0.35
        x = range(len(sub))
        ax.bar([xi + offset for xi in x], sub["mean_congestion_wait"].fillna(0), width=0.35,
               label=scenario, color=PALETTE[i % len(PALETTE)])
        ax.set_xticks(list(x))
        ax.set_xticklabels(sub["model"], rotation=20)
    ax.set_ylabel("Espera media por congestión")
    ax.set_title("Congestión modelada (0 / NaN => modelo no la mide, no que valga 0)")
    ax.legend()
    fig.tight_layout()
    return _save(fig, "congestion_wait.png")


def plot_scatter_time_vs_param(df, model: str, scenario: str, param: str) -> "str | None":
    """Scatter of `param` (e.g. N or V) vs total_time, OK rows only, one model/scenario."""
    sub = df[(df["model"] == model) & (df["scenario"] == scenario) & (df["status"] == "ok")]
    sub = sub.dropna(subset=[param, "total_time"])
    if sub.empty:
        print(f"[plots] no data for {model}/{scenario} to scatter {param} vs total_time.")
        return None

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.scatter(sub[param], sub["total_time"], color=PALETTE[0], alpha=0.75)
    ax.set_xlabel(param)
    ax.set_ylabel("total_time (s)")
    ax.set_title(f"{model} ({scenario}): {param} vs. tiempo total")
    fig.tight_layout()
    return _save(fig, f"scatter_{model}_{scenario}_{param}.png")
