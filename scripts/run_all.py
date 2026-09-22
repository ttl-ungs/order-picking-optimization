"""Run every model's test suites and compare the results with a baseline.

    python -m scripts.run_all --collect-only               # counts only, seconds (no test is run)
    python -m scripts.run_all                              # functional suites of the HC/ACO models
    python -m scripts.run_all --profile full               # every model (opp_v1..v5 use SCIP/zimpl: slow)
    python -m scripts.run_all --tier stress --stress-timeout-minutes 1
    python -m scripts.run_all --models opp_hc_2,opp_aco_3 --tier all
    python -m scripts.run_all --tier stress --smoke        # only the fast stress tests (scripts/stress_smoke.json)
    python -m scripts.run_all --retries 1                  # re-run a failing suite once (ACO tests without a Seed can flake)
    python -m scripts.run_all --json report.json           # machine-readable result too

scripts/baseline_counts.json holds how many tests each suite had on main before
the reorganization (and the failures known to exist there). A suite is:
  PASS      ran, no failures/errors beyond the known ones, same test count as the baseline
  COUNT     ran without failures but the number of tests differs from the baseline
  FAIL      failures/errors (or the runner crashed)
  TIMEOUT   the suite hit its time limit (functional: --timeout seconds for the whole
            suite; stress: --stress-suite-timeout for the whole suite)
  SKIP      needs the `zimpl` binary and it is not on PATH
Stress suites, and the zimpl-dependent functional suites (opp_v2_zpl/opp_v4/opp_v5), run
through tests/run_suite.py with --allow-timeout: a single test that exceeds
--stress-timeout-minutes / --timeout-minutes is reported but does not make the suite fail.
Every other functional suite runs via plain `unittest discover` (no per-test cap needed --
none of them are expected to hang).
--smoke restricts stress suites to the tests listed in scripts/stress_smoke.json (built by
scripts/make_stress_smoke.py from the recorded results: the ones that finished quickly).
--retries N re-runs a suite that FAILed up to N more times; if it then passes it is reported
as PASS with "flaky" in the detail, so instability stays visible.
Exit code is 1 if any suite is FAIL, COUNT or (functional) TIMEOUT.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.getcwd()
BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baseline_counts.json")
SMOKE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stress_smoke.json")
FAST_MODELS = ["opp_hc_1", "opp_hc_2", "opp_hc_3", "opp_hc_4", "opp_aco_1", "opp_aco_2", "opp_aco_3", "opp_aco_4"]
NEEDS_ZIMPL = {"opp_v2_zpl", "opp_v4", "opp_v5"}

COLLECT_CODE = """
import sys, unittest
n = 0
def walk(s):
    global n
    for t in s:
        if isinstance(t, unittest.TestSuite):
            walk(t)
        else:
            n += 1
walk(unittest.TestLoader().discover(start_dir=sys.argv[1], pattern="test_*.py"))
print("COUNT", n)
"""


def load_baseline():
    with open(BASELINE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def suite_dir(model, tier):
    return os.path.join("tests", model, tier)


def run(cmd, timeout, env=None):
    """Returns (returncode or None on timeout, combined output, timed_out)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env, cwd=ROOT)
        return p.returncode, (p.stdout or "") + "\n" + (p.stderr or ""), False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode(errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        return None, out, True


def judge(tier, model, ran, failures, errors, baseline, timed_out):
    known = baseline.get("known_failures", {}).get(f"{tier}/{model}", {})
    expected = baseline["counts"].get(tier, {}).get(model)
    if timed_out:
        return "TIMEOUT"
    if ran is None:
        return "FAIL"
    if failures > known.get("failures", 0) or errors > known.get("errors", 0):
        return "FAIL"
    if expected is not None and ran != expected:
        return "COUNT"
    return "PASS"


def grab(pattern, text):
    m = re.search(pattern, text, re.M)
    return int(m.group(1)) if m else None


def do_suite(args, baseline, model, tier):
    expected = baseline["counts"].get(tier, {}).get(model)
    if model in NEEDS_ZIMPL and not args.collect_only and not shutil.which("zimpl"):
        return dict(model=model, tier=tier, status="SKIP", ran=None, expected=expected, detail="zimpl not on PATH")
    if args.collect_only:
        rc, out, to = run([sys.executable, "-c", COLLECT_CODE, suite_dir(model, tier)], 300)
        ran = grab(r"COUNT (\d+)", out)
        status = "FAIL" if ran is None else ("PASS" if expected is None or ran == expected else "COUNT")
        return dict(model=model, tier=tier, status=status, ran=ran, expected=expected, detail="collect only")
    env = dict(os.environ, WRITE_RESULTS_CSV="0")
    if tier == "stress":
        cmd = [sys.executable, "-m", "tests.run_suite", model, "stress", "--allow-timeout",
               "--timeout-minutes", str(args.stress_timeout_minutes)]
        if args.smoke:
            entry = args.smoke_list.get(model)
            if not entry:
                return dict(model=model, tier=tier, status="SKIP", ran=None, expected=None, detail="no smoke tests listed")
            cmd += ["--id"] + entry["ids"]
            expected = entry["tests"]
        rc, out, to = run(cmd, args.stress_suite_timeout, env)
        ran = grab(r"^Ran: (\d+)", out)
        failures, errors, timeouts = (grab(r"^Failures: (\d+)", out) or 0, grab(r"^Errors: (\d+)", out) or 0,
                                      grab(r"^Timeouts: (\d+)", out) or 0)
        status = judge(tier, model, ran, failures, errors, baseline, to)
        if args.smoke and status in ("PASS", "COUNT"):
            status = "PASS" if ran == expected else "COUNT"
        return dict(model=model, tier=tier, status=status, ran=ran, expected=expected,
                    detail=f"failures={failures} errors={errors} per-test timeouts={timeouts}")
    if model in NEEDS_ZIMPL:
        # Plain `unittest discover` (below) has no per-test cap: a single non-converging
        # instance runs unbounded until this whole suite's --timeout kills the process, wiping
        # out every other test's result with it (no final "Ran N tests" summary line ever gets
        # printed). opp_v4/opp_v5 each have one documented instance that never converges (see
        # analysis/README.md) -- exactly the "many tests, one is fine to time out" case
        # tests.run_suite/TestRunner already handles for the stress tier above. Scoped to
        # NEEDS_ZIMPL only: TestRunner spawns a fresh process per test, which is needless
        # overhead for the HC/ACO suites below (fast, never expected to hang).
        cmd = [sys.executable, "-m", "tests.run_suite", model, "functional", "--allow-timeout"]
        if args.timeout_minutes is not None:
            cmd += ["--timeout-minutes", str(args.timeout_minutes)]
        rc, out, to = run(cmd, args.timeout, env)
        ran = grab(r"^Ran: (\d+)", out)
        failures, errors, timeouts = (grab(r"^Failures: (\d+)", out) or 0, grab(r"^Errors: (\d+)", out) or 0,
                                      grab(r"^Timeouts: (\d+)", out) or 0)
        status = judge(tier, model, ran, failures, errors, baseline, to)
        detail = f"failures={failures} errors={errors}"
        if timeouts:
            detail += f" per-test timeouts={timeouts}"
        return dict(model=model, tier=tier, status=status, ran=ran, expected=expected, detail=detail)

    cmd = [sys.executable, "-m", "unittest", "discover", "-s", suite_dir(model, tier), "-p", "test_*.py"]
    rc, out, to = run(cmd, args.timeout, env)
    ran = grab(r"^Ran (\d+) tests? in", out)
    failures, errors = grab(r"failures=(\d+)", out) or 0, grab(r"errors=(\d+)", out) or 0
    status = judge(tier, model, ran, failures, errors, baseline, to)
    return dict(model=model, tier=tier, status=status, ran=ran, expected=expected,
                detail=f"failures={failures} errors={errors}")


def do_suite_with_retries(args, baseline, model, tier):
    result = do_suite(args, baseline, model, tier)
    attempt = 0
    while result["status"] == "FAIL" and attempt < args.retries:
        attempt += 1
        again = do_suite(args, baseline, model, tier)
        if again["status"] != "FAIL":
            again["detail"] += f" (flaky: failed {attempt} time(s) before passing)"
            return again
        result = again
    if attempt:
        result["detail"] += f" (still failing after {attempt} retr{'y' if attempt == 1 else 'ies'})"
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", choices=["functional", "stress", "all"], default="functional")
    ap.add_argument("--profile", choices=["fast", "full"], default="fast")
    ap.add_argument("--models", help="comma-separated; overrides --profile")
    ap.add_argument("--jobs", type=int, default=2, help="suites run in parallel (default 2)")
    ap.add_argument("--timeout", type=int, default=900, help="seconds for a whole functional suite (default 900)")
    ap.add_argument("--timeout-minutes", type=float, default=None,
                     help="per test, for opp_v2_zpl/opp_v4/opp_v5 only (default: TEST_TIMEOUT_MINUTES from .env)")
    ap.add_argument("--stress-timeout-minutes", type=float, default=1.0, help="per stress test (default 1)")
    ap.add_argument("--stress-suite-timeout", type=int, default=3600, help="seconds for a whole stress suite (default 3600)")
    ap.add_argument("--smoke", action="store_true", help="stress tier: only the fast tests in scripts/stress_smoke.json")
    ap.add_argument("--retries", type=int, default=0, help="re-run a failing suite up to N more times (default 0)")
    ap.add_argument("--collect-only", action="store_true", help="only count tests (no test is run)")
    ap.add_argument("--update-baseline", action="store_true", help="rewrite the baseline counts from the current tree")
    ap.add_argument("--json", help="also write the results to this file")
    args = ap.parse_args()

    baseline = load_baseline()
    args.smoke_list = {}
    if args.smoke:
        with open(SMOKE_PATH, encoding="utf-8") as fh:
            args.smoke_list = json.load(fh)["models"]
        if args.models is None and args.profile == "fast":
            args.models = ",".join(args.smoke_list)
    tiers = ["functional", "stress"] if args.tier == "all" else [args.tier]
    known = {m for t in baseline["counts"].values() for m in t}
    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    elif args.profile == "full" or args.update_baseline:
        models = sorted(known | {m for m in os.listdir("tests") if m.startswith("opp_") and os.path.isdir(os.path.join("tests", m))})
    else:
        models = FAST_MODELS
    suites = [(m, t) for t in tiers for m in models if os.path.isdir(suite_dir(m, t))]

    if args.update_baseline:
        args.collect_only = True
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(lambda s: do_suite_with_retries(args, baseline, *s), suites))

    if args.update_baseline:
        for r in results:
            if r["ran"] is not None:
                baseline["counts"].setdefault(r["tier"], {})[r["model"]] = r["ran"]
        with open(BASELINE_PATH, "w", encoding="utf-8") as fh:
            json.dump(baseline, fh, indent=1)
        print(f"Baseline rewritten: {BASELINE_PATH}")

    print(f"{'suite':<28}{'status':<9}{'ran':>6}{'baseline':>10}  detail")
    for r in sorted(results, key=lambda r: (r["tier"], r["model"])):
        print(f"{r['tier'] + '/' + r['model']:<28}{r['status']:<9}{str(r['ran']):>6}{str(r['expected']):>10}  {r['detail']}")
    bad = [r for r in results if r["status"] in ("FAIL", "COUNT") or (r["status"] == "TIMEOUT" and r["tier"] == "functional")]
    print(f"\n{len(results)} suite(s): " + ", ".join(f"{s}={sum(r['status'] == s for r in results)}" for s in ("PASS", "COUNT", "FAIL", "TIMEOUT", "SKIP")))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1)
    return 1 if bad and not args.update_baseline else 0


if __name__ == "__main__":
    sys.exit(main())
