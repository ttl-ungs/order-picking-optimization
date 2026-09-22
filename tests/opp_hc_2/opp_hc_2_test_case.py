from observer.observer import Observer
from tests.opp_test_case import OPPTestCase


class SolutionInfoCapture(Observer):
    """Captures the solution_info dict notified by OPPHillClimbing.solve()."""

    def __init__(self):
        self.solution_info = {}

    def update(self, solution_info: dict, **kwargs):
        self.solution_info = solution_info


class OPPTestCaseHC2(OPPTestCase):
    """
    Base test case for opp_hc_2, adding assertions specific to the picker
    parallelization introduced vs. opp_hc_1 (v3): batches distributed across
    pickers (X_pb) and no time overlap between batches on the same picker.
    """

    def solve_and_capture(self, model, params):
        """Attach a capture observer, solve, and return (result, output_graph, solution_info)."""
        capture = SolutionInfoCapture()
        model.attach(capture)
        result, output_graph = model.solve(params)
        return result, output_graph, capture.solution_info

    def assert_every_batch_has_one_picker(self, solution_info, P):
        """Mirrors ZPL constraint (14): assign_exactly_one_picker."""
        picker_assignments = solution_info.get("picker_assignments", {})
        for batch, picker in picker_assignments.items():
            self.assertIn(
                picker, P, f"Batch {batch} assigned to unknown picker {picker}"
            )

    def assert_workload_balance(self, solution_info, P, max_difference=1):
        """Batches should be spread across pickers, not piled on one."""
        picker_assignments = solution_info.get("picker_assignments", {})
        workload = {p: 0 for p in P}
        for _, picker in picker_assignments.items():
            workload[picker] = workload.get(picker, 0) + 1

        workloads = list(workload.values())
        if workloads:
            self.assertLessEqual(
                max(workloads) - min(workloads),
                max_difference,
                f"Picker workload imbalance: {workload}",
            )

    def assert_no_time_overlap(self, solution_info, P):
        """
        Mirrors ZPL constraints (19)/(20): batches on the same picker must be
        sequenced without overlap. Batches on different pickers are free to
        run in parallel (no constraint between them).
        """
        picker_assignments = solution_info.get("picker_assignments", {})
        batch_times = solution_info.get("batch_times", {})
        batch_completions = solution_info.get("batch_completions", {})

        for picker in P:
            batches = [b for b, p in picker_assignments.items() if p == picker]
            intervals = sorted(
                (
                    batch_completions[b] - batch_times[b],
                    batch_completions[b],
                    b,
                )
                for b in batches
            )
            for i in range(len(intervals) - 1):
                end_i = intervals[i][1]
                start_next = intervals[i + 1][0]
                self.assertGreaterEqual(
                    start_next,
                    end_i - 1e-6,
                    f"Time overlap on picker {picker}: {intervals[i]} vs {intervals[i + 1]}",
                )
