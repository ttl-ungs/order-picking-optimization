import unittest
import sys
import os
import time
import multiprocessing

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

STRESS_TEST_TIMEOUT_MINUTES = int(os.environ.get("STRESS_TEST_TIMEOUT_MINUTES", "60"))


def _collect_test_ids(suite):
    ids = []
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            ids.extend(_collect_test_ids(t))
        else:
            try:
                ids.append(t.id())
            except Exception:
                pass
    return ids


def _run_test_child(test_name, q):
    """Run a single test by name and put a summary in queue."""
    start = time.time()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = time.time() - start
    summary = {
        "test": test_name,
        "wasSuccessful": result.wasSuccessful(),
        "failures": [t[0].id() for t in result.failures],
        "errors": [t[0].id() for t in result.errors],
        "duration": duration,
    }
    try:
        q.put(summary)
    except Exception:
        pass


if __name__ == "__main__":
    loader = unittest.TestLoader()
    tests_dir = os.path.join(os.path.dirname(__file__), "tests", "stress")
    suite = loader.discover(start_dir=tests_dir, pattern="test_*_11.py")

    test_ids = _collect_test_ids(suite)

    results = []
    timeout_seconds = STRESS_TEST_TIMEOUT_MINUTES * 60

    for test_id in test_ids:
        print(f"Running {test_id} (timeout: {STRESS_TEST_TIMEOUT_MINUTES} min)")
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=_run_test_child, args=(test_id, q))
        p.start()
        p.join(timeout_seconds)
        if p.is_alive():
            print(
                f"Test {test_id} exceeded timeout ({STRESS_TEST_TIMEOUT_MINUTES} min). Terminating."
            )
            p.terminate()
            p.join()
            results.append(
                {"test": test_id, "status": "timeout", "duration": timeout_seconds}
            )
        else:
            if not q.empty():
                summary = q.get()
                status = "ok" if summary.get("wasSuccessful") else "failed"
                summary["status"] = status
                results.append(summary)
            else:
                results.append(
                    {"test": test_id, "status": "no_result", "duration": None}
                )

    # Print detailed times
    print("\n" + "=" * 60)
    print("DETAILED EXECUTION TIMES")
    print("=" * 60)
    for r in results:
        print(f"{r['test']}: {r.get('duration')}s ({r['status']})")

    # Final summary
    ran = len(results)
    failures = sum(1 for r in results if r.get("status") == "failed")
    errors = sum(1 for r in results if r.get("status") == "failed" and r.get("errors"))
    timeouts = sum(1 for r in results if r.get("status") == "timeout")

    print("\n" + "=" * 60)
    print("FINAL SUMMARY (STRESS TESTS)")
    print("=" * 60)
    print(f"Ran: {ran}")
    print(f"Failures: {failures}")
    print(f"Errors: {errors}")
    print(f"Timeouts: {timeouts}")

    if failures:
        print("\nFailed tests:")
        for r in results:
            if r.get("status") == "failed":
                print(f" - {r['test']}")

    if timeouts:
        print("\nTimed out tests:")
        for r in results:
            if r.get("status") == "timeout":
                print(f" - {r['test']}")

    if failures == 0 and timeouts == 0:
        print("\nAll tests passed or were skipped without failures/timeouts.")

    sys.exit(0 if failures == 0 and timeouts == 0 else 1)
