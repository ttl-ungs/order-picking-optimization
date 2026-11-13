"""
Single source of truth for WHICH Split-vs-heuristic comparisons are valid.

Builds one row per comparable unit (a functional instance, or a stress
scenario) with the Split's reference outcome and whether the heuristics'
outcome (feasible vs infeasible) and objective can be compared against it,
with the reason when not. Every comparison table or plot should filter on
these columns instead of re-deciding case by case; see
docs/specs/comparabilidad_split_heuristicas.md for the rules.

- functional: the instances in
  tests/shared_scenarios/functional/functional_instances.json (exported
  from opp_split's functional tests), which opp_aco/opp_hc solve in
  test_case_functional_instances.py as test_instance__<Split test>[__<k>]. Their Split
  objective comes from that file (per instance -- the Split results CSV keeps
  only the last solve of tests that solve more than one instance).
  The OTHER opp_aco/opp_hc functional tests are not comparable with the Split, even
  when they share a test name: most run with one picker where the Split
  test has two (2026-09-28 audit).
- stress: the 19 scenarios of tests/stress_cases, solved by every model (the
  same method names in each model's CSV). opp_split's
  reference outcome comes from its stress CSVs as merged by experiments.common.load
  (04-19 with W_c = 27, 01-03 unchanged scenarios).

Run:

    python -m experiments.comparison.comparability

Writes results/comparability/comparability_split_vs_heuristics.csv (the
registry) and results/comparability/results_split_vs_heuristics.csv (the
registry joined with opp_aco's and opp_hc's latest results: objective, time,
gap and speedup per instance and heuristic -- see build_results).
"""

import os

import pandas as pd

from experiments.common.config import OUTPUTS_ROOT
from experiments.common.load import _extract_instance, _load_sources, _pick_sources
from tests.infra.factories.functional_instances import FIXTURE_PATH, METHOD_PREFIX, _method_names, load_fixtures

OUTPUT_PATH = os.path.join(OUTPUTS_ROOT, "comparability", "comparability_split_vs_heuristics.csv")

COLUMNS = [
    "tier", "split_test", "heuristic_instance", "split_model", "split_status", "split_obj",
    "comparable_status", "comparable_objective", "not_comparable_reason", "source",
]


def functional_rows(fixture_path=FIXTURE_PATH):
    fixtures = load_fixtures(fixture_path)
    rows = []
    for method_name, entry in _method_names(fixtures["instances"]):
        rows.append({
            "tier": "functional",
            "split_test": entry["split_test"],
            "heuristic_instance": method_name,
            "split_model": "opp_split",
            "split_status": entry["split_status"],
            "split_obj": entry["split_obj"],
            "comparable_status": entry["comparable_status"],
            "comparable_objective": entry["comparable_objective"],
            "not_comparable_reason": entry["not_comparable_reason"],
            "source": os.path.basename(fixture_path),
        })
    for name, reason in sorted(fixtures["excluded"].items()):
        rows.append({
            "tier": "functional", "split_test": name, "heuristic_instance": None, "split_model": "opp_split",
            "split_status": None, "split_obj": None, "comparable_status": False, "comparable_objective": False,
            "not_comparable_reason": f"excluido: {reason}", "source": os.path.basename(fixture_path),
        })
    for name in fixtures["not_captured"]:
        rows.append({
            "tier": "functional", "split_test": name, "heuristic_instance": None, "split_model": "opp_split",
            "split_status": None, "split_obj": None, "comparable_status": False, "comparable_objective": False,
            "not_comparable_reason": "el test del Split no llega al solver (rechaza la entrada antes)",
            "source": os.path.basename(fixture_path),
        })
    return rows


def stress_rows():
    sources, _ = _pick_sources("opp_split", "stress")
    split_rows = _load_sources(sources)
    rows = []
    for _, row in split_rows.iterrows():
        instance = _extract_instance(row["test"])
        ok = row["status"] == "ok"
        rows.append({
            "tier": "stress",
            "split_test": instance,
            "heuristic_instance": instance,
            "split_model": "opp_split",
            "split_status": "optimal" if ok else row["status"],
            "split_obj": pd.to_numeric(row["obj_val"], errors="coerce") if ok else None,
            # Same scenario builder call on both sides (verified 2026-09-28).
            # No voluntary waiting to rule out: 04-19 have W_c = 27 >
            # orders per batch (waiting never pays), 01-03 have every order
            # late (no earliness to cut).
            "comparable_status": ok,
            "comparable_objective": ok,
            "not_comparable_reason": "" if ok else "el Split no terminó en 40 min (timeout): no hay referencia",
            "source": row["source_file"],
        })
    return rows


def build_registry():
    return pd.DataFrame(functional_rows() + stress_rows(), columns=COLUMNS)


# --- results joined with the registry ---------------------------------------

HEURISTICS = ["opp_aco", "opp_hc"]

RESULTS_PATH = os.path.join(OUTPUTS_ROOT, "comparability", "results_split_vs_heuristics.csv")

RESULT_COLUMNS = COLUMNS[:-1] + [
    "heuristic", "split_time", "split_time_source",
    "heuristic_obj", "heuristic_time", "heuristic_found_solution", "status_matches",
    "gap_pct", "speedup", "speedup_is_lower_bound", "heuristic_source",
]

# Relative gaps below this are float noise, not a different solution.
GAP_TOLERANCE_PCT = 1e-6


def _seconds(total_time):
    """
    total_time as seconds. A timed-out run stores the text "Ejecución
    detenida por timeout - <minutes>" instead: its limit in seconds is
    returned (a lower bound on the real time), so speedups against a Split
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
        # share the Split's data even when they share its test name.
        df = df[df["instance"].str.startswith(METHOD_PREFIX)]
    return df


def _split_functional_times(registry):
    """
    the Split's time per functional instance, from its functional results CSV.
    That CSV keeps one row per test METHOD (the last solve), so a time is
    only attributable when the method name is unique in the CSV, the
    fixture has a single instance for it, and the CSV's objective matches
    the fixture's; otherwise the time is left empty.
    """
    sources, _ = _pick_sources("opp_split", "functional")
    if not sources:
        return {}
    split_rows = _load_sources(sources)
    unique = split_rows[~split_rows["instance"].duplicated(keep=False)].set_index("instance")
    functional = registry[(registry["tier"] == "functional") & registry["heuristic_instance"].notna()]
    instances_per_test = functional["split_test"].value_counts()
    times = {}
    for _, row in functional.iterrows():
        name = row["split_test"]
        if instances_per_test[name] != 1 or name not in unique.index:
            continue
        split_row = unique.loc[name]
        csv_obj = pd.to_numeric(split_row["obj_val"], errors="coerce")
        same_obj = (pd.isna(csv_obj) and pd.isna(row["split_obj"])) or (
            pd.notna(csv_obj) and pd.notna(row["split_obj"]) and abs(csv_obj - row["split_obj"]) <= 1e-6 * max(1.0, abs(row["split_obj"]))
        )
        if same_obj:
            times[row["heuristic_instance"]] = (_seconds(split_row["total_time"]), split_row["source_file"])
    return times


def build_results(registry):
    """
    The registry joined with each heuristic's latest results (as picked by
    experiments.common.load), one row per (instance, heuristic):

    - heuristic_found_solution: the heuristic reported an objective;
    - status_matches: it found a solution where the Split did and none where the Split
      proved infeasibility (empty when the status isn't comparable);
    - gap_pct: 100 * (heuristic - the Split) / |the Split|, only where the objective is
      comparable (negative = heuristic better);
    - speedup: split_time / heuristic_time, where both times are known (for
      the Split timeouts it's a lower bound, the Split having been cut at its time
      limit: speedup_is_lower_bound).
    """
    split_stress = _load_sources(_pick_sources("opp_split", "stress")[0]).set_index("instance")
    split_functional_times = _split_functional_times(registry)
    rows = []
    for model_dir in HEURISTICS:
        results = {tier: _heuristic_rows(model_dir, tier).set_index("instance") for tier in ("functional", "stress")}
        for _, reg in registry.iterrows():
            instance = reg["heuristic_instance"]
            if pd.isna(instance):
                continue
            row = {c: reg[c] for c in COLUMNS[:-1]}
            row["heuristic"] = model_dir
            if reg["tier"] == "stress" and instance in split_stress.index:
                row["split_time"] = _seconds(split_stress.loc[instance, "total_time"])
                row["split_time_source"] = split_stress.loc[instance, "source_file"]
            elif instance in split_functional_times:
                row["split_time"], row["split_time_source"] = split_functional_times[instance]

            tier_results = results[reg["tier"]]
            if instance in tier_results.index:
                h = tier_results.loc[instance]
                obj = pd.to_numeric(h["obj_val"], errors="coerce")
                row["heuristic_obj"] = obj
                row["heuristic_time"] = _seconds(h["total_time"])
                row["heuristic_source"] = h["source_file"]
                row["heuristic_found_solution"] = pd.notna(obj)
                if reg["comparable_status"]:
                    row["status_matches"] = row["heuristic_found_solution"] == (reg["split_status"] in ("optimal", "feasible"))
                if reg["comparable_objective"] and pd.notna(obj):
                    gap = 100.0 * (obj - reg["split_obj"]) / max(abs(reg["split_obj"]), 1e-9)
                    row["gap_pct"] = 0.0 if abs(gap) < GAP_TOLERANCE_PCT else gap
                if pd.notna(row.get("split_time")) and pd.notna(row["heuristic_time"]) and row["heuristic_time"] > 0:
                    row["speedup"] = row["split_time"] / row["heuristic_time"]
                    row["speedup_is_lower_bound"] = reg["split_status"] == "timeout"
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
