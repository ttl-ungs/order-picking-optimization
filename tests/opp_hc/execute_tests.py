import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from tests.test_runner import OPPTestRunner

TEST_TIMEOUT_MINUTES = int(os.environ.get("TEST_TIMEOUT_MINUTES", "25"))
WRITE_RESULTS_CSV = os.environ.get("WRITE_RESULTS_CSV", "").strip().lower() in (
    "1",
    "true",
    "yes",
)

if __name__ == "__main__":
    runner = OPPTestRunner(
        timeout_minutes=TEST_TIMEOUT_MINUTES,
        write_csv=WRITE_RESULTS_CSV,
        csv_path=os.path.join(os.path.dirname(__file__), "..", "outputs", "opp_hc", "results.csv"),
    )

    suite = unittest.TestLoader().discover(
        start_dir=os.path.join(os.path.dirname(__file__), "tests", "normal"),
        pattern="test_*.py",
    )
    test_ids = OPPTestRunner.collect_test_ids(suite)

    results = runner.run(test_ids)
    runner.print_summary(results, "NORMAL TESTS")

    if WRITE_RESULTS_CSV:
        runner.write_results_csv(results)

    sys.exit(0 if runner.succeeded(results) else 1)