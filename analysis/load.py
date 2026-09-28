"""
Discovery and loading of the raw per-test CSVs into one tidy DataFrame.

Each row in the output DataFrame is one test execution, tagged with:
- model     : short label from config.MODEL_DIRS
- scenario  : "functional" | "stress"
- instance  : the test *method* name (e.g. "test_basic_two_orders_capacity_limit"),
              used to join the same scenario across models -- unittest method
              names are shared across model variants because they exercise the
              same scenario file (see tests/opp_v4/scenarios vs
              tests/opp_hc_2/scenarios, etc.)
- source_file: which CSV the row came from, for traceability.

Numeric casting and the status/success filter are intentionally NOT applied
here -- that belongs to metrics.py, so callers can still inspect timeouts/
failures if they want to.
"""

import glob
import os
import re

import pandas as pd

from analysis.config import (
    LATEST_FILE_OVERRIDES,
    MODEL_DIRS,
    OUTPUTS_ROOT,
    SCENARIOS,
    STABILITY_MODELS,
)

_RUN_TIMESTAMP_RE = re.compile(r"(\d{8}_\d{6})")

NUMERIC_COLUMNS = [
    "total_time",
    "model_time",
    "solver_time",
    "obj_val",
    "obj_val_congestion",
    "congestion_collisions",
    "peak_rss_mb",
    "sla_on_time_pct",
    "iterations_run",
    "best_found_at_iteration",
    "N",
    "V",
    "B",
    "P",
    "C_v",
    "W_full",
    "W_ea_ta",
    "W_ea",
    "W_ta",
]


def _run_timestamp_key(path: str) -> str:
    """
    Extracts the "YYYYMMDD_HHMMSS" run timestamp embedded in a CSV's own
    filename.
    """
    match = _RUN_TIMESTAMP_RE.search(os.path.basename(path))
    if match:
        return match.group(1)
    return str(os.path.getmtime(path))


def _pick_csv(model_dir: str, scenario: str) -> "tuple[str, list[str]]":
    """
    Returns (chosen_path, dropped_paths). Honors LATEST_FILE_OVERRIDES;
    otherwise picks the CSV whose filename encodes the most recent run
    timestamp (see _run_timestamp_key), and reports every other candidate
    as dropped so a caller can log what was skipped (never silently
    discard data without saying so).
    """
    pattern = os.path.join(OUTPUTS_ROOT, model_dir, scenario, "*.csv")
    candidates = glob.glob(pattern)
    if not candidates:
        return None, []

    override = LATEST_FILE_OVERRIDES.get((model_dir, scenario))
    if isinstance(override, list):
        raise ValueError(f"{(model_dir, scenario)} has a multi-source override: use _pick_sources")
    if override:
        forced = os.path.join(OUTPUTS_ROOT, model_dir, scenario, override)
        if os.path.exists(forced):
            return forced, [c for c in candidates if c != forced]

    chosen = max(candidates, key=_run_timestamp_key)
    return chosen, [c for c in candidates if c != chosen]


def _pick_sources(model_dir: str, scenario: str) -> "tuple[list[tuple[str, object]], list[str]]":
    """
    Like _pick_csv, but returns a list of (path, instances-or-None) sources
    to merge (see LATEST_FILE_OVERRIDES' list form in analysis/config.py).
    A plain filename override or no override gives a single source with no
    instance filter, exactly _pick_csv's choice. A listed file that doesn't
    exist raises, instead of silently dropping its rows.
    """
    override = LATEST_FILE_OVERRIDES.get((model_dir, scenario))
    if not isinstance(override, list):
        path, dropped = _pick_csv(model_dir, scenario)
        return ([(path, None)] if path else []), dropped

    sources = []
    for entry in override:
        filename, instances = (entry, None) if isinstance(entry, str) else entry
        path = os.path.join(OUTPUTS_ROOT, model_dir, scenario, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"LATEST_FILE_OVERRIDES[{(model_dir, scenario)}] lists missing file {path}")
        sources.append((path, set(instances) if instances is not None else None))
    used = {path for path, _ in sources}
    dropped = [c for c in glob.glob(os.path.join(OUTPUTS_ROOT, model_dir, scenario, "*.csv")) if c not in used]
    return sources, dropped


def _load_sources(sources) -> pd.DataFrame:
    """Rows of every source, filtered to its instances; an instance keeps only its first source's rows."""
    frames = []
    seen = set()
    for path, instances in sources:
        df = pd.read_csv(path)
        df["source_file"] = os.path.basename(path)
        df["instance"] = df["test"].map(_extract_instance)
        if instances is not None:
            df = df[df["instance"].isin(instances)]
        df = df[~df["instance"].isin(seen)]
        seen.update(df["instance"])
        frames.append(df)
    return pd.concat(frames, ignore_index=True, sort=False)


def _extract_instance(test_id: str) -> str:
    """The unittest *method* name, shared across model variants."""
    if not isinstance(test_id, str):
        return test_id
    return test_id.split(".")[-1]


def load_all(verbose: bool = True) -> pd.DataFrame:
    """
    Loads the latest CSV per (model, scenario) declared in config.MODEL_DIRS,
    concatenates them into one tidy frame, and casts the known numeric
    columns. Missing (model, scenario) combinations are skipped and reported,
    not silently ignored.
    """
    frames = []
    missing = []
    dropped_report = []

    for label, model_dir in MODEL_DIRS.items():
        for scenario in SCENARIOS:
            sources, dropped = _pick_sources(model_dir, scenario)
            if not sources:
                missing.append((label, scenario))
                continue
            if dropped:
                dropped_report.append((label, scenario, [path for path, _ in sources], dropped))

            df = _load_sources(sources)
            df["model"] = label
            df["scenario"] = scenario
            frames.append(df)

    if verbose:
        for label, scenario in missing:
            print(f"[load_all] No CSV found for model={label} scenario={scenario} "
                  f"-- run `python -m tests.run_suite {label} {scenario}` first. Skipping.")
        for label, scenario, chosen, dropped in dropped_report:
            print(f"[load_all] model={label} scenario={scenario}: using "
                  f"{[os.path.basename(c) for c in chosen]}, ignoring {len(dropped)} other run(s): "
                  f"{[os.path.basename(d) for d in dropped]}")

    if not frames:
        return pd.DataFrame()

    df_master = pd.concat(frames, ignore_index=True, sort=False)

    for col in NUMERIC_COLUMNS:
        if col in df_master.columns:
            df_master[col] = pd.to_numeric(df_master[col], errors="coerce")

    return df_master


def load_stability(verbose: bool = True) -> pd.DataFrame:
    """
    Loads the latest seed-stability CSV (analysis/run_stability_study.py) per
    heuristic model in STABILITY_MODELS, from results/<model>/stability/.

    Separate from load_all() because the schema is different: one row per
    (instance, seed) solve of a SHARED instance (tests/shared_scenarios/
    instances.py), not one row per unittest test method -- there's no
    "scenario" (functional/stress) dimension, and "instance" here means one of
    the 3 shared instances, not a test method name.
    """
    frames = []
    missing = []
    dropped_report = []

    for label in STABILITY_MODELS:
        model_dir = MODEL_DIRS[label]
        path, dropped = _pick_csv(model_dir, "stability")
        if path is None:
            missing.append(label)
            continue
        if dropped:
            dropped_report.append((label, path, dropped))

        df = pd.read_csv(path)
        df["model"] = label
        df["source_file"] = os.path.basename(path)
        frames.append(df)

    if verbose:
        for label in missing:
            print(f"[load_stability] No stability CSV found for model={label} -- "
                  f"run analysis/run_stability_study.py first. Skipping.")
        for label, chosen, dropped in dropped_report:
            print(f"[load_stability] model={label}: using {os.path.basename(chosen)}, "
                  f"ignoring {len(dropped)} older run(s): "
                  f"{[os.path.basename(d) for d in dropped]}")

    if not frames:
        return pd.DataFrame()

    df_master = pd.concat(frames, ignore_index=True, sort=False)
    for col in ("seed", "obj_val", "elapsed"):
        if col in df_master.columns:
            df_master[col] = pd.to_numeric(df_master[col], errors="coerce")

    return df_master
