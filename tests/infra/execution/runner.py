import csv
import multiprocessing
import os
import subprocess
import sys
import time
import unittest
from datetime import datetime  # NUEVO IMPORT

try:
    import resource  # Unix only
except ImportError:
    resource = None

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def _peak_rss_mb():
    """
    Peak resident set size (RAM actually used, all of it -- Python objects
    AND native allocations like PySCIPOpt's C-level SCIP state) of the
    CURRENT process since it started, in MB. Read from the OS, not
    tracemalloc: tracemalloc only sees Python-level allocations, which would
    badly UNDERSTATE memory for exact-model tests (opp_v2/v3/v4/v5_1_mono/v5_2_split), whose
    actual RAM cost is dominated by SCIP's native branch-and-bound state.

    Unix: getrusage's ru_maxrss (bytes on macOS/BSD, KB on Linux), normalized
    to MB. Windows has no `resource` module: uses the process's
    PeakWorkingSetSize instead. Returns None if neither is available.
    """
    if resource is not None:
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        divisor = (1024 * 1024) if sys.platform == "darwin" else 1024
        return raw / divisor
    if sys.platform == "win32":
        # Guarded because this runs in _run_test_child BEFORE the result is
        # queued: any exception here (e.g. `from ctypes import wintypes`
        # failing under memory pressure) would kill the child silently and
        # the parent would report "no_result", discarding the test's real
        # outcome. A missing memory figure must never cost us the result.
        try:
            import ctypes
            from ctypes import wintypes

            class _ProcessMemoryCounters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = _ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessMemoryCounters), wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            if psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return counters.PeakWorkingSetSize / (1024 * 1024)
        except Exception:
            return None
    return None


def _kill_process_tree(pid):
    """Kill `pid` and every descendant (best effort).

    multiprocessing's terminate() kills only the direct child. A test that
    spawned worker processes of its own -- opp_v5_2_split's Stage 1 runs a
    ProcessPoolExecutor -- leaves them orphaned when a timeout terminates
    that child: SCIP keeps optimizing in each worker with nobody left to
    collect the result, holding RAM and burning CPU against every test that
    runs afterwards, so one timeout silently corrupts the timings of all
    the tests behind it.
    """
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
        return
    try:
        import psutil

        for child in psutil.Process(pid).children(recursive=True):
            child.kill()
    except Exception:
        pass


def _run_test_child(test_name, q):
    start = time.time()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = time.time() - start
    peak_rss_mb = _peak_rss_mb()

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
        "peak_rss_mb": peak_rss_mb,
        "solve_data": solve_data,
    }
    try:
        q.put(summary)
    except Exception:
        pass


class TestRunner:
    TIMEOUT_MSG = "Ejecución detenida por timeout"
    _FIXED_FIELDNAMES = ["test", "status", "total_time", "model_time", "obj_val", "peak_rss_mb"]

    def __init__(
        self, timeout_minutes: int, write_csv: bool, model_name: str, test_type: str
    ):
        self.timeout_minutes = timeout_minutes
        self.TIMEOUT_MSG = f"{self.TIMEOUT_MSG} - {timeout_minutes}"
        self.write_csv = write_csv

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Ej: 20231024_153000

        # Ej: output_opp_hc_stress_tests_20231024_153000.csv
        csv_filename = f"output_{model_name}_{test_type}_tests_{timestamp}.csv"

        # Ej: results/opp_hc_1/stress/output_opp_hc_stress_tests_20231024_153000.csv
        self.csv_path = os.path.join(
            project_root, "results", model_name, test_type, csv_filename
        )

        if self.write_csv:
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                pass

    @staticmethod
    def collect_test_ids(suite) -> list:
        ids = []
        for t in suite:
            if isinstance(t, unittest.TestSuite):
                ids.extend(TestRunner.collect_test_ids(t))
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
                _kill_process_tree(p.pid)
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
                    summary["status"] = (
                        "ok" if summary.get("wasSuccessful") else "failed"
                    )
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

            if self.write_csv:
                self.write_results_csv(results)

        return results

    def print_summary(self, results: list, label: str = "TESTS"):
        failures = [r for r in results if r.get("status") == "failed"]
        timeouts = [r for r in results if r.get("status") == "timeout"]
        errors = [r for r in failures if r.get("errors")]

        print("\n" + "=" * 60)
        print(f"FINAL SUMMARY ({label})")
        print("=" * 60)
        print(f"Ran: {len(results)}")
        print(f"Passed: {len(results) - len(failures) - len(timeouts)}")
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

        if self.write_csv:
            print(f"\n✅ Resultados guardados en:\n{self.csv_path}")

    def write_results_csv(self, results: list):
        param_keys = list(
            dict.fromkeys(
                k
                for r in results
                for k in (r.get("solve_data") or {})
                if k not in ("model_time", "obj_val")
            )
        )
        fieldnames = self._FIXED_FIELDNAMES + param_keys

        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                is_timeout = r.get("status") == "timeout"
                solve_data = r.get("solve_data") or {}
                row = {
                    "test": r["test"],
                    "status": r.get("status"),
                    "total_time": self.TIMEOUT_MSG if is_timeout else r.get("duration"),
                    "model_time": (
                        self.TIMEOUT_MSG if is_timeout else solve_data.get("model_time")
                    ),
                    "obj_val": (
                        self.TIMEOUT_MSG if is_timeout else solve_data.get("obj_val")
                    ),
                    "peak_rss_mb": (
                        self.TIMEOUT_MSG if is_timeout else r.get("peak_rss_mb")
                    ),
                    **{k: solve_data.get(k) for k in param_keys},
                }
                writer.writerow(row)

    def succeeded(self, results: list, allow_timeout: bool = False) -> bool:
        """True if every test passed; with allow_timeout, timeouts are tolerated
        (they are still reported by print_summary) but failures/errors are not."""
        accepted = {"ok", "timeout"} if allow_timeout else {"ok"}
        return all(r.get("status") in accepted for r in results)
