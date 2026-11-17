"""
Which models and which result files the experiments read.

- opp_split : exact, two stages (routing, then scheduling). The reference of
              the comparisons.
- opp_mono  : exact, the same problem as one monolithic MIP.
- opp_hc    : Hill Climbing heuristic.
- opp_aco   : Ant Colony Optimization heuristic.
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

# The results that count are consolidated runs under a fixed name, without a
# timestamp: results/<model>/<tier>/output_<model>_<tier>_tests.csv. A new run
# writes a timestamped file next to it, which nothing reads until it replaces
# the consolidated one. OPP-Split's stress run solved Stage 1 on 6 workers,
# hence its "_parallel" suffix.
def result_csv(model: str, tier: str) -> str:
    """Path of the consolidated results CSV of a model and tier."""
    suffix = "_parallel" if (model, tier) == ("opp_split", "stress") else ""
    return os.path.join(OUTPUTS_ROOT, MODEL_DIRS[model], tier, f"output_{model}_{tier}_tests{suffix}.csv")
