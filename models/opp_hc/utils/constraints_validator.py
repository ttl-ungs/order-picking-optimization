"""
Constraints validator for opp_hc.

Extends the base validator (models/utils/base_constraints_validator.py: all
topology/capacity/assignment constraints, enforced as HARD constraints via
validate_solution()) with cold-chain eligibility. Unlike those, cold chain is
deliberately NOT folded into validate_solution():

validate_solution() runs once, right after the initial construction. If a
cold-chain-ineligible batch made it fail, the WHOLE initial solution would be
thrown away and the Hill Climbing loop would never get to run the 2-opt and
reassignment moves that might fix that one batch.

So cold chain is a SOFT constraint during the search (see
cold_chain_violation(), consumed as a large cost penalty by opp_hc.py's
_search_cost/_route_local_search_cost) and a HARD constraint only on what is
reported as the final answer (see validate_cold_chain_strict(), used by
opp_hc.py's solve() to decide what may become best_feasible_solution).
validate_solution() itself checks ONLY the base hard constraints: an initial
solution with a cold-chain-ineligible batch is accepted, and Hill Climbing
gets a full-budget chance to fix it, guided by the penalty biasing the
accept/reject decisions towards compliance.
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

        # Incremental cold_chain_violation() cache -- see
        # cold_chain_violation_incremental()'s docstring. _last_* reflects
        # the last COMMITTED solution (commit()); _pending_* is the tentative
        # result of the most recent cold_chain_violation_incremental() call,
        # promoted to _last_* only if that same solution gets committed.
        self._last_solution = None
        self._last_overrun_by_batch: Dict[str, float] = {}
        self._last_total_violation = 0.0
        self._pending_solution = None
        self._pending_overrun_by_batch: Dict[str, float] = {}
        self._pending_total_violation = 0.0

    def validate_solution(self, solution) -> bool:
        """
        The base hard constraints only (topology, capacity,
        exactly-one-picker-per-batch) -- cold chain is intentionally NOT
        checked here anymore (see module docstring). An initial solution
        with a cold-chain-ineligible batch is still accepted here, so Hill
        Climbing gets a chance to fix it.
        """
        return super().validate_solution(solution)

    def validate_cold_chain_strict(self, solution) -> bool:
        """
        HARD cold-chain check: every batch with orders must be assigned to
        a picker whose T_exec_pb is within T_cold. Used to decide
        whether a solution may become the reported best_feasible_solution
        -- NOT used to gate the search itself (see cold_chain_violation()
        for that; module docstring explains why).
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
        Total cold-chain overrun across every batch with orders: sum of
        max(0, T_exec_pb[assigned_picker, b] - T_cold - COLD_CHAIN_TOLERANCE).
        Zero exactly when validate_cold_chain_strict() would return True --
        the tolerance is subtracted here too, so a T_exec_pb within tolerance
        of T_cold has no overrun (otherwise a solution could never reach the
        zero-violation state validate_cold_chain_strict() accepts). Consumed by opp_hc.py as a large
        search-cost penalty, so Hill Climbing is biased toward (and, once
        it reaches zero, satisfies) cold chain without needing to
        hard-reject a solution that hasn't gotten there yet.
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
        """This batch's own contribution to cold_chain_violation()'s total
        -- see that method's docstring for why it can be computed (and
        cached) independently, per batch."""
        orders = self.batch_assignments.get(batch)
        if not orders:
            return 0.0

        picker = solution.get_batch_picker(batch)
        if picker is None or picker not in self.P:
            return 0.0

        route = solution.get_batch_route(batch)
        return max(0.0, self.T_exec_pb(batch, route, picker) - self.T_cold - COLD_CHAIN_TOLERANCE)

    def _diff_batches(self, a, b) -> Set[str]:
        """Batches whose route or assigned picker differs between two
        solutions (a sequence-order-only change, e.g. a swap move, reports
        no differing batches here -- cold chain doesn't depend on
        position/order, only on (batch, route, picker))."""
        changed = set()
        for batch in self.B:
            if a.get_batch_route(batch) != b.get_batch_route(batch):
                changed.add(batch)
            elif a.get_batch_picker(batch) != b.get_batch_picker(batch):
                changed.add(batch)
        return changed

    def cold_chain_violation_incremental(self, solution) -> float:
        """
        Same value cold_chain_violation(solution) would return, computed as
        a delta from the last COMMITTED solution (see commit()) instead of
        recomputing every batch's T_exec_pb from scratch every call: unlike
        the objective's completion times (which cascade through a picker's
        whole sequence), a batch's cold-chain overrun depends only on its
        OWN route and picker, never on other batches or on sequence order
        -- so only batches that actually changed need their overrun
        recomputed; everything else is reused from the cache untouched.

        Does NOT mutate the committed cache itself -- see commit(), which
        solve() calls only once it has decided to keep `solution` as the
        new current_solution (a candidate that gets scored here and then
        rejected must not corrupt the cache the NEXT candidate diffs
        against).
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
        """Make `solution` the baseline cold_chain_violation_incremental()
        diffs against from now on. Call this exactly when solve() accepts
        `solution` as the new current_solution -- never for a candidate
        that ends up rejected."""
        if self._pending_solution is solution:
            self._last_solution = solution
            self._last_overrun_by_batch = self._pending_overrun_by_batch
            self._last_total_violation = self._pending_total_violation
            return

        # solution wasn't the one most recently scored incrementally
        # (shouldn't happen given how solve() uses this class -- defensive
        # fallback so the cache can't silently go stale/incorrect instead).
        self._last_solution = solution
        self._last_overrun_by_batch = {b: self._batch_overrun(b, solution) for b in self.B}
        self._last_total_violation = sum(self._last_overrun_by_batch.values())

    def T_exec_pb(self, batch: str, route: list, picker: str) -> float:
        """Same formula as opp_split_stage2_scheduling.zpl's T_exec_pb: fixed setup/
        picking time (speed-independent) plus travel+service time divided
        by the picker's speed."""
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
