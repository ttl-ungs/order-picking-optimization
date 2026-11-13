"""Repository consistency checks (imports, layout, naming, stale references).

The checks that were done by hand after every restructuring, as one command:

    python -m scripts.check_repo            # everything
    python -m scripts.check_repo --skip-imports   # layout/naming/references only (instant)

Checks:
  imports     every tracked module imports cleanly
  naming      test files (test_*.py) under tests/<model>/{functional,stress,diagnostics}/
              are test_case_<NN|slug>.py, and the numbered ones are continuous (01..N)
  layout      no leftover scenarios/, tests/, doc/ inside tests/<model>/;
              results/ is results/<model>/<tier|study>/, results/compliance/<model>/<tier>/
              or the flat results/comparability/ and results/equal_time/ (tiers:
              functional|stress; studies: ablation|pheromone|seeds|budget)
  references  no tracked .py/.md still uses a module path or directory that
              was removed or renamed
Exit code is 1 if any check fails.
"""

import importlib
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.getcwd()
TIERS = ("functional", "stress", "diagnostics")
RESULT_TIERS = {"functional", "stress"}
# results/<model>/<study>/: a model's own calibration studies (opp_aco_4's
# ablation, pheromone and seed sweeps, opp_hc_4's budget study), not test-suite runs.
RESULT_STUDIES = {"ablation", "pheromone", "seeds", "budget"}
# results/<dir>/ that hold cross-model outputs instead of one model's runs:
#   compliance/<model>/<tier>/  verification/ reports (one per run it checks)
#   comparability/, equal_time/  flat CSVs (analysis.comparability, the
#                                equal-time study)
RESULT_CROSS_MODEL_NESTED = {"compliance"}
RESULT_CROSS_MODEL_FLAT = {"comparability", "equal_time"}

# Entry points / scripts whose import would run something or is not a library module.
# experiments/*/studies/ keeps each study's scripts exactly as they were run;
# most execute the experiment at import time.
IMPORT_SKIP_PREFIXES = ("experiments/opp_v5/studies/",)
IMPORT_SKIP_FILES = {"tests/run_suite.py"}

# (pattern, why) -- paths and dotted modules that no longer exist.
STALE = [
    (r"tests/outputs", "results moved to results/"),
    (r"tests\.opp_test_case\b", "moved to tests.infra.cases.opp_test_case"),
    (r"tests\.family_case\b", "moved to tests.infra.factories.family_case"),
    (r"tests\.test_(runner|config)\b", "moved to tests.infra.execution.(runner|config)"),
    (r"tests\.utils\.zpl_utils\b", "moved to tests.infra.zimpl.zpl_utils"),
    (r"models\.utils\.dat_files_builder\b", "moved to tests.infra.zimpl.dat_files_builder"),
    (r"\bgraphs\.graphs_factory\b", "moved to tests.infra.factories.graphs_factory"),
    (r"\b(models|tests)\.opp_v5\b|\b(models|tests|results)/opp_v5\b", "opp_v5 was renamed to opp_v5_2_split"),
    (r"tests\.opp_v[24]\.route_assertions\b", "moved to tests.infra.cases.route_assertions"),
    (r"tests\.opp_\w+\.tests\.(normal|stress|diagnostics)\b", "tests/<model>/tests/ was flattened"),
    (r"tests\.support\b|tests/support\b", "tests/support/ was regrouped into tests/infra/{execution,cases,factories,zimpl}"),
    (r"tests\.shared_scenarios\.normal\b", "renamed to tests.shared_scenarios.functional"),
    (r"\bmodels\.opp\.|\bmodels\.opp_hc\.|\bmodels\.opp_aco\.", "renamed to opp_v1 / opp_hc_1 / opp_aco_1"),
]
# Text where the old names are the point (history), not live references.
STALE_ALLOW = ("meta.md", "scripts/check_repo.py", "analysis/output/")


def tracked():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split("\n")
    return [f for f in out if f and os.path.exists(f)]


def check_imports(files):
    errors = []
    mods = 0
    for f in files:
        if not f.endswith(".py") or f.startswith(IMPORT_SKIP_PREFIXES) or f in IMPORT_SKIP_FILES:
            continue
        mod = f[:-3].replace("/", ".")
        if mod.endswith(".__init__"):
            mod = mod[: -len(".__init__")]
        if not mod:
            continue
        mods += 1
        try:
            importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001 -- report any failure, whatever its type
            errors.append(f"{mod}: {type(exc).__name__}: {str(exc)[:100]}")
    return mods, errors


def check_naming(files):
    errors = []
    by_dir = {}
    for f in files:
        m = re.match(r"tests/(opp_\w+)/(functional|stress|diagnostics)/([^/]+\.py)$", f)
        if m and m.group(3).startswith("test_"):  # helper modules in a tier dir are not tests
            by_dir.setdefault((m.group(1), m.group(2)), []).append(m.group(3))
    for (model, tier), names in sorted(by_dir.items()):
        numbers = []
        for n in names:
            if n in ("test_functional_cases.py", "test_stress_cases.py"):  # bind the shared cases to the model
                continue
            m = re.fullmatch(r"test_case_(\d+|[a-z0-9_]+)\.py", n)
            if not m:
                errors.append(f"tests/{model}/{tier}/{n}: not named test_case_<NN|slug>.py")
            elif m.group(1).isdigit():
                if len(m.group(1)) != 2:
                    errors.append(f"tests/{model}/{tier}/{n}: number must have two digits")
                numbers.append(int(m.group(1)))
        if tier != "functional" and numbers and sorted(numbers) != list(range(1, len(numbers) + 1)):
            missing = sorted(set(range(1, max(numbers) + 1)) - set(numbers))
            errors.append(f"tests/{model}/{tier}: numbering not continuous (missing {missing}, duplicates: {len(numbers) - len(set(numbers))})")
    shared = sorted(int(m.group(1)) for f in files if (m := re.fullmatch(r"tests/functional_cases/case_(\d\d)\.py", f)))
    if shared != list(range(1, len(shared) + 1)):
        errors.append(f"tests/functional_cases: case numbering not continuous (found {shared})")
    stress = sorted(int(m.group(1)) for f in files if (m := re.fullmatch(r"tests/stress_cases/case_(\d\d)\.py", f)))
    if stress != list(range(1, len(stress) + 1)):
        errors.append(f"tests/stress_cases: case numbering not continuous (found {stress})")
    return errors


def _check_result_path(f):
    """results/ holds exactly four shapes (anything else is a misplaced file):
      results/<opp_model>/<tier|study>/...
      results/compliance/<opp_model>/<tier>/<file>
      results/comparability/<file>, results/equal_time/<file>
    """
    parts = f.split("/")[1:]
    top = parts[0]
    if top.startswith("opp_"):
        if len(parts) < 3:
            return [f"{f}: results/{top}/ files go inside a tier or study directory"]
        if parts[1] not in RESULT_TIERS | RESULT_STUDIES:
            return [f"{f}: results tier must be one of {sorted(RESULT_TIERS)} (or a study: {sorted(RESULT_STUDIES)})"]
        return []
    if top in RESULT_CROSS_MODEL_NESTED:
        if len(parts) != 4 or not parts[1].startswith("opp_") or parts[2] not in RESULT_TIERS:
            return [f"{f}: expected results/{top}/<opp_model>/<tier>/<file>, tier in {sorted(RESULT_TIERS)}"]
        return []
    if top in RESULT_CROSS_MODEL_FLAT:
        if len(parts) != 2:
            return [f"{f}: results/{top}/ holds files directly, no subdirectories"]
        return []
    return [f"{f}: unknown results/ directory '{top}' (expected opp_<model>, "
            f"{', '.join(sorted(RESULT_CROSS_MODEL_NESTED | RESULT_CROSS_MODEL_FLAT))})"]


def check_layout(files):
    errors = []
    for f in files:
        m = re.match(r"tests/(opp_\w+)/(scenarios|tests|doc)/", f)
        if m:
            errors.append(f"{f}: tests/<model>/{m.group(2)}/ should not exist (scenarios -> tests/shared_scenarios)")
        if re.match(r"models/opp_\w+/example_usage\.py$", f):
            errors.append(f"{f}: usage examples live in examples/")
        if f.startswith("results/"):
            errors.extend(_check_result_path(f))
    return errors


def check_references(files):
    errors = []
    for f in files:
        if not f.endswith((".py", ".md")) or f.startswith(STALE_ALLOW):
            continue
        text = open(f, encoding="utf-8", errors="ignore").read()
        for pattern, why in STALE:
            m = re.search(pattern, text)
            if m:
                line = text[: m.start()].count("\n") + 1
                errors.append(f"{f}:{line}: '{m.group(0)}' -- {why}")
    return errors


def main():
    skip_imports = "--skip-imports" in sys.argv
    files = tracked()
    failed = 0
    sections = [
        ("layout", lambda: (None, check_layout(files))),
        ("naming", lambda: (None, check_naming(files))),
        ("references", lambda: (None, check_references(files))),
    ]
    if not skip_imports:
        sections.append(("imports", lambda: check_imports(files)))
    for name, fn in sections:
        count, errors = fn()
        extra = f" ({count} modules)" if count else ""
        print(f"[{'FAIL' if errors else ' ok '}] {name}{extra}")
        for e in errors[:25]:
            print(f"        {e}")
        if len(errors) > 25:
            print(f"        ... and {len(errors) - 25} more")
        failed += bool(errors)
    print("\nAll checks passed." if not failed else f"\n{failed} check(s) failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
