"""
Shared, model-family-agnostic problem instances + adapters, for anything
that needs to run the SAME instance across all 6 heuristic model families
(hc_2/3/4, aco_2/3/4) OUTSIDE the unittest test suite (e.g. the seed-
stability study, analysis/run_stability_study.py).

Not a refactor of the existing ~500 test files (each still builds its own
instance inline) -- this is a small, forward-compatible starting point:
if the existing suite is ever reorganized to separate instance
construction from DTO-wrapping from assertions, these are a template for
that shape. See instances.py / adapters.py for the actual split.
"""
