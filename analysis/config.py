"""
Configuration for the model-comparison analysis pipeline.

Generalizes specs/model_analysis.md (originally written for
opp_v3 / opp_hc / opp_aco) to the current model lineup:

- opp_v4    : exact model (ZIMPL + SCIP)               -> ground truth for quality gap
- opp_hc_2  : Hill Climbing, parallel pickers, no congestion
- opp_aco_2 : ACO, parallel pickers, no congestion
- opp_hc_3  : Hill Climbing, congestion-aware
- opp_aco_3 : ACO, congestion-aware, multi-pheromone
- opp_v5    : exact model, 2-stage decomposition (routing then scheduling),
              no congestion -- migrated normal/stress tests neutralize its
              two extra features (heterogeneous picker speed, cold-chain
              limit) via tests/opp_v5/tests/v4_compat.py, so those rows
              solve the same problem as opp_v4/opp_hc_2/opp_aco_2. Kept
              OUT of CONGESTION_AWARE_MODELS and NOT set as EXACT_MODEL
              (still opp_v4) -- it's compared AGAINST opp_v4, not used to
              replace it, until the 2-stage decomposition's optimality is
              independently confirmed.
- opp_hc_4  : Hill Climbing, parallel pickers, opp_v5's two extra features
              (heterogeneous picker speed, cold-chain deadline) plugged
              into a Hill Climbing search instead of a 2-stage exact
              decomposition. No congestion (orthogonal to this model's
              addition, see models/opp_hc_4/opp_hc_4.py header). Most of
              its normal/stress tests are ports of opp_hc_2's (V_p unset /
              T_frio_max default +inf -> pure equivalence, same pattern as
              opp_v5's v4_compat.py), plus a handful of its own that
              actually exercise heterogeneous speeds and a binding
              cold-chain deadline (see tests/opp_hc_4/README.md). Kept OUT
              of CONGESTION_AWARE_MODELS.

Each entry maps a short label -> the directory name under tests/outputs/.
Add/remove entries here as models evolve; nothing else in the pipeline
should need to change.
"""

import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUTS_ROOT = os.path.join(PROJECT_ROOT, "tests", "outputs")
ANALYSIS_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "analysis", "output")

# label -> directory name under tests/outputs/
MODEL_DIRS = {
    "opp_v4": "opp_v4",
    "opp_hc_2": "opp_hc_2",
    "opp_aco_2": "opp_aco_2",
    "opp_hc_3": "opp_hc_3",
    "opp_aco_3": "opp_aco_3",
    "opp_v5": "opp_v5",
    "opp_hc_4": "opp_hc_4",
}

SCENARIOS = ["normal", "stress"]

# The model treated as ground truth for the optimality-gap analysis.
EXACT_MODEL = "opp_v4"

# Models that carry a congestion-aware objective term (obj_val_congestion /
# batch_congestion_wait). Anything not in this list is assumed to NOT model
# congestion at all (opp_hc_2 / opp_aco_2) -- the comparison must say so
# explicitly rather than silently showing an empty column.
CONGESTION_AWARE_MODELS = {"opp_hc_3", "opp_aco_3"}

# Columns that identify an instance's "shape" (used for grouping/correlation).
PARAM_COLUMNS = ["N", "V", "B", "P", "C_v", "W_full", "W_ea_ta", "W_ea", "W_ta"]

# Independent variables for the sensitivity / correlation analysis.
CORRELATION_INDEPENDENTS = ["N", "V", "B", "C_v", "W_full", "W_ea_ta"]

# Hard-coded "latest file" overrides, mirroring the exceptions called out in
# specs/model_analysis.md (e.g. a consolidated file that must win over any
# later partial run, or a specific high-density stress run). Keyed by
# (model_label, scenario) -> exact filename (relative to its output dir).
LATEST_FILE_OVERRIDES = {
    ("opp_v3", "stress"): "complete_output_v3_stress_tests.csv",
    ("opp_aco", "stress"): "output_opp_aco_stress_tests_20260617_123001.csv",
    # 2026-08-28: opp_v4's stress test files were renumbered/reshuffled at
    # some point (the "Rename tests" commit) without a matching full stress
    # re-run under the new numbering. The chronologically NEWER CSV
    # (20260825_194316, 3 rows) tests scenario names
    # (test_25_orders_per_batch_30_batches_25x25, etc.) that don't match ANY
    # current tests/opp_v4/tests/stress/*.py file -- orphaned data from
    # before the rename. This OLDER file's 8 test names match the current
    # suite exactly (test_100_locations, test_infeasible_capacity, ...,
    # test_10_orders_per_batch) -- pin to it explicitly rather than let
    # _pick_csv's recency heuristic (correct in general, wrong here) choose
    # the newer-but-stale one. Still only a partial answer: this file is
    # itself from 2026-08-18 and hasn't been re-run since (the performance
    # fix, the algorithm fixes from the 2026-08-27/28 code audit, etc.
    # postdate it) -- a genuinely fresh, complete opp_v4 stress run is still
    # pending (several of its 8 tests are known to take the full 25min
    # timeout each, so budget hours, not minutes, for that run).
    ("opp_v4", "stress"): "output_opp_v4_stress_tests_20260818_181050.csv",
}
