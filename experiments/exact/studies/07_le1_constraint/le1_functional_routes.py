"""Split only: what happens to the route-checking functional tests without `<= 1`?

A trial, not a model change: models/ is never touched. The split config copies
its Stage 1 .zpl into a per-process temp workspace at import time; this script
overwrites THAT copy, runs the tests in this same process (so no child process
re-imports a pristine copy), then does it again with the original model for a
side-by-side comparison.

The 11 tests are the v4 functional ones that assert the exact route
(`assertEqual(output_graph, expected_graph)`): 01-06, 08-11, 17.

Kept as it was run on 2026-09-23 (translated to English on 2026-09-24, same
logic). Its printed output is recorded in meta.md; it saved no CSV.
"""
import os
import re
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
os.environ.pop("OPP_STAGE1_METRIC_CLOSURE", None)
os.environ["OPP_STAGE1_WORKERS"] = "1"

from tests.opp_split.config import STAGE1_ZPL_PATH
import models.utils.solve_registry as solve_registry

TESTS = ["01", "02", "03", "04", "05", "06", "08", "09", "10", "11", "17"]

with open(STAGE1_ZPL_PATH, encoding="utf-8") as fh:
    ORIGINAL = fh.read()

RELAXED = ORIGINAL
for name in ("one_input_arc_per_node", "one_output_arc_per_node"):
    RELAXED, count = re.subn(rf"subto {name}:.*?;\s*", "", RELAXED, flags=re.S)
    assert count == 1, f"expected to remove exactly one {name}, removed {count}"
assert "one_input_arc_per_node" not in RELAXED and "one_output_arc_per_node" not in RELAXED


def walk(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from walk(item)
        else:
            yield item


def run(label, zpl_text):
    with open(STAGE1_ZPL_PATH, "w", encoding="utf-8") as fh:
        fh.write(zpl_text)
    out = {}
    for n in TESTS:
        suite = unittest.TestLoader().loadTestsFromName(f"tests.opp_split.functional.test_case_{n}")
        for test in walk(suite):
            solve_registry.register(None)
            result = unittest.TestResult()
            t0 = time.time()
            test.run(result)
            elapsed = time.time() - t0
            last = solve_registry.get_last()
            obj = last.params.get("obj_val") if last is not None else None
            problems = result.failures + result.errors
            detail = problems[0][1].strip().splitlines()[-1][:110] if problems else ""
            key = f"{n}.{test.id().split('.')[-1]}"
            out[key] = ("ok" if result.wasSuccessful() else "FAIL", obj, elapsed, detail,
                        problems[0][1] if problems else "")
    return out


original = run("original", ORIGINAL)
relaxed = run("without <= 1", RELAXED)

with open(STAGE1_ZPL_PATH, "w", encoding="utf-8") as fh:
    fh.write(ORIGINAL)

print(f"{'test':<46}{'original':>10}{'obj':>10}{'no <=1':>10}{'obj':>10}  t orig/relaxed")
print("-" * 104)
for key in original:
    s0, o0, t0, _, _ = original[key]
    s1, o1, t1, d1, _ = relaxed[key]
    fmt = lambda v: f"{v:.1f}" if isinstance(v, (int, float)) else "-"
    mark = "  <== changes" if (s0 != s1 or (o0 is not None and o1 is not None and abs(o0 - o1) > 1e-6)) else ""
    print(f"{key[:46]:<46}{s0:>10}{fmt(o0):>10}{s1:>10}{fmt(o1):>10}  {t0:.2f}/{t1:.2f}s{mark}")

print("\n--- failures without <= 1, in detail ---")
for key, (s1, o1, t1, d1, full) in relaxed.items():
    if s1 != "ok":
        print(f"\n[{key}]")
        tail = [ln for ln in full.strip().splitlines() if ln.strip()][-12:]
        print("\n".join("   " + ln for ln in tail))
