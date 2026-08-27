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
}
