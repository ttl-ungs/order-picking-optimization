"""
Metric computations over the tidy DataFrame produced by analysis.load.load_all().

Sections (mirroring the discussion / specs/model_analysis.md, generalized to
opp_v4 / opp_hc_2 / opp_aco_2 / opp_hc_3 / opp_aco_3):

1. success_rate_table   -- feasibility / convergence rate per model x scenario
2. time_stats_table     -- mean/std/max total_time (OK cases only)
3. profiling_table      -- solver-time share vs total overhead, exact model only
4. quality_gap_table    -- optimality gap of each heuristic vs opp_v4 (obj_val)
5. congestion_table     -- congestion wait comparison (hc_3/aco_3 vs hc_2/aco_2)
6. correlation_table    -- Pearson r of total_time vs instance-shape params,
                           at "global" and "scenario" levels
"""

import numpy as np
import pandas as pd

from analysis.config import CONGESTION_AWARE_MODELS, CORRELATION_INDEPENDENTS, EXACT_MODEL


def _ok(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["status"] == "ok"].copy()


def success_rate_table(df: pd.DataFrame) -> pd.DataFrame:
    """Total / OK / success rate per model x scenario, using ALL rows
    (timeouts and failures must count towards the denominator)."""
    g = df.groupby(["model", "scenario"])
    out = g["status"].count().rename("total").to_frame()
    out["ok"] = g["status"].apply(lambda s: (s == "ok").sum())
    out["timeout"] = g["status"].apply(lambda s: (s == "timeout").sum())
    out["failed"] = g["status"].apply(lambda s: (s == "failed").sum())
    out["success_rate_pct"] = (out["ok"] / out["total"] * 100).round(1)
    return out.reset_index()


def time_stats_table(df: pd.DataFrame) -> pd.DataFrame:
    """Mean / std / max total_time per model x scenario, OK cases only."""
    ok = _ok(df)
    g = ok.groupby(["model", "scenario"])["total_time"]
    out = g.agg(mean_time="mean", std_time="std", max_time="max", n="count")
    return out.reset_index()


def profiling_table(df: pd.DataFrame, exact_model: str = EXACT_MODEL) -> pd.DataFrame:
    """
    For the exact model only: what share of total_time is spent inside the
    solver (`model_time`, i.e. pyscipopt model.optimize()) vs everything else
    (ZIMPL compilation, subprocess/python overhead). Mirrors the "90% modeling
    time" hypothesis from specs/model_analysis.md, adapted to opp_v4's
    solve_zpl() split (there model_time == pure SCIP optimize time).
    """
    ok = _ok(df)
    sub = ok[ok["model"] == exact_model].copy()
    if sub.empty:
        return pd.DataFrame(columns=["scenario", "mean_total_time", "mean_solver_time",
                                      "solver_ratio_pct", "overhead_ratio_pct", "n"])
    g = sub.groupby("scenario")
    out = pd.DataFrame({
        "mean_total_time": g["total_time"].mean(),
        "mean_solver_time": g["model_time"].mean(),
        "n": g["total_time"].count(),
    })
    out["solver_ratio_pct"] = (out["mean_solver_time"] / out["mean_total_time"] * 100).round(1)
    out["overhead_ratio_pct"] = (100 - out["solver_ratio_pct"]).round(1)
    return out.reset_index()


def quality_gap_table(df: pd.DataFrame, exact_model: str = EXACT_MODEL) -> pd.DataFrame:
    """
    Optimality gap of every heuristic model vs the exact model, computed only
    on instances (scenario, instance) where BOTH the exact model and the
    heuristic converged ("ok"). Rows the exact model didn't solve (timeout on
    larger stress instances) are reported as excluded, not dropped silently.
    """
    ok = _ok(df)
    exact = ok[ok["model"] == exact_model][["scenario", "instance", "obj_val"]]
    exact = exact.rename(columns={"obj_val": "obj_val_exact"})

    heuristics = ok[ok["model"] != exact_model]
    merged = heuristics.merge(exact, on=["scenario", "instance"], how="left")

    matched = merged.dropna(subset=["obj_val_exact", "obj_val"]).copy()
    matched["gap_pct"] = (
        (matched["obj_val"] - matched["obj_val_exact"]) / matched["obj_val_exact"] * 100
    )

    unmatched = merged[merged["obj_val_exact"].isna()]
    if not unmatched.empty:
        n_unmatched = len(unmatched)
        print(f"[quality_gap_table] {n_unmatched} heuristic rows have no matching "
              f"'{exact_model}' OK result for the same (scenario, instance) -- "
              f"excluded from the gap computation (exact model likely timed out "
              f"or that instance/scenario hasn't been run for {exact_model} yet).")

    g = matched.groupby(["model", "scenario"])["gap_pct"]
    out = g.agg(mean_gap_pct="mean", std_gap_pct="std", max_gap_pct="max", n_matched="count")
    return out.reset_index()


def congestion_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mean congestion wait (obj_val_congestion) per model x scenario, OK cases
    only. Models outside CONGESTION_AWARE_MODELS (opp_hc_2 / opp_aco_2) never
    measured this at all -- they show up with n=0 / NaN, and that absence is
    itself the point: it's the metric their v3 counterparts add.
    """
    ok = _ok(df)
    if "obj_val_congestion" not in ok.columns:
        ok["obj_val_congestion"] = np.nan

    g = ok.groupby(["model", "scenario"])["obj_val_congestion"]
    out = g.agg(mean_congestion_wait="mean", std_congestion_wait="std",
                max_congestion_wait="max", n="count")
    out = out.reset_index()
    out["congestion_modeled"] = out["model"].isin(CONGESTION_AWARE_MODELS)
    return out


def congestion_reduction_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pairs each congestion-aware model with its v2 baseline (hc_3 vs hc_2,
    aco_3 vs aco_2) and reports total_time delta on matched instances -- i.e.
    the runtime price paid for modeling congestion, since hc_2/aco_2 can't be
    compared on the congestion metric itself (they don't compute it).
    """
    pairs = {"opp_hc_3": "opp_hc_2", "opp_aco_3": "opp_aco_2"}
    ok = _ok(df)
    rows = []
    for aware, baseline in pairs.items():
        a = ok[ok["model"] == aware][["scenario", "instance", "total_time", "obj_val"]]
        b = ok[ok["model"] == baseline][["scenario", "instance", "total_time", "obj_val"]]
        m = a.merge(b, on=["scenario", "instance"], suffixes=("_aware", "_baseline"))
        if m.empty:
            print(f"[congestion_reduction_table] no matched instances for "
                  f"{aware} vs {baseline} yet.")
            continue
        m["time_overhead_pct"] = (
            (m["total_time_aware"] - m["total_time_baseline"]) / m["total_time_baseline"] * 100
        )
        g = m.groupby("scenario")["time_overhead_pct"]
        summary = g.agg(mean_time_overhead_pct="mean", n_matched="count").reset_index()
        summary["aware_model"] = aware
        summary["baseline_model"] = baseline
        rows.append(summary)
    if not rows:
        return pd.DataFrame(columns=["scenario", "mean_time_overhead_pct", "n_matched",
                                      "aware_model", "baseline_model"])
    return pd.concat(rows, ignore_index=True)


def correlation_table(df: pd.DataFrame, level: str = "global") -> pd.DataFrame:
    """
    Pearson r of total_time against CORRELATION_INDEPENDENTS.

    level="global"   -> one row per model, pooling normal+stress.
    level="scenario" -> one row per (model, scenario).
    """
    ok = _ok(df)
    cols = ["total_time"] + CORRELATION_INDEPENDENTS
    cols = [c for c in cols if c in ok.columns]

    group_keys = ["model"] if level == "global" else ["model", "scenario"]
    rows = []
    for key, sub in ok.groupby(group_keys):
        sub = sub[cols].dropna()
        if len(sub) < 2:
            continue
        corr = sub.corr(numeric_only=True)["total_time"].drop("total_time")
        row = dict(zip(group_keys, key if isinstance(key, tuple) else (key,)))
        row.update(corr.round(4).to_dict())
        row["n"] = len(sub)
        rows.append(row)
    return pd.DataFrame(rows)
