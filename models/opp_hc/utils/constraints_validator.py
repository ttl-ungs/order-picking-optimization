"""
Constraints validator for opp_hc.

Extends the base validator (topology, capacity and assignment, all hard) with
the cold chain, which is deliberately kept out of validate_solution(): that
check runs once on the initial solution, and rejecting it for one ineligible
batch would throw it away before the search could repair it with 2-opt or a
reassignment. So the cold chain is soft during the search
(cold_chain_violation(), a cost penalty in opp_hc.py) and hard only on the
reported answer (validate_cold_chain_strict()).
"""

from typing import Dict, List, Set

from models.utils.base_constraints_validator import (
    ConstraintsValidator as BaseConstraintsValidator,
)
from models.utils.cold_chain_validation import COLD_CHAIN_TOLERANCE


class ConstraintsValidator(BaseConstraintsValidator):
    """The base validator plus a cold-chain eligibility check on x_pb."""

    def __init__(
        self,
        N: Set,
        B: Set,
        location_graph,
        batch_assignments: Dict[str, Set[str]],
        C_n: Dict,
        C_v: float,
        A: Dict,
        T_travel: float,
        T_setup: float,
        T_pick: float,
        S: Dict,
        V_p: Dict[str, float],
        T_cold: float,
        P: List[str] = None,
    ):
        super().__init__(N, B, location_graph, batch_assignments, C_n, C_v, A, P)
        self.T_travel = T_travel
        self.T_setup = T_setup
        self.T_pick = T_pick
        self.S = S if isinstance(S, dict) else {}
        self.V_p = V_p or {}
        self.T_cold = T_cold

        # Cache of cold_chain_violation_incremental(): _last_* belongs to the
        # last committed solution, _pending_* to the last one scored, which
        # commit() promotes.
        self._last_solution = None
        self._last_overrun_by_batch: Dict[str, float] = {}
        self._last_total_violation = 0.0
        self._pending_solution = None
        self._pending_overrun_by_batch: Dict[str, float] = {}
        self._pending_total_violation = 0.0

    def validate_solution(self, solution) -> bool:
        """
        The base hard constraints only (topology, capacity, one picker per
        batch). The cold chain is not checked here (see the module docstring).
        """
        return super().validate_solution(solution)

    def validate_cold_chain_strict(self, solution) -> bool:
        """
        Hard cold-chain check: every batch with orders is assigned to a picker
        whose T_exec_pb is within T_cold. Decides whether a solution may be
        reported; the search itself uses cold_chain_violation().
        """
        for batch in self.B:
            orders = self.batch_assignments.get(batch)
            if not orders:
                continue

            picker = solution.get_batch_picker(batch)
            if picker is None or picker not in self.P:
                return False

            route = solution.get_batch_route(batch)
            if self.T_exec_pb(batch, route, picker) > self.T_cold + COLD_CHAIN_TOLERANCE:
                return False

        return True

    def cold_chain_violation(self, solution) -> float:
        """
        Total cold-chain overrun: the sum over the batches with orders of
        max(0, T_exec_pb[picker, b] - T_cold - COLD_CHAIN_TOLERANCE). It is
        zero exactly when validate_cold_chain_strict() holds (the tolerance
        is subtracted here too, so that state is reachable).
        """
        total = 0.0
        for batch in self.B:
            orders = self.batch_assignments.get(batch)
            if not orders:
                continue

            picker = solution.get_batch_picker(batch)
            if picker is None or picker not in self.P:
                continue

            route = solution.get_batch_route(batch)
            overrun = self.T_exec_pb(batch, route, picker) - self.T_cold - COLD_CHAIN_TOLERANCE
            if overrun > 0:
                total += overrun

        return total

    def _batch_overrun(self, batch: str, solution) -> float:
        """Overrun of one batch; it depends only on the batch's own route and picker."""
        orders = self.batch_assignments.get(batch)
        if not orders:
            return 0.0

        picker = solution.get_batch_picker(batch)
        if picker is None or picker not in self.P:
            return 0.0

        route = solution.get_batch_route(batch)
        return max(0.0, self.T_exec_pb(batch, route, picker) - self.T_cold - COLD_CHAIN_TOLERANCE)

    def _diff_batches(self, a, b) -> Set[str]:
        """Batches whose route or picker differs between two solutions (a
        change of sequence order alone does not affect the cold chain)."""
        changed = set()
        for batch in self.B:
            if a.get_batch_route(batch) != b.get_batch_route(batch):
                changed.add(batch)
            elif a.get_batch_picker(batch) != b.get_batch_picker(batch):
                changed.add(batch)
        return changed

    def cold_chain_violation_incremental(self, solution) -> float:
        """
        Same value as cold_chain_violation(solution), computed as a delta from
        the last committed solution: a batch's overrun depends only on its
        own route and picker, so only the batches that changed are recomputed.

        The committed cache is not touched: solve() calls commit() only when
        it keeps `solution`, so a rejected candidate cannot corrupt the
        baseline of the next one.
        """
        if self._last_solution is None:
            total = self.cold_chain_violation(solution)
            self._pending_overrun_by_batch = {b: self._batch_overrun(b, solution) for b in self.B}
            self._pending_total_violation = total
            self._pending_solution = solution
            return total

        changed = self._diff_batches(self._last_solution, solution)
        if not changed:
            self._pending_solution = solution
            self._pending_overrun_by_batch = self._last_overrun_by_batch
            self._pending_total_violation = self._last_total_violation
            return self._last_total_violation

        total = self._last_total_violation
        overrun_by_batch = dict(self._last_overrun_by_batch)
        for batch in changed:
            new_overrun = self._batch_overrun(batch, solution)
            total += new_overrun - overrun_by_batch.get(batch, 0.0)
            overrun_by_batch[batch] = new_overrun

        self._pending_overrun_by_batch = overrun_by_batch
        self._pending_total_violation = total
        self._pending_solution = solution
        return total

    def commit(self, solution) -> None:
        """Make `solution` the baseline of cold_chain_violation_incremental().
        Call it exactly when solve() accepts `solution`."""
        if self._pending_solution is solution:
            self._last_solution = solution
            self._last_overrun_by_batch = self._pending_overrun_by_batch
            self._last_total_violation = self._pending_total_violation
            return

        # Defensive: `solution` was not the last one scored incrementally.
        self._last_solution = solution
        self._last_overrun_by_batch = {b: self._batch_overrun(b, solution) for b in self.B}
        self._last_total_violation = sum(self._last_overrun_by_batch.values())

    def T_exec_pb(self, batch: str, route: list, picker: str) -> float:
        """T_exec_pb as in opp_split_stage2_scheduling.zpl: setup and picking
        time plus the travel + service time divided by the picker's speed."""
        fixed_time = self.T_setup + self.T_pick * sum(
            self.C_n.get(order, 0) for order in self.batch_assignments.get(batch, set())
        )
        speed = self.V_p.get(picker, 1.0)
        return fixed_time + self._route_time(route) / speed

    def _route_time(self, route: list) -> float:
        """Travel time (T_travel * distance) + service time -- the part of
        t_exec that scales with picker speed (opp_split's R_b)."""
        if not route:
            return 0.0

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        distance = self.location_graph.get_distance(depot, route[0])
        for i in range(len(route) - 1):
            distance += self.location_graph.get_distance(route[i], route[i + 1])
        distance += self.location_graph.get_distance(route[-1], final)

        service_time = sum(self.S.get(loc, 0) for loc in route)

        return self.T_travel * distance + service_time
