"""
Single source of truth for WHICH v5-vs-heuristic comparisons are valid.

Builds one row per comparable unit (a functional instance, or a stress
scenario) with v5's reference outcome and whether the heuristics'
outcome (feasible vs infeasible) and objective can be compared against it,
with the reason when not. Every comparison table or plot should filter on
these columns instead of re-deciding case by case; see
docs/specs/comparabilidad_v5_heuristicas.md for the rules.

- functional: the instances in
  tests/shared_scenarios/functional/v5_equivalence_scenarios.json (exported
  from opp_v5_2_split's functional tests), which aco_4/hc_4 solve in
  test_case_v5_equivalence.py as test_v5eq__<v5 test>[__<k>]. Their v5
  objective comes from that file (per instance -- the v5 results CSV keeps
  only the last solve of tests that solve more than one instance).
  The OTHER aco_4/hc_4 functional tests are not comparable with v5, even
  when they share a test name: most run with one picker where the v5
  test has two (2026-09-28 audit).
- stress: the 19 scenarios of tests/opp_v5_2_split/stress (ported to
  aco_4/hc_4 as test_case_v5_*, same test method names). v5_2_split's
  reference outcome comes from its stress CSVs as merged by analysis.load
  (04-19 with W_full = 27, 01-03 unchanged migrated scenarios).

Run:

    python -m analysis.comparability

Writes results/comparability/comparability_v5_vs_heuristics.csv (the
registry) and results/comparability/results_v5_vs_heuristics.csv (the
registry joined with aco_4's and hc_4's latest results: objective, time,
gap and speedup per instance and heuristic -- see build_results).
"""

import os

import pandas as pd

from analysis.config import OUTPUTS_ROOT
from analysis.load import _extract_instance, _load_sources, _pick_sources
from tests.infra.factories.v5_equivalence import FIXTURE_PATH, METHOD_PREFIX, _method_names, load_fixtures

OUTPUT_PATH = os.path.join(OUTPUTS_ROOT, "comparability", "comparability_v5_vs_heuristics.csv")

COLUMNS = [
    "tier", "v5_test", "heuristic_instance", "v5_model", "v5_status", "v5_obj",
    "comparable_status", "comparable_objective", "not_comparable_reason", "source",
]


def functional_rows(fixture_path=FIXTURE_PATH):
    fixtures = load_fixtures(fixture_path)
    rows = []
    for method_name, entry in _method_names(fixtures["instances"]):
        rows.append({
            "tier": "functional",
            "v5_test": entry["v5_test"],
            "heuristic_instance": method_name,
            "v5_model": "opp_v5_2_split",
            "v5_status": entry["v5_status"],
            "v5_obj": entry["v5_obj"],
            "comparable_status": entry["comparable_status"],
            "comparable_objective": entry["comparable_objective"],
            "not_comparable_reason": entry["not_comparable_reason"],
            "source": os.path.basename(fixture_path),
        })
    for name, reason in sorted(fixtures["excluded"].items()):
        rows.append({
            "tier": "functional", "v5_test": name, "heuristic_instance": None, "v5_model": "opp_v5_2_split",
            "v5_status": None, "v5_obj": None, "comparable_status": False, "comparable_objective": False,
            "not_comparable_reason": f"excluido: {reason}", "source": os.path.basename(fixture_path),
        })
    for name in fixtures["not_captured"]:
        rows.append({
            "tier": "functional", "v5_test": name, "heuristic_instance": None, "v5_model": "opp_v5_2_split",
            "v5_status": None, "v5_obj": None, "comparable_status": False, "comparable_objective": False,
            "not_comparable_reason": "el test de v5 no llega al solver (rechaza la entrada antes)",
            "source": os.path.basename(fixture_path),
        })
    return rows


def stress_rows():
    sources, _ = _pick_sources("opp_v5_2_split", "stress")
    v5 = _load_sources(sources)
    rows = []
    for _, row in v5.iterrows():
        instance = _extract_instance(row["test"])
        ok = row["status"] == "ok"
        rows.append({
            "tier": "stress",
            "v5_test": instance,
            "heuristic_instance": instance,
            "v5_model": "opp_v5_2_split",
            "v5_status": "optimal" if ok else row["status"],
            "v5_obj": pd.to_numeric(row["obj_val"], errors="coerce") if ok else None,
            # Same scenario builder call on both sides (verified 2026-09-28).
            # No voluntary waiting to rule out: 04-19 have W_full = 27 >
            # orders per batch (waiting never pays), 01-03 have every order
            # late (no earliness to cut).
            "comparable_status": ok,
            "comparable_objective": ok,
            "not_comparable_reason": "" if ok else "v5 no terminó en 40 min (timeout): no hay referencia",
            "source": row["source_file"],
        })
    return rows


def build_registry():
    return pd.DataFrame(functional_rows() + stress_rows(), columns=COLUMNS)


# --- results joined with the registry ---------------------------------------

HEURISTICS = ["opp_aco_4", "opp_hc_4"]

RESULTS_PATH = os.path.join(OUTPUTS_ROOT, "comparability", "results_v5_vs_heuristics.csv")

RESULT_COLUMNS = COLUMNS[:-1] + [
    "heuristic", "v5_time", "v5_time_source",
    "heuristic_obj", "heuristic_time", "heuristic_found_solution", "status_matches",
    "gap_pct", "speedup", "speedup_is_lower_bound", "heuristic_source",
]

# Relative gaps below this are float noise, not a different solution.
GAP_TOLERANCE_PCT = 1e-6


def _seconds(total_time):
    """
    total_time as seconds. A timed-out run stores the text "Ejecución
    detenida por timeout - <minutes>" instead: its limit in seconds is
    returned (a lower bound on the real time), so speedups against a v5
    timeout are lower bounds.
    """
    value = pd.to_numeric(total_time, errors="coerce")
    if pd.notna(value):
        return float(value)
    if isinstance(total_time, str) and "timeout" in total_time:
        minutes = pd.to_numeric(total_time.rsplit("-", 1)[-1].strip(), errors="coerce")
        return float(minutes) * 60 if pd.notna(minutes) else None
    return None


def _heuristic_rows(model_dir, tier):
    """One row per instance of the heuristic's CSV that the registry covers."""
    sources, _ = _pick_sources(model_dir, tier)
    if not sources:
        return pd.DataFrame(columns=["instance", "obj_val", "total_time", "source_file"])
    df = _load_sources(sources)
    if tier == "functional":
        # Only the equivalence instances: the other functional tests don't
        # share v5's data even when they share its test name.
        df = df[df["instance"].str.startswith(METHOD_PREFIX)]
    return df


def _v5_functional_times(registry):
    """
    v5's time per functional instance, from its functional results CSV.
    That CSV keeps one row per test METHOD (the last solve), so a time is
    only attributable when the method name is unique in the CSV, the
    fixture has a single instance for it, and the CSV's objective matches
    the fixture's; otherwise the time is left empty.
    """
    sources, _ = _pick_sources("opp_v5_2_split", "functional")
    if not sources:
        return {}
    v5 = _load_sources(sources)
    unique = v5[~v5["instance"].duplicated(keep=False)].set_index("instance")
    functional = registry[(registry["tier"] == "functional") & registry["heuristic_instance"].notna()]
    instances_per_test = functional["v5_test"].value_counts()
    times = {}
    for _, row in functional.iterrows():
        name = row["v5_test"]
        if instances_per_test[name] != 1 or name not in unique.index:
            continue
        v5_row = unique.loc[name]
        csv_obj = pd.to_numeric(v5_row["obj_val"], errors="coerce")
        same_obj = (pd.isna(csv_obj) and pd.isna(row["v5_obj"])) or (
            pd.notna(csv_obj) and pd.notna(row["v5_obj"]) and abs(csv_obj - row["v5_obj"]) <= 1e-6 * max(1.0, abs(row["v5_obj"]))
        )
        if same_obj:
            times[row["heuristic_instance"]] = (_seconds(v5_row["total_time"]), v5_row["source_file"])
    return times


def build_results(registry):
    """
    The registry joined with each heuristic's latest results (as picked by
    analysis.load), one row per (instance, heuristic):

    - heuristic_found_solution: the heuristic reported an objective;
    - status_matches: it found a solution where v5 did and none where v5
      proved infeasibility (empty when the status isn't comparable);
    - gap_pct: 100 * (heuristic - v5) / |v5|, only where the objective is
      comparable (negative = heuristic better);
    - speedup: v5_time / heuristic_time, where both times are known (for
      v5 timeouts it's a lower bound, v5 having been cut at its time
      limit: speedup_is_lower_bound).
    """
    v5_stress = _load_sources(_pick_sources("opp_v5_2_split", "stress")[0]).set_index("instance")
    v5_functional_times = _v5_functional_times(registry)
    rows = []
    for model_dir in HEURISTICS:
        results = {tier: _heuristic_rows(model_dir, tier).set_index("instance") for tier in ("functional", "stress")}
        for _, reg in registry.iterrows():
            instance = reg["heuristic_instance"]
            if pd.isna(instance):
                continue
            row = {c: reg[c] for c in COLUMNS[:-1]}
            row["heuristic"] = model_dir
            if reg["tier"] == "stress" and instance in v5_stress.index:
                row["v5_time"] = _seconds(v5_stress.loc[instance, "total_time"])
                row["v5_time_source"] = v5_stress.loc[instance, "source_file"]
            elif instance in v5_functional_times:
                row["v5_time"], row["v5_time_source"] = v5_functional_times[instance]

            tier_results = results[reg["tier"]]
            if instance in tier_results.index:
                h = tier_results.loc[instance]
                obj = pd.to_numeric(h["obj_val"], errors="coerce")
                row["heuristic_obj"] = obj
                row["heuristic_time"] = _seconds(h["total_time"])
                row["heuristic_source"] = h["source_file"]
                row["heuristic_found_solution"] = pd.notna(obj)
                if reg["comparable_status"]:
                    row["status_matches"] = row["heuristic_found_solution"] == (reg["v5_status"] in ("optimal", "feasible"))
                if reg["comparable_objective"] and pd.notna(obj):
                    gap = 100.0 * (obj - reg["v5_obj"]) / max(abs(reg["v5_obj"]), 1e-9)
                    row["gap_pct"] = 0.0 if abs(gap) < GAP_TOLERANCE_PCT else gap
                if pd.notna(row.get("v5_time")) and pd.notna(row["heuristic_time"]) and row["heuristic_time"] > 0:
                    row["speedup"] = row["v5_time"] / row["heuristic_time"]
                    row["speedup_is_lower_bound"] = reg["v5_status"] == "timeout"
            rows.append(row)
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def _summarize_results(results):
    lines = []
    for (tier, model_dir), group in results.groupby(["tier", "heuristic"]):
        comparable = group[group["comparable_objective"] == True]  # noqa: E712
        gaps = comparable["gap_pct"].dropna()
        status = group[group["comparable_status"] == True]  # noqa: E712
        lines.append(
            f"{tier:10} {model_dir:10} status ok {int(status['status_matches'].fillna(False).sum())}/{len(status)}"
            f" | objetivo: {len(gaps)}/{len(comparable)} con resultado, empata {(gaps == 0).sum()},"
            f" mejor {(gaps < 0).sum()}, peor {(gaps > 0).sum()}"
            + (f" (brecha máx. {gaps.max():+.3f}%)" if len(gaps) else "")
        )
    return "\n".join(lines)


def main():
    registry = build_registry()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    registry.to_csv(OUTPUT_PATH, index=False)
    summary = registry.groupby(["tier", "comparable_status", "comparable_objective"]).size()
    print(summary.to_string())
    print(f"\n{len(registry)} filas en {OUTPUT_PATH}")

    results = build_results(registry)
    results.to_csv(RESULTS_PATH, index=False)
    print("\n" + _summarize_results(results))
    print(f"\n{len(results)} filas en {RESULTS_PATH}")


if __name__ == "__main__":
    main()
