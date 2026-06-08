import csv
import multiprocessing
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _run_test_child(test_name, q):
    start = time.time()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = time.time() - start

    solve_data = None
    try:
        from models.utils.solve_registry import get_last
        sr = get_last()
        if sr is not None:
            solve_data = sr.to_csv_row()
    except Exception:
        pass

    summary = {
        "test": test_name,
        "wasSuccessful": result.wasSuccessful(),
        "failures": [t[0].id() for t in result.failures],
        "errors": [t[0].id() for t in result.errors],
        "duration": duration,
        "solve_data": solve_data,
    }
    try:
        q.put(summary)
    except Exception:
        pass


class OPPTestRunner:
    TIMEOUT_MSG = "Ejecución detenida - Más de 25 minutos"
    _FIXED_FIELDNAMES = ["test", "status", "total_time", "model_time"]

    def __init__(self, timeout_minutes: int, write_csv: bool, csv_path: str):
        self.timeout_minutes = timeout_minutes
        self.write_csv = write_csv
        self.csv_path = csv_path

    @staticmethod
    def collect_test_ids(suite) -> list:
        ids = []
        for t in suite:
            if isinstance(t, unittest.TestSuite):
                ids.extend(OPPTestRunner.collect_test_ids(t))
            else:
                try:
                    ids.append(t.id())
                except Exception:
                    pass
        return ids

    def run(self, test_ids: list) -> list:
        results = []
        timeout_seconds = self.timeout_minutes * 60

        for test_id in test_ids:
            print(f"Running {test_id} (timeout: {self.timeout_minutes} min)")
            q = multiprocessing.Queue()
            p = multiprocessing.Process(target=_run_test_child, args=(test_id, q))
            p.start()
            p.join(timeout_seconds)

            if p.is_alive():
                print(
                    f"Test {test_id} exceeded timeout ({self.timeout_minutes} min). Terminating."
                )
                p.terminate()
                p.join()
                results.append(
                    {
                        "test": test_id,
                        "status": "timeout",
                        "duration": None,
                        "solve_data": None,
                    }
                )
            else:
                if not q.empty():
                    summary = q.get()
                    summary["status"] = "ok" if summary.get("wasSuccessful") else "failed"
                    results.append(summary)
                else:
                    results.append(
                        {
                            "test": test_id,
                            "status": "no_result",
                            "duration": None,
                            "solve_data": None,
                        }
                    )

        return results

    def print_summary(self, results: list, label: str = "TESTS"):
        failures = [r for r in results if r.get("status") == "failed"]
        timeouts = [r for r in results if r.get("status") == "timeout"]
        errors = [r for r in failures if r.get("errors")]

        print("\n" + "=" * 60)
        print(f"FINAL SUMMARY ({label})")
        print("=" * 60)
        print(f"Ran: {len(results)}")
        print(f"Failures: {len(failures)}")
        print(f"Errors: {len(errors)}")
        print(f"Timeouts: {len(timeouts)}")

        if failures:
            print("\nFailed tests:")
            for r in failures:
                print(f" - {r['test']}")

        if timeouts:
            print("\nTimed out tests:")
            for r in timeouts:
                print(f" - {r['test']}")

        if not failures and not timeouts:
            print("\nAll tests passed.")

    def write_results_csv(self, results: list):
        # Collect param keys in insertion order, deduplicated, across all results
        param_keys = list(
            dict.fromkeys(
                k
                for r in results
                for k in (r.get("solve_data") or {})
                if k not in "model_time"
            )
        )
        fieldnames = self._FIXED_FIELDNAMES + param_keys

        os.makedirs(os.path.dirname(os.path.abspath(self.csv_path)), exist_ok=True)
        file_exists = os.path.isfile(self.csv_path)
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for r in results:
                is_timeout = r.get("status") == "timeout"
                solve_data = r.get("solve_data") or {}
                row = {
                    "test": r["test"],
                    "status": r.get("status"),
                    "total_time": self.TIMEOUT_MSG if is_timeout else r.get("duration"),
                    "model_time": self.TIMEOUT_MSG if is_timeout else solve_data.get("model_time"),
                    **{k: solve_data.get(k) for k in param_keys},
                }
                writer.writerow(row)
        print(f"\nResults were written in: {self.csv_path}")

    def succeeded(self, results: list) -> bool:
        return all(r.get("status") == "ok" for r in results)
