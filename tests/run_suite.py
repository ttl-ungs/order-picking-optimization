"""Single parametrized entry point for running a model's test suite.

Runs each test of a model's suite in its own process (TestRunner), with a
per-test timeout, and writes the results to results/<model>/<tier>/.

Usage:
    python -m tests.run_suite opp_hc functional
    python -m tests.run_suite opp_hc stress
    python -m tests.run_suite opp_hc stress --id 04
        (runs only case 04 instead of the full suite)

A case id NN selects the module test_case_NN.py and the shared cases whose
class is named Case<NN>... or Stress<NN>... (see tests/functional_cases and
tests/stress_cases).
"""

import argparse
import os
import re
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.infra.execution.config import (
    PRINT_RESULTS, STRESS_TEST_TIMEOUT_MINUTES, TEST_TIMEOUT_MINUTES, WRITE_RESULTS_CSV, WRITE_SOLUTIONS,
)
from tests.infra.execution.runner import TestRunner


def selected_by_id(test_id, case_ids):
    """Whether the test with this dotted id belongs to one of the cases `case_ids`."""
    *_, module, class_name, _method = test_id.split(".")
    return any(
        module == f"test_case_{case_id}" or re.match(rf"(Case|Stress){re.escape(case_id)}(?!\d)", class_name)
        for case_id in case_ids
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", help="Model directory name under tests/, e.g. opp_hc, opp_aco, opp_split, opp_mono.")
    parser.add_argument("tier", choices=["functional", "stress"])
    parser.add_argument(
        "--id",
        metavar="NN",
        nargs="+",
        help="Run only the case with each given id instead of the full suite.",
    )
    parser.add_argument(
        "--timeout-minutes",
        type=float,
        help="Per-test timeout in minutes (default: TEST_TIMEOUT_MINUTES / STRESS_TEST_TIMEOUT_MINUTES from .env).",
    )
    parser.add_argument(
        "--allow-timeout",
        action="store_true",
        help="Do not fail the exit code on timeouts (failures and errors still do).",
    )
    args = parser.parse_args(argv)

    model_dir = os.path.join(os.path.dirname(__file__), args.model)
    start_dir = os.path.join(model_dir, args.tier)
    if not os.path.isdir(start_dir):
        parser.error(f"No such directory: {start_dir}")

    if args.id:
        print(f"Single cases: {', '.join(args.id)}")

    timeout_minutes = args.timeout_minutes or (
        STRESS_TEST_TIMEOUT_MINUTES if args.tier == "stress" else TEST_TIMEOUT_MINUTES
    )

    runner = TestRunner(
        timeout_minutes=timeout_minutes,
        write_csv=WRITE_RESULTS_CSV,
        model_name=args.model,
        test_type=args.tier,
        write_solutions=WRITE_SOLUTIONS,
        print_results=PRINT_RESULTS,
    )

    suite = unittest.TestLoader().discover(start_dir=start_dir, pattern="test_*.py")
    test_ids = TestRunner.collect_test_ids(suite)
    if args.id:
        test_ids = [t for t in test_ids if selected_by_id(t, args.id)]

    results = runner.run(test_ids)
    label = f"{args.tier.upper()} TESTS ({args.model})"
    if args.id:
        label += f" [{', '.join(args.id)}]"
    runner.print_summary(results, label)

    sys.exit(0 if runner.succeeded(results, allow_timeout=args.allow_timeout) else 1)


if __name__ == "__main__":
    main()
