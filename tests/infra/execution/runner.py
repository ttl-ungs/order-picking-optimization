import csv
import multiprocessing
import os
import subprocess
import sys
import time
import unittest
from datetime import datetime

try:
    import resource  # Unix only
except ImportError:
    resource = None

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


def _peak_rss_mb():
    """
    Peak resident set size of the current process, in MB, read from the OS.
    tracemalloc sees only Python allocations and would badly understate the
    exact models, whose memory is mostly SCIP's native state.

    Unix: getrusage's ru_maxrss (bytes on macOS/BSD, KB on Linux). Windows:
    the process's PeakWorkingSetSize. None if neither is available.
    """
    if resource is not None:
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        divisor = (1024 * 1024) if sys.platform == "darwin" else 1024
        return raw / divisor
    if sys.platform == "win32":
        # Guarded: this runs in the child before the result is queued, and an
        # exception here would lose the test's outcome for a memory figure.
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
    spawned workers of its own (opp_split's parallel Stage 1) would leave
    them orphaned on a timeout, with SCIP still running in each and
    distorting the timings of every test that runs afterwards.
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


def _save_solution(sr, test_name, solutions_dir, solve_data):
    """Write the solution record (if the model attached one) as JSON under
    solutions_dir and link it from the CSV row as solution_file, a path
    relative to the project root. It runs after `duration` was taken, so it
    does not count towards the test's time; a failure here is reported in the
    row instead of costing the test's result."""
    record = getattr(sr, "solution_record", None)
    if record is None or solve_data is None:
        return
    try:
        from verification.solution_store import write_solution_record

        # <module>.<class>.<method>.json: the id of the test as it appears in the CSV.
        parts = test_name.split(".")
        path = os.path.join(solutions_dir, f"{'.'.join(parts[-3:])}.json")
        write_solution_record(record, test_name, path)
        solve_data["solution_file"] = os.path.relpath(path, _PROJECT_ROOT).replace(os.sep, "/")
    except Exception as e:
        solve_data["solution_file"] = f"ERROR: {e}"


def _attach_output_handlers():
    """Make every OPP-HC and OPP-ACO solver created in this process print its
    result through its own OutputHandler. The tests build the solvers
    themselves, so the handler is registered on the classes."""
    from models.opp_aco import OPPAntColonyOptimization
    from models.opp_aco.utils.output_handler import OutputHandler as AcoOutputHandler
    from models.opp_hc import OPPHillClimbing
    from models.opp_hc.utils.output_handler import OutputHandler as HcOutputHandler

    OPPHillClimbing.attach_to_new_instances(HcOutputHandler)
    OPPAntColonyOptimization.attach_to_new_instances(AcoOutputHandler)


def _run_test_child(test_name, q, solutions_dir=None, print_results=False):
    if print_results:
        _attach_output_handlers()
    start = time.time()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_name)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = time.time() - start
    peak_rss_mb = _peak_rss_mb()

    # One row per instance the test solved. A test with several instances
    # (the variants of a case) gets the ids <test>__1, <test>__2, ... in solve
    # order, the ids of functional_instances.json; each row's total_time is
    # the time of its own instance.
    instances = []
    try:
        from models.utils.solve_registry import get_instances

        entries = [e for e in get_instances() if e["result"] is not None]
        for k, entry in enumerate(entries, start=1):
            instance_id = f"{test_name}__{k}" if len(entries) > 1 else test_name
            solve_data = entry["result"].to_csv_row()
            if solutions_dir:
                _save_solution(entry["result"], instance_id, solutions_dir, solve_data)
            instance_duration = duration
            if len(entries) > 1 and entry["started_at"] is not None:
                instance_duration = entry["ended_at"] - entry["started_at"]
            instances.append({"test": instance_id, "duration": instance_duration, "solve_data": solve_data})
    except Exception:
        pass

    summary = {
        "test": test_name,
        "wasSuccessful": result.wasSuccessful(),
        "failures": [t[0].id() for t in result.failures],
        "errors": [t[0].id() for t in result.errors],
        "duration": duration,
        "peak_rss_mb": peak_rss_mb,
        "instances": instances or [{"test": test_name, "duration": duration, "solve_data": None}],
    }
    try:
        q.put(summary)
    except Exception:
        pass


class TestRunner:
    TIMEOUT_MSG = "Ejecución detenida por timeout"
    _FIXED_FIELDNAMES = ["test", "status", "total_time", "model_time", "obj_val", "peak_rss_mb"]

    def __init__(
        self, timeout_minutes: int, write_csv: bool, model_name: str, test_type: str,
        write_solutions: bool = False, print_results: bool = False,
    ):
        self.timeout_minutes = timeout_minutes
        self.print_results = print_results
        self.TIMEOUT_MSG = f"{self.TIMEOUT_MSG} - {timeout_minutes}"
        self.write_csv = write_csv

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        csv_filename = f"output_{model_name}_{test_type}_tests_{timestamp}.csv"

        self.csv_path = os.path.join(
            project_root, "results", model_name, test_type, csv_filename
        )

        # One JSON per test, same run timestamp as the CSV that links them
        # (column solution_file). See verification/solution_store.py.
        self.solutions_dir = (
            os.path.join(project_root, "results", model_name, test_type, "solutions", timestamp)
            if write_solutions
            else None
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
            p = multiprocessing.Process(target=_run_test_child, args=(test_id, q, self.solutions_dir, self.print_results))
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
            print(f"\n✅ Results written to:\n{self.csv_path}")
        if self.solutions_dir and os.path.isdir(self.solutions_dir):
            print(f"\n✅ Solutions written to:\n{self.solutions_dir}")

    def write_results_csv(self, results: list):
        param_keys = list(
            dict.fromkeys(
                k
                for r in results
                for instance in self._instances(r)
                for k in (instance.get("solve_data") or {})
                if k not in ("model_time", "obj_val")
            )
        )
        fieldnames = self._FIXED_FIELDNAMES + param_keys

        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r, instance in ((r, instance) for r in results for instance in self._instances(r)):
                is_timeout = r.get("status") == "timeout"
                solve_data = instance.get("solve_data") or {}
                row = {
                    "test": instance["test"],
                    "status": r.get("status"),
                    "total_time": self.TIMEOUT_MSG if is_timeout else instance.get("duration"),
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

    @staticmethod
    def _instances(result):
        """The CSV rows of one test's result: one per instance it solved (a
        timed-out test has a single row, with its own id)."""
        return result.get("instances") or [{"test": result["test"], "duration": result.get("duration"), "solve_data": None}]

    def succeeded(self, results: list, allow_timeout: bool = False) -> bool:
        """True if every test passed; with allow_timeout, timeouts are tolerated
        (they are still reported by print_summary) but failures/errors are not."""
        accepted = {"ok", "timeout"} if allow_timeout else {"ok"}
        return all(r.get("status") in accepted for r in results)
