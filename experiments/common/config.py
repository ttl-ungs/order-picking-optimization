"""
Configuration for the model-comparison analysis pipeline.

The four models of the thesis:

- opp_split : exact model, 2-stage decomposition (routing then scheduling).
                   The reference of the comparisons.
- opp_mono  : exact model, the same problem solved as ONE monolithic MIP.
- opp_hc       : Hill Climbing heuristic.
- opp_aco      : Ant Colony Optimization heuristic.

Neither the exact models nor the heuristics model congestion between pickers.

Each entry maps a short label -> the directory name under results/.
Add/remove entries here as models evolve; nothing else in the pipeline
should need to change.
"""

import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUTS_ROOT = os.path.join(PROJECT_ROOT, "results")

# label -> directory name under results/
MODEL_DIRS = {
    "opp_mono": "opp_mono",
    "opp_split": "opp_split",
    "opp_hc": "opp_hc",
    "opp_aco": "opp_aco",
}

SCENARIOS = ["functional", "stress"]

# The two heuristics (the models whose own randomness a seed study measures).
HEURISTIC_MODELS = ["opp_hc", "opp_aco"]

# Stress tests 01-03 (grid_stress_scenario): the scenarios that keep W_c = 9, unlike
# the designed ones (04-19, W_c = 27, see stress_scenarios_designed.py).
GRID_STRESS_INSTANCES = (
    "test_25_orders_per_batch_30_batches_100x100",
    "test_10_orders_per_batch",
    "test_8_orders_per_batch_7x7_320_orders",
)

# (model_label, scenario) -> exact filename (relative to its output dir),
# or a list of sources merged in order: each source is a filename (all its
# rows) or (filename, instance names to take from it); when two sources
# have the same instance, the earlier source wins.
# Only labels present in MODEL_DIRS are ever looked up here (see
# experiments/common/load.py).
LATEST_FILE_OVERRIDES = {
    # The results that count are consolidated runs under fixed names (no
    # timestamp), whatever a later run writes next to them.
    ("opp_mono", "functional"): "output_opp_mono_functional_tests.csv",
    # Stress 04-19 use W_c = 27 (to rule out the voluntary-wait exploit of the
    # exact models), a different objective function than 01-03 (W_c = 9). Mono
    # was only run on 01-04 with the current stress suite (04 timed out at
    # 40 min), so only those are read from its file; the rest are reported as
    # missing instead of being taken from runs with W_c = 9.
    ("opp_mono", "stress"): [
        ("output_opp_mono_stress_tests.csv",
         GRID_STRESS_INSTANCES + ("test_realistic_crew_7x7_warehouse",)),
    ],
    ("opp_split", "functional"): "output_opp_split_functional_tests.csv",
    # opp_hc / opp_aco: one row per current test, every row taken from a run
    # saved with WRITE_SOLUTIONS, so each links to its solution JSON
    # (solution_file) and to its row in results/compliance/ (all verified
    # against opp_mono). opp_aco's 100x100 row (objective 988,252) includes a
    # 4-minute laptop suspension, so it is 6.9% above a discarded run without
    # a saved solution (924,536).
    ("opp_hc", "functional"): "output_opp_hc_functional_tests.csv",
    ("opp_hc", "stress"): "output_opp_hc_stress_tests.csv",
    ("opp_aco", "functional"): "output_opp_aco_functional_tests.csv",
    ("opp_aco", "stress"): "output_opp_aco_stress_tests.csv",
    # opp_split stress, Stage 1 on 6 workers ("_parallel"): the timeouts (40
    # min) are kept from earlier runs of the same scenarios.
    ("opp_split", "stress"): "output_opp_split_stress_tests_parallel.csv",
}
