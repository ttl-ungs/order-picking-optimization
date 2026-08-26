import unittest

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.test_runner import TestRunner

from tests.test_config import TEST_TIMEOUT_MINUTES, WRITE_RESULTS_CSV

if __name__ == "__main__":
    runner = TestRunner(
        timeout_minutes=TEST_TIMEOUT_MINUTES,
        write_csv=WRITE_RESULTS_CSV,
        model_name="opp_v4",
        test_type="stress",
    )

    suite = unittest.TestLoader().discover(
        start_dir=os.path.join(os.path.dirname(__file__), "tests", "stress"),
        pattern="test_*.py",
    )
    test_ids = TestRunner.collect_test_ids(suite)

    results = runner.run(test_ids)
    runner.print_summary(results, "STRESS TESTS")

    sys.exit(0 if runner.succeeded(results) else 1)
