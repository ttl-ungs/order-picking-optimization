import unittest

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

if __name__ == "__main__":
    loader = unittest.TestLoader()
    tests_dir = os.path.join(os.path.dirname(__file__), "stress")
    suite = loader.discover(start_dir=tests_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

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
