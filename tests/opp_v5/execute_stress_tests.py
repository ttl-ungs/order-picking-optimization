import os
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.test_config import STRESS_TEST_TIMEOUT_MINUTES, WRITE_RESULTS_CSV
from tests.test_runner import TestRunner


if __name__ == "__main__":
    runner = TestRunner(STRESS_TEST_TIMEOUT_MINUTES, WRITE_RESULTS_CSV, "opp_v5", "stress")
    suite = unittest.TestLoader().discover(
        start_dir=os.path.join(os.path.dirname(__file__), "tests", "stress"),
        pattern="test_*.py",
    )
    results = runner.run(TestRunner.collect_test_ids(suite))
    runner.print_summary(results, "OPP V5 STRESS TESTS")
    sys.exit(0 if runner.succeeded(results) else 1)
