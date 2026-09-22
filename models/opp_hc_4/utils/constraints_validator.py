"""
Constraints validator for opp_hc_4.

Extends opp_hc_2's validator (all topology/capacity/assignment constraints,
unchanged and still enforced as HARD constraints via validate_solution())
with cold-chain eligibility. Unlike those, cold chain is deliberately NOT
folded into validate_solution() -- see the 2026-09-10 audit finding this
addresses:

Cold chain used to be an extra hard check inside validate_solution(),
called once right after the initial construction (opp_hc_4.py's
_generate_initial_feasible_solution) and never again. That meant a batch
that came out cold-chain-ineligible under its initial (heuristic) route
made the WHOLE initial solution get thrown away immediately -- the Hill
Climbing loop never got a chance to run 2-opt/reassignment moves that
might have fixed just that one batch, because there was no solution left
to run them on.

Fix: cold chain is now a SOFT constraint during search (see
cold_chain_violation(), consumed as a large cost penalty by
opp_hc_4.py's _search_cost/_route_local_search_cost) and a HARD
constraint only on what gets reported as the final answer (see
validate_cold_chain_strict(), used by opp_hc_4.py's solve() to decide
what may become best_feasible_solution). validate_solution() itself now
checks ONLY opp_hc_2's original hard constraints (topology/capacity/
one-picker-per-batch) -- an initial solution with a cold-chain-ineligible
batch is no longer discarded outright; Hill Climbing gets a real,
full-budget chance to fix it via 2-opt/reassignment, guided by the
penalty naturally biasing accept/reject decisions towards compliance.

No congestion here (unlike opp_hc_3): this model's only addition over
opp_hc_2 is picker speed + cold chain, kept orthogonal to congestion.
"""

from typing import Dict, List, Set

from models.opp_hc_2.utils.constraints_validator import (
    ConstraintsValidator as BaseConstraintsValidator,
)


class ConstraintsValidator(BaseConstraintsValidator):
    """opp_hc_2's validator plus a cold-chain eligibility check on X_pb."""

    def __init__(
        self,
        N: Set,
        B: Set,
        location_graph,
        batch_assignments: Dict[str, Set[str]],
        C_n: Dict,
        C_v: float,
        A: Dict,
        B_time: float,
        B_setup: float,
        B_picking: float,
        S: Dict,
        V_p: Dict[str, float],
        T_frio_max: float,
        P: List[str] = None,
    ):
        super().__init__(N, B, location_graph, batch_assignments, C_n, C_v, A, P)
        self.B_time = B_time
        self.B_setup = B_setup
        self.B_picking = B_picking
        self.S = S if isinstance(S, dict) else {}
        self.V_p = V_p or {}
        self.T_frio_max = T_frio_max

    def validate_solution(self, solution) -> bool:
        """
        opp_hc_2's ORIGINAL hard constraints only (topology, capacity,
        exactly-one-picker-per-batch) -- cold chain is intentionally NOT
        checked here anymore (see module docstring). An initial solution
        with a cold-chain-ineligible batch is still accepted here, so Hill
        Climbing gets a chance to fix it.
        """
        return super().validate_solution(solution)

    def validate_cold_chain_strict(self, solution) -> bool:
        """
        HARD cold-chain check: every batch with orders must be assigned to
        a picker whose t_exec_pb is within T_frio_max. Used to decide
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
            if self.t_exec_pb(batch, route, picker) > self.T_frio_max + 1e-9:
                return False

        return True

    def cold_chain_violation(self, solution) -> float:
        """
        Total cold-chain overrun across every batch with orders: sum of
        max(0, t_exec_pb[assigned_picker, b] - T_frio_max). Zero exactly
        when validate_cold_chain_strict() would return True. Consumed by
        opp_hc_4.py as a large search-cost penalty, so Hill Climbing is
        biased toward (and, once it reaches zero, satisfies) cold chain
        without needing to hard-reject a solution that hasn't gotten there
        yet.
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
            overrun = self.t_exec_pb(batch, route, picker) - self.T_frio_max
            if overrun > 0:
                total += overrun

        return total

    def t_exec_pb(self, batch: str, route: list, picker: str) -> float:
        """Same formula as stage2_scheduling.zpl's t_exec_pb: fixed setup/
        picking time (speed-independent) plus travel+service time divided
        by the picker's speed."""
        fixed_time = self.B_setup + self.B_picking * sum(
            self.C_n.get(order, 0) for order in self.batch_assignments.get(batch, set())
        )
        speed = self.V_p.get(picker, 1.0)
        return fixed_time + self._route_time(route) / speed

    def _route_time(self, route: list) -> float:
        """Travel time (B_time * distance) + service time -- the part of
        t_exec that scales with picker speed (opp_v5_2_split's R_b_time)."""
        if not route:
            return 0.0

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        distance = self.location_graph.get_distance(depot, route[0])
        for i in range(len(route) - 1):
            distance += self.location_graph.get_distance(route[i], route[i + 1])
        distance += self.location_graph.get_distance(route[-1], final)

        service_time = sum(self.S.get(loc, 0) for loc in route)

        return self.B_time * distance + service_time
