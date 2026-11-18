"""The Split instances that opp_split, opp_hc and opp_aco share.

Shared by build_functional_comparison and build_heuristics_comparison, so both
documents compare the same base: the registry that `python -m
experiments.comparison.comparability` writes (see docs/specs/comparabilidad_split_heuristicas.md).
A functional test of the Split is comparable when the registry marks all its instances
as comparable in status; the stress scenarios are the 19 of the suite.
"""
import csv
import os

from experiments.exact.reports.charts import ROOT

REGISTRY = os.path.join(ROOT, "results", "comparability", "comparability_split_vs_heuristics.csv")
RESULTS = os.path.join(ROOT, "results", "comparability", "results_split_vs_heuristics.csv")
SPLIT_VS_MONO = os.path.join(ROOT, "results", "comparability", "compare_split_vs_mono.csv")
HEURISTICS = ("opp_hc", "opp_aco")


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def registry():
    return _read(REGISTRY)


def results():
    return _read(RESULTS)


def functional_methods():
    """{Split method: (comparable, reason)}; a method is comparable if every instance is."""
    out = {}
    for r in registry():
        if r["tier"] != "functional":
            continue
        ok = r["comparable_status"] == "True"
        prev_ok, prev_reason = out.get(r["split_test"], (True, ""))
        out[r["split_test"]] = (prev_ok and ok, prev_reason or ("" if ok else r["not_comparable_reason"]))
    return out


def split_vs_mono_verdicts():
    """{(tier, method): [(verdict, detail), ...]} in file order (a method can repeat)."""
    out = {}
    for r in _read(SPLIT_VS_MONO):
        out.setdefault((r["tier"], r["test"]), []).append((r["verdict"], r["detail"]))
    return out


def compliance(model, tier):
    """{(case, test): verdict} of the model's compliance report."""
    path = os.path.join(ROOT, "results", "compliance", model, tier,
                        f"compliance_output_{model}_{tier}_tests.csv")
    return {tuple(r["test"].split(".")[-2:]): r["verdict"] for r in _read(path)}
