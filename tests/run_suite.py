"""Single parametrized entry point for running a model's test suite.

Replaces the ~24 near-identical per-model execute_tests.py /
execute_stress_tests.py scripts (one pair per model, differing only in the
model_name/test_type strings passed to TestRunner) with one script driven by
CLI arguments. Two legacy models (opp_v1, opp_v2) predate TestRunner entirely
(plain unittest.TextTestRunner, no CSV output, no timeout) and keep their own
execute_tests.py/execute_stress_tests.py unchanged -- they don't fit this
runner's contract.

Usage:
    python -m tests.run_suite opp_hc_2 functional
    python -m tests.run_suite opp_hc_3 stress
    python -m tests.run_suite opp_hc_3 stress --id 04
        (equivalent to the old `python tests/opp_hc_3/execute_stress_tests.py 04`
        -- runs only test_case_04.py instead of the full suite)
"""

import argparse
import os
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.infra.execution.config import STRESS_TEST_TIMEOUT_MINUTES, TEST_TIMEOUT_MINUTES, WRITE_RESULTS_CSV
from tests.infra.execution.runner import TestRunner


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", help="Model directory name under tests/, e.g. opp_hc_2, opp_aco_3, opp_v4.")
    parser.add_argument("tier", choices=["functional", "stress"])
    parser.add_argument(
        "--id",
        metavar="NN",
        help="Run only test_case_<id>.py instead of the full suite (stress tier only).",
    )
    args = parser.parse_args(argv)

    if args.id and args.tier != "stress":
        parser.error("--id is only supported for the stress tier")

    model_dir = os.path.join(os.path.dirname(__file__), args.model)
    start_dir = os.path.join(model_dir, args.tier)
    if not os.path.isdir(start_dir):
        parser.error(f"No such directory: {start_dir}")

    test_pattern = "test_*.py"
    if args.id:
        test_pattern = f"test_case_{args.id}.py"
        print(f"Modo individual: Buscando el test {test_pattern}")

    timeout_minutes = STRESS_TEST_TIMEOUT_MINUTES if args.tier == "stress" else TEST_TIMEOUT_MINUTES

    runner = TestRunner(
        timeout_minutes=timeout_minutes,
        write_csv=WRITE_RESULTS_CSV,
        model_name=args.model,
        test_type=args.tier,
    )

    suite = unittest.TestLoader().discover(start_dir=start_dir, pattern=test_pattern)
    test_ids = TestRunner.collect_test_ids(suite)

    results = runner.run(test_ids)
    label = f"{args.tier.upper()} TESTS ({args.model})"
    if args.id:
        label += f" [{test_pattern}]"
    runner.print_summary(results, label)

    sys.exit(0 if runner.succeeded(results) else 1)


if __name__ == "__main__":
    main()
