"""
Metric computations over the tidy DataFrame produced by analysis.load.load_all().

Sections (mirroring the discussion / docs/specs/model_analysis.md, generalized to
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


def _dedupe_or_flag_collisions(df: pd.DataFrame, key_cols, compare_cols, label: str) -> pd.DataFrame:
    """
    `instance` is just the bare unittest *method* name (see analysis/load.py),
    used to join the same scenario across models/CSVs -- but nothing
    enforces that name is unique. Two rows can share (key_cols) for two
    different reasons that need different handling:
      - benign duplicate: the identical test loaded twice (e.g. from an
        overlapping/leftover CSV) -- same compare_cols values, safe to
        collapse to one row.
      - real collision: two DIFFERENT test methods, defined in different
        test files/classes, that happen to share a method name -- found
        2026-08-28, e.g. opp_hc_2's own stress CSV defines
        "test_10_orders_per_batch_10_x_10" in two files with unrelated
        obj_val/total_time. Merging on the shared name here would silently
        fan out into a comparison against the wrong instance. There's no
        way to tell which of the two is "the real" one from this data
        alone, so both are excluded and reported -- never guessed at.
    """
    key_cols = list(key_cols)
    present_compare = [c for c in compare_cols if c in df.columns]
    if not present_compare or df.empty:
        return df.drop_duplicates(subset=key_cols)

    keep_idx = []
    collided = []
    for key, group in df.groupby(key_cols, dropna=False):
        if len(group) == 1:
            keep_idx.append(group.index[0])
            continue
        identical = all(group[c].nunique(dropna=False) <= 1 for c in present_compare)
        if identical:
            keep_idx.append(group.index[0])
        else:
            collided.append(key if len(key_cols) > 1 else (key,))

    if collided:
        print(f"[{label}] {len(collided)} (scenario, instance) key(s) have rows with "
              f"DIFFERENT {present_compare} under the same test method name -- these are "
              f"two different test scenarios sharing a name across different test files, "
              f"not a benign duplicate. Excluded entirely (can't tell which is 'the real' "
              f"instance -- rename one of the colliding test methods to fix this at the "
              f"source): {collided[:10]}{'...' if len(collided) > 10 else ''}")

    return df.loc[keep_idx]


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


def memory_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mean / std / max peak_rss_mb (peak resident set size, MB) per model x
    scenario, OK cases only. Measures the whole test child process (see
    tests/test_runner.py::_peak_rss_mb), so for exact models this is
    dominated by SCIP's native branch-and-bound memory, not Python
    objects.

    peak_rss_mb was added 2026-09-11 -- a CSV from before that (still the
    "latest" one for some model/scenario until it's re-run) simply won't
    have the column at all, not just empty values, so this returns an
    (empty but correctly-shaped) table for that combination instead of
    raising, same as profiling_table's empty-`sub` guard above.
    """
    ok = _ok(df)
    empty = pd.DataFrame(columns=["model", "scenario", "mean_rss_mb", "std_rss_mb", "max_rss_mb", "n"])
    if "peak_rss_mb" not in ok.columns:
        return empty
    ok = ok.dropna(subset=["peak_rss_mb"])
    if ok.empty:
        return empty
    g = ok.groupby(["model", "scenario"])["peak_rss_mb"]
    out = g.agg(mean_rss_mb="mean", std_rss_mb="std", max_rss_mb="max", n="count")
    return out.reset_index()


def sla_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mean / min sla_on_time_pct (% of orders with tardiness <= 0) per model
    x scenario, OK cases with a recorded SLA value only.

    sla_on_time_pct was added 2026-09-11 -- see memory_table's docstring
    for why a missing column (not just missing values) needs its own guard.
    """
    ok = _ok(df)
    empty = pd.DataFrame(columns=["model", "scenario", "mean_sla_pct", "min_sla_pct", "n"])
    if "sla_on_time_pct" not in ok.columns:
        return empty
    ok = ok.dropna(subset=["sla_on_time_pct"])
    if ok.empty:
        return empty
    g = ok.groupby(["model", "scenario"])["sla_on_time_pct"]
    out = g.agg(mean_sla_pct="mean", min_sla_pct="min", n="count")
    return out.reset_index()


def convergence_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Only meaningful for the 6 Hill Climbing/ACO models (hc_2/3/4,
    aco_2/3/4) -- exact models don't iterate, so their rows simply won't
    have best_found_at_iteration/iterations_run and are absent here, not
    zero. mean_convergence_pct is best_found_at_iteration / iterations_run
    (0% = the initial construction was already the final answer, 100% =
    kept improving until the very last iteration it ran, i.e. likely
    would've kept improving with a bigger budget) -- how much of the
    search was actually useful vs. wasted after convergence, complementing
    the raw iteration counts with a scale-independent number comparable
    across instances with different Max_it.
    """
    ok = _ok(df)
    empty = pd.DataFrame(columns=[
        "model", "scenario", "mean_iterations_run", "mean_best_found_at_iteration",
        "mean_convergence_pct", "n",
    ])
    needed = {"iterations_run", "best_found_at_iteration"}
    if not needed.issubset(ok.columns):
        return empty
    ok = ok.dropna(subset=list(needed))
    if ok.empty:
        return empty

    ok = ok.copy()
    # iterations_run == 0 only for a solve that never entered its main
    # loop (e.g. failed before iterating) -- shouldn't reach an "ok" row,
    # but guard the division anyway rather than propagate a divide-by-zero.
    ok["convergence_pct"] = np.where(
        ok["iterations_run"] > 0,
        ok["best_found_at_iteration"] / ok["iterations_run"] * 100,
        np.nan,
    )

    g = ok.groupby(["model", "scenario"])
    out = pd.DataFrame({
        "mean_iterations_run": g["iterations_run"].mean(),
        "mean_best_found_at_iteration": g["best_found_at_iteration"].mean(),
        "mean_convergence_pct": g["convergence_pct"].mean(),
        "n": g["iterations_run"].count(),
    })
    return out.reset_index()


def stability_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates analysis.load.load_stability()'s per-(model, instance, seed)
    rows into mean/std/best/worst/gap_best_worst_pct per (model, instance) --
    how much a single heuristic's OWN randomness moves obj_val across seeds
    for the exact same instance, distinct from quality_gap_table (accuracy
    vs. the exact model). success_rate_pct uses ALL rows (not just "optimal"/
    "feasible" ones) as the denominator, same reasoning as
    success_rate_table: a seed that comes back infeasible must count against
    the model, not be silently dropped before the mean/std are computed.

    gap_best_worst_pct is (worst - best) / best * 100 -- 0% means every seed
    landed on the exact same obj_val (perfectly repeatable for this
    instance); this is undefined (NaN) when there isn't at least one row
    with a numeric obj_val (e.g. every seed came back infeasible).
    """
    empty = pd.DataFrame(columns=[
        "model", "instance", "n_seeds", "n_ok", "success_rate_pct",
        "mean_obj_val", "std_obj_val", "best_obj_val", "worst_obj_val",
        "gap_best_worst_pct",
    ])
    if df.empty:
        return empty

    g = df.groupby(["model", "instance"])
    out = g["seed"].count().rename("n_seeds").to_frame()
    out["n_ok"] = g["obj_val"].apply(lambda s: s.notna().sum())
    out["success_rate_pct"] = (out["n_ok"] / out["n_seeds"] * 100).round(1)

    ok_obj = df.dropna(subset=["obj_val"]).groupby(["model", "instance"])["obj_val"]
    out["mean_obj_val"] = ok_obj.mean().round(2)
    out["std_obj_val"] = ok_obj.std().round(2)
    out["best_obj_val"] = ok_obj.min()
    out["worst_obj_val"] = ok_obj.max()
    out["gap_best_worst_pct"] = np.where(
        out["best_obj_val"] > 0,
        (out["worst_obj_val"] - out["best_obj_val"]) / out["best_obj_val"] * 100,
        np.nan,
    )
    out["gap_best_worst_pct"] = out["gap_best_worst_pct"].round(2)
    return out.reset_index()


def profiling_table(df: pd.DataFrame, exact_model: str = EXACT_MODEL) -> pd.DataFrame:
    """
    For the exact model only: what share of total_time is spent inside the
    solver (`model_time`, i.e. pyscipopt model.optimize()) vs everything else
    (ZIMPL compilation, subprocess/python overhead). Mirrors the "90% modeling
    time" hypothesis from docs/specs/model_analysis.md, adapted to opp_v4's
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


# Columns that must match between a heuristic row and the exact-model row for
# the same (scenario, instance) before their obj_val's are comparable at all.
# Same *test method name* does NOT guarantee the same instance: e.g.
# opp_hc_2/opp_aco_2's test_basic_two_orders_capacity_limit never sets a
# picker set and falls back to a single implicit picker (P=1), while
# opp_v4's own scenario_01 (same method name) bakes P={"P1","P2"} into the
# scenario builder -- same weights, same N/V/B, but a fundamentally
# different parallelism structure, giving wildly different objective values
# (~744 vs ~30 for that instance) that have nothing to do with solution
# quality. Verified empirically before adding this guard -- don't remove it
# without re-checking that assumption.
SHAPE_COLUMNS = ["N", "V", "B", "P", "C_v"]


def quality_gap_table(
    df: pd.DataFrame, exact_model: str = EXACT_MODEL, heuristic_models=None,
) -> pd.DataFrame:
    """
    Optimality gap of every heuristic model vs the exact model, computed only
    on instances (scenario, instance) where BOTH the exact model and the
    heuristic converged ("ok") AND the instance shape actually matches
    (SHAPE_COLUMNS) -- same test method name is not sufficient, see above.
    Rows excluded for either reason are counted and reported, never dropped
    silently.

    heuristic_models: optional iterable restricting which non-exact models are
    compared (default: every model in df other than exact_model). Used e.g.
    to compare opp_hc_4/opp_aco_4 against opp_v5 specifically -- they're the
    only heuristics sharing opp_v5's extra features (picker speed, cold
    chain), so comparing the rest (opp_hc_2/3, opp_aco_2/3) against opp_v5
    would silently mix in instances that were never solved under the same
    problem definition.
    """
    ok = _ok(df)
    shape_cols_present = [c for c in SHAPE_COLUMNS if c in ok.columns]
    exact_cols = ["scenario", "instance", "obj_val"] + shape_cols_present
    exact = ok[ok["model"] == exact_model][exact_cols].copy()
    exact = _dedupe_or_flag_collisions(
        exact, key_cols=["scenario", "instance"], compare_cols=["obj_val"] + shape_cols_present,
        label=f"quality_gap_table:{exact_model}",
    )
    exact = exact.rename(columns={"obj_val": "obj_val_exact",
                                   **{c: f"{c}_exact" for c in shape_cols_present}})

    heuristics = ok[ok["model"] != exact_model]
    if heuristic_models is not None:
        heuristics = heuristics[heuristics["model"].isin(heuristic_models)]
    heuristics = _dedupe_or_flag_collisions(
        heuristics, key_cols=["model", "scenario", "instance"],
        compare_cols=["obj_val"] + shape_cols_present, label="quality_gap_table:heuristics",
    )
    merged = heuristics.merge(exact, on=["scenario", "instance"], how="left")

    no_exact_run = merged[merged["obj_val_exact"].isna()]
    if not no_exact_run.empty:
        print(f"[quality_gap_table] {len(no_exact_run)} heuristic rows have no matching "
              f"'{exact_model}' OK result for the same (scenario, instance) -- "
              f"excluded from the gap computation (exact model likely timed out "
              f"or that instance/scenario hasn't been run for {exact_model} yet).")

    candidates = merged.dropna(subset=["obj_val_exact", "obj_val"]).copy()

    shape_ok = pd.Series(True, index=candidates.index)
    for c in shape_cols_present:
        shape_ok &= candidates[c] == candidates[f"{c}_exact"]

    shape_mismatch = candidates[~shape_ok]
    if not shape_mismatch.empty:
        print(f"[quality_gap_table] {len(shape_mismatch)} rows excluded: same test method "
              f"name as an {exact_model} row, but a different instance shape "
              f"({', '.join(shape_cols_present)}) -- their obj_val's aren't comparable. "
              f"Affected instances: {sorted(shape_mismatch['instance'].unique())[:10]}"
              f"{'...' if shape_mismatch['instance'].nunique() > 10 else ''}")

    matched = candidates[shape_ok].copy()
    matched["gap_pct"] = (
        (matched["obj_val"] - matched["obj_val_exact"]) / matched["obj_val_exact"] * 100
    )

    g = matched.groupby(["model", "scenario"])["gap_pct"]
    out = g.agg(mean_gap_pct="mean", median_gap_pct="median",
                std_gap_pct="std", max_gap_pct="max", n_matched="count")
    return out.reset_index()


def congestion_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mean congestion wait (obj_val_congestion, a DURATION) and mean/max
    collision count (congestion_collisions, a FREQUENCY -- how often two
    pickers actually contended for the same node/edge, see
    models/utils/congestion.py::CongestionTracker.total_collisions) per
    model x scenario, OK cases only. Models outside CONGESTION_AWARE_MODELS
    (opp_hc_2 / opp_aco_2) never measured either at all -- they show up
    with n=0 / NaN, and that absence is itself the point: these are the
    metrics their v3 counterparts add.
    """
    ok = _ok(df)
    if "obj_val_congestion" not in ok.columns:
        ok["obj_val_congestion"] = np.nan
    if "congestion_collisions" not in ok.columns:
        ok["congestion_collisions"] = np.nan

    g = ok.groupby(["model", "scenario"])
    out = pd.DataFrame({
        "mean_congestion_wait": g["obj_val_congestion"].mean(),
        "std_congestion_wait": g["obj_val_congestion"].std(),
        "max_congestion_wait": g["obj_val_congestion"].max(),
        "mean_collisions": g["congestion_collisions"].mean(),
        "max_collisions": g["congestion_collisions"].max(),
        "n": g["obj_val_congestion"].count(),
    })
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
        a = _dedupe_or_flag_collisions(
            a, key_cols=["scenario", "instance"], compare_cols=["total_time", "obj_val"],
            label=f"congestion_reduction_table:{aware}",
        )
        b = _dedupe_or_flag_collisions(
            b, key_cols=["scenario", "instance"], compare_cols=["total_time", "obj_val"],
            label=f"congestion_reduction_table:{baseline}",
        )
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

    level="global"   -> one row per model, pooling functional+stress.
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
