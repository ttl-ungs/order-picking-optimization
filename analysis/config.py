"""
Configuration for the model-comparison analysis pipeline.

Generalizes docs/specs/model_analysis.md (originally written for
opp_v3 / opp_hc_1 / opp_aco_1) to the current model lineup:

- opp_v4    : exact model (ZIMPL + SCIP)               -> ground truth for quality gap
- opp_hc_2  : Hill Climbing, parallel pickers, no congestion
- opp_aco_2 : ACO, parallel pickers, no congestion
- opp_hc_3  : Hill Climbing, congestion-aware
- opp_aco_3 : ACO, congestion-aware, multi-pheromone
- opp_v5_1_mono : exact model, the same problem as opp_v5_2_split (heterogeneous picker
              speed + cold chain) solved as ONE monolithic MIP instead of two stages;
              tested with the same suites as opp_v5_2_split.
- opp_v5_2_split    : exact model, 2-stage decomposition (routing then scheduling),
              no congestion -- migrated normal/stress tests neutralize its
              two extra features (heterogeneous picker speed, cold-chain
              limit) via tests/infra/factories/migrated_case.py, so those rows
              solve the same problem as opp_v4/opp_hc_2/opp_aco_2. Kept
              OUT of CONGESTION_AWARE_MODELS and NOT set as EXACT_MODEL
              (still opp_v4) -- it's compared AGAINST opp_v4, not used to
              replace it, until the 2-stage decomposition's optimality is
              independently confirmed.
- opp_hc_4  : Hill Climbing, parallel pickers, opp_v5_2_split's two extra features
              (heterogeneous picker speed, cold-chain deadline) plugged
              into a Hill Climbing search instead of a 2-stage exact
              decomposition. No congestion (orthogonal to this model's
              addition, see models/opp_hc_4/opp_hc_4.py header). Most of
              its normal/stress tests are ports of opp_hc_2's (V_p unset /
              T_frio_max default +inf -> pure equivalence, same pattern as
              opp_v5_2_split's migrated_case.py), plus a handful of its own that
              actually exercise heterogeneous speeds and a binding
              cold-chain deadline (see tests/opp_hc_4/README.md). Kept OUT
              of CONGESTION_AWARE_MODELS.
- opp_aco_4 : ACO counterpart of opp_hc_4 - same two extra features
              (heterogeneous picker speed, cold-chain deadline) plugged
              into opp_aco_2's probabilistic construction instead of Hill
              Climbing's neighbor search. No congestion (orthogonal to
              this model's addition, see models/opp_aco_4/opp_aco_4.py
              header) -- opp_aco_3's incremental congestion reservation
              and multi-pheromone (m-ACO4) architecture are NOT adopted
              here. Same test strategy as opp_hc_4: most normal/stress
              tests are ports of opp_aco_2's (V_p unset / T_frio_max
              default +inf -> pure equivalence), plus a handful of its own
              exercising heterogeneous speeds and a binding cold-chain
              deadline (see tests/opp_aco_4/README.md). Kept OUT of
              CONGESTION_AWARE_MODELS.

Each entry maps a short label -> the directory name under results/.
Add/remove entries here as models evolve; nothing else in the pipeline
should need to change.
"""

import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUTS_ROOT = os.path.join(PROJECT_ROOT, "results")
ANALYSIS_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "analysis", "output")

# label -> directory name under results/
MODEL_DIRS = {
    "opp_v4": "opp_v4",
    "opp_hc_2": "opp_hc_2",
    "opp_aco_2": "opp_aco_2",
    "opp_hc_3": "opp_hc_3",
    "opp_aco_3": "opp_aco_3",
    "opp_v5_1_mono": "opp_v5_1_mono",
    "opp_v5_2_split": "opp_v5_2_split",
    "opp_hc_4": "opp_hc_4",
    "opp_aco_4": "opp_aco_4",
}

SCENARIOS = ["functional", "stress"]

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

# Models covered by the seed-stability study (analysis/run_stability_study.py)
# -- the 6 heuristics only, since it measures how much a model's OWN
# randomness moves obj_val for the exact same instance, which is meaningless
# for a deterministic exact model (opp_v4/opp_v5_2_split always return the same
# answer for the same instance).
STABILITY_MODELS = ["opp_hc_2", "opp_hc_3", "opp_hc_4", "opp_aco_2", "opp_aco_3", "opp_aco_4"]

# Hard-coded "latest file" overrides, mirroring the exceptions called out in
# docs/specs/model_analysis.md (e.g. a consolidated file that must win over any
# later partial run, or a specific high-density stress run). Keyed by
# v5 stress tests 01-03 (migrated_stress_scenario): the scenarios the
# 2026-09-26 W_full change did NOT touch -- see the v5 stress overrides.
MIGRATED_STRESS_INSTANCES = (
    "test_25_orders_per_batch_30_batches_100x100",
    "test_10_orders_per_batch",
    "test_8_orders_per_batch_7x7_320_orders",
)

# (model_label, scenario) -> exact filename (relative to its output dir),
# or a list of sources merged in order: each source is a filename (all its
# rows) or (filename, instance names to take from it); when two sources
# have the same instance, the earlier source wins.
# Only labels present in MODEL_DIRS are ever looked up here (see
# analysis/load.py) -- legacy labels (opp_v3, opp_aco_1) were removed
# 2026-09-17 as dead/unreachable entries once those models dropped out of
# MODEL_DIRS.
LATEST_FILE_OVERRIDES = {
    # 2026-08-28: opp_v4's stress test files were renumbered/reshuffled at
    # some point (the "Rename tests" commit) without a matching full stress
    # re-run under the new numbering. The chronologically NEWER CSV
    # (20260825_194316, 3 rows) tests scenario names
    # (test_25_orders_per_batch_30_batches_25x25, etc.) that don't match ANY
    # current tests/opp_v4/stress/*.py file -- orphaned data from
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
    # 2026-09-24: opp_v5's results are consolidated runs under fixed names
    # (no timestamp) -- the version that counts, whatever a later run writes
    # next to it. "_parallel": the split stress run with Stage 1 on 6 workers.
    ("opp_v5_1_mono", "functional"): "output_opp_v5_1_mono_functional_tests.csv",
    # 2026-09-28: stress runs of 04-19 (the designed realistic_crew family)
    # after W_full changed from 9 to 27 in stress_scenarios_v5_designed.py
    # (2026-09-26, to rule out v5's voluntary-wait exploit) have a
    # DIFFERENT objective function than the consolidated files above, so
    # each stress entry now merges sources (list form, see
    # analysis/load.py): the new run for 04-19, plus the consolidated file
    # ONLY for 01-03 (migrated_stress_scenario, unchanged -- W_full still
    # 9 there). Mono's new run was cut after 04 (timeout at 40 min, the
    # smallest scenario); 05-19 were never run with W_full = 27, so they're
    # left out and reported as missing rather than taken from the W_full = 9
    # file.
    ("opp_v5_1_mono", "stress"): [
        "output_opp_v5_1_mono_stress_tests_20260927_124455.csv",
        ("output_opp_v5_1_mono_stress_tests.csv", MIGRATED_STRESS_INSTANCES),
    ],
    ("opp_v5_2_split", "functional"): "output_opp_v5_2_split_functional_tests.csv",
    ("opp_v5_2_split", "stress"): [
        "output_opp_v5_2_split_stress_tests_20260926_225549.csv",
        ("output_opp_v5_2_split_stress_tests_parallel.csv", MIGRATED_STRESS_INSTANCES),
    ],
}
