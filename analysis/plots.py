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
    """
    Grouped bar: mean total_time per model, for one scenario. Log-scaled
    (times here span 3+ orders of magnitude, e.g. opp_hc_2's ~0.02s vs
    opp_aco_3's ~1000s -- on a linear axis the fast models are literally
    invisible next to the slow ones). Error bars are one-sided upward only:
    total_time can't be negative, so a symmetric std bar (mean - std) would
    dip below zero whenever std > mean, which happened here and is
    meaningless for a duration.
    """
    sub = time_stats_df[time_stats_df["scenario"] == scenario]
    if sub.empty:
        print(f"[plots] no time_stats data for scenario={scenario}, skipping bar chart.")
        return None

    std = sub["std_time"].fillna(0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(sub["model"], sub["mean_time"], yerr=[[0] * len(sub), std],
           color=PALETTE[: len(sub)], capsize=4)
    ax.set_yscale("log")
    ax.set_ylabel("Tiempo medio (s, escala log)")
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


def plot_quality_gap(
    quality_gap_df, exact_model: str = "opp_v4", file_name: str = "quality_gap.png",
) -> "str | None":
    """
    Grouped bar: mean AND median optimality gap (%) per model (normal
    scenario only so far -- see metrics.quality_gap_table). Showing mean
    alone is actively misleading here: it's pulled way up by a handful of
    outlier instances while the median sits at 0% (more than half the
    matched instances hit the exact optimum). A mean-only chart would
    contradict the mean/median split already called out in the report text.

    exact_model / file_name let this be reused for a different ground-truth
    model (e.g. opp_v5_2_split for the opp_hc_4/opp_aco_4 comparison) without
    clobbering the opp_v4 chart.
    """
    if quality_gap_df.empty:
        print(f"[plots] no quality-gap data yet (need matching {exact_model} + heuristic OK "
              "runs on the same instances), skipping chart.")
        return None

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = range(len(quality_gap_df))
    width = 0.35
    ax.bar([xi - width / 2 for xi in x], quality_gap_df["mean_gap_pct"], width,
           label="media", color=PALETTE[0])
    ax.bar([xi + width / 2 for xi in x], quality_gap_df["median_gap_pct"], width,
           label="mediana", color=PALETTE[1])
    ax.set_xticks(list(x))
    ax.set_xticklabels(
        [f"{m}\n({s})" for m, s in zip(quality_gap_df["model"], quality_gap_df["scenario"])],
        rotation=0,
    )
    ax.set_ylabel(f"Gap vs. {exact_model} (%)")
    ax.set_title(f"Gap de optimalidad vs. {exact_model} (media vs. mediana)")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend()
    fig.tight_layout()
    return _save(fig, file_name)


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


def plot_scatter_time_vs_param(df, model: str, scenario: str, param: str,
                                min_points: int = 3) -> "str | None":
    """Scatter of `param` (e.g. N or V) vs total_time, OK rows only, one model/scenario."""
    sub = df[(df["model"] == model) & (df["scenario"] == scenario) & (df["status"] == "ok")]
    sub = sub.dropna(subset=[param, "total_time"])
    if len(sub) < min_points:
        print(f"[plots] only {len(sub)} OK point(s) for {model}/{scenario} ({param} vs "
              f"total_time) -- need >= {min_points} for a scatter to say anything, skipping.")
        return None

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.scatter(sub[param], sub["total_time"], color=PALETTE[0], alpha=0.75)
    ax.set_xlabel(param)
    ax.set_ylabel("total_time (s)")
    ax.set_title(f"{model} ({scenario}): {param} vs. tiempo total")
    fig.tight_layout()
    return _save(fig, f"scatter_{model}_{scenario}_{param}.png")
