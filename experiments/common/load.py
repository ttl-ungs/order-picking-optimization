"""
Discovery and loading of the raw per-test CSVs into one tidy DataFrame.

Each row in the output DataFrame is one test execution, tagged with:
- model     : short label from config.MODEL_DIRS
- scenario  : "functional" | "stress"
- instance  : the test *method* name (e.g. "test_basic_two_orders_capacity_limit"),
              used to join the same scenario across models -- unittest method
              names are shared across the models because every model solves the
              same cases (tests/functional_cases, tests/stress_cases)
- source_file: which CSV the row came from, for traceability.

The status/success filter is intentionally NOT applied here, so callers can
still inspect timeouts/failures if they want to.
"""

import os
import re

import pandas as pd

from experiments.common.config import MODEL_DIRS, SCENARIOS, result_csv

NUMERIC_COLUMNS = [
    "total_time",
    "model_time",
    "obj_val",
    "peak_rss_mb",
    "sla_on_time_pct",
    "iterations_run",
    "best_found_at_iteration",
    "N",
    "V",
    "B",
    "P",
    "C_v",
    "W_c",
    "W_pen",
    "W_e",
    "W_t",
]


def load_results(model: str, tier: str) -> pd.DataFrame:
    """Rows of the consolidated CSV of a model and tier (config.result_csv), with
    `instance` and `source_file`. Raises FileNotFoundError if it does not exist."""
    path = result_csv(model, tier)
    df = pd.read_csv(path)
    df["source_file"] = os.path.basename(path)
    df["instance"] = df["test"].map(_extract_instance)
    return df


def _extract_instance(test_id: str) -> str:
    """The unittest *method* name, shared across model variants."""
    if not isinstance(test_id, str):
        return test_id
    return test_id.split(".")[-1]


def case_number(test_id: str) -> str:
    """The two-digit case number of a test id: 'Case24b...' and 'Stress04' give '24' and '04'."""
    match = re.search(r"\b(?:Case|Stress)(\d+)", test_id)
    return match.group(1) if match else ""


def load_all(verbose: bool = True) -> pd.DataFrame:
    """
    Loads the consolidated CSV of every (model, scenario) in config.MODEL_DIRS,
    concatenates them into one tidy frame, and casts the known numeric
    columns. Missing (model, scenario) combinations are skipped and reported,
    not silently ignored.
    """
    frames = []
    missing = []

    for label in MODEL_DIRS:
        for scenario in SCENARIOS:
            if not os.path.exists(result_csv(label, scenario)):
                missing.append((label, scenario))
                continue
            df = load_results(label, scenario)
            df["model"] = label
            df["scenario"] = scenario
            frames.append(df)

    if verbose:
        for label, scenario in missing:
            print(f"[load_all] No CSV found for model={label} scenario={scenario} "
                  f"-- run `python -m tests.run_suite {label} {scenario}` first. Skipping.")

    if not frames:
        return pd.DataFrame()

    df_master = pd.concat(frames, ignore_index=True, sort=False)

    for col in NUMERIC_COLUMNS:
        if col in df_master.columns:
            df_master[col] = pd.to_numeric(df_master[col], errors="coerce")

    return df_master
