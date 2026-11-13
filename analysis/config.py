"""
Configuration for the model-comparison analysis pipeline.

The four models of the thesis:

- opp_v5_2_split : exact model, 2-stage decomposition (routing then scheduling).
                   The reference of the comparisons.
- opp_v5_1_mono  : exact model, the same problem solved as ONE monolithic MIP.
- opp_hc_4       : Hill Climbing heuristic.
- opp_aco_4      : Ant Colony Optimization heuristic.

Neither the exact models nor the heuristics model congestion between pickers.

Each entry maps a short label -> the directory name under results/.
Add/remove entries here as models evolve; nothing else in the pipeline
should need to change.
"""

import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUTS_ROOT = os.path.join(PROJECT_ROOT, "results")

# label -> directory name under results/
MODEL_DIRS = {
    "opp_v5_1_mono": "opp_v5_1_mono",
    "opp_v5_2_split": "opp_v5_2_split",
    "opp_hc_4": "opp_hc_4",
    "opp_aco_4": "opp_aco_4",
}

SCENARIOS = ["functional", "stress"]

# The two heuristics (the models whose own randomness a seed study measures).
HEURISTIC_MODELS = ["opp_hc_4", "opp_aco_4"]

# Stress tests 01-03 (migrated_stress_scenario): the scenarios the 2026-09-26
# W_c change did NOT touch -- see the stress overrides below.
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
# analysis/load.py).
LATEST_FILE_OVERRIDES = {
    # 2026-09-24: opp_v5's results are consolidated runs under fixed names
    # (no timestamp) -- the version that counts, whatever a later run writes
    # next to it. "_parallel": the split stress run with Stage 1 on 6 workers.
    ("opp_v5_1_mono", "functional"): "output_opp_v5_1_mono_functional_tests.csv",
    # 2026-09-28: stress runs of 04-19 (the designed realistic_crew family)
    # after W_c changed from 9 to 27 in stress_scenarios_v5_designed.py
    # (2026-09-26, to rule out v5's voluntary-wait exploit) have a
    # DIFFERENT objective function than the consolidated files above, so
    # each stress entry now merges sources (list form, see
    # analysis/load.py): the new run for 04-19, plus the consolidated file
    # ONLY for 01-03 (migrated_stress_scenario, unchanged -- W_c still
    # 9 there). Mono's new run was cut after 04 (timeout at 40 min, the
    # smallest scenario); 05-19 were never run with W_c = 27, so they're
    # left out and reported as missing rather than taken from the W_c = 9
    # file. 2026-09-29: unified in one file (04's row from the 2026-09-27
    # run replaced the W_c = 9 one; 05-19 kept untouched as the W_c = 9
    # record), so only 01-04 are read from it.
    ("opp_v5_1_mono", "stress"): [
        ("output_opp_v5_1_mono_stress_tests.csv",
         MIGRATED_STRESS_INSTANCES + ("test_realistic_crew_7x7_warehouse",)),
    ],
    ("opp_v5_2_split", "functional"): "output_opp_v5_2_split_functional_tests.csv",
    # 2026-09-29: opp_hc_4/opp_aco_4 results are unified runs under fixed
    # names, like opp_v5's: one row per current test, every row taken from a
    # run saved with WRITE_SOLUTIONS, so each links to its solution JSON
    # (solution_file) and to its row in results/compliance/ (all verified
    # against opp_v5_1_mono). opp_aco_4 stress merges three runs (8 + 10
    # tests + the 100x100); its 100x100 row had a 4-min laptop suspension,
    # so its objective (988,252) is 6.9% above the discarded 2026-09-28 run
    # without a saved solution (924,536) -- see meta.md.
    ("opp_hc_4", "functional"): "output_opp_hc_4_functional_tests.csv",
    ("opp_hc_4", "stress"): "output_opp_hc_4_stress_tests.csv",
    ("opp_aco_4", "functional"): "output_opp_aco_4_functional_tests.csv",
    ("opp_aco_4", "stress"): "output_opp_aco_4_stress_tests.csv",
    # 2026-09-29: split stress unified in one file. 02, 04-07, 09-11 and 15
    # re-run with the current code (Stage 1 on 6 workers, same objectives as
    # before); the 10 timeouts (40 min) kept from their previous runs: 01 and
    # 03 from the 09-24 run, 08 and 12-19 from the 09-26 run (W_c = 27).
    ("opp_v5_2_split", "stress"): "output_opp_v5_2_split_stress_tests_parallel.csv",
}
