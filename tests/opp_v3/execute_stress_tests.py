import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class TimedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_times = []

    def startTest(self, test):
        self._start_time = time.time()
        super().startTest(test)

    def stopTest(self, test):
        duration = time.time() - self._start_time
        self.test_times.append((test.id(), duration))
        print(f"{test.id()} executed in {duration:.4f} seconds")
        super().stopTest(test)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    tests_dir = os.path.join(os.path.dirname(__file__), "tests", "stress")
    suite = loader.discover(start_dir=tests_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2, resultclass=TimedResult)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print("DETAILED EXECUTION TIMES")
    print("=" * 60)
    for test_id, duration in result.test_times:
        print(f"{test_id}: {duration:.4f}s")

    print("\n" + "=" * 60)
    print("FINAL SUMMARY (STRESS TESTS)")
    print("=" * 60)
    print(f"Ran: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\nFailed tests:")
        for test, _ in result.failures:
            print(f" - {test.id()}")

    if result.errors:
        print("\nTests with errors:")
        for test, _ in result.errors:
            print(f" - {test.id()}")

    if not result.failures and not result.errors:
        print("\nAll tests passed.")

    sys.exit(0 if result.wasSuccessful() else 1)
