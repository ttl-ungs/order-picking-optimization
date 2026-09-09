"""
Constraints validator for opp_hc_4.

Extends opp_hc_2's validator (all topology/capacity/assignment constraints,
unchanged) with a cold-chain eligibility check: a batch's route may only be
paired with a picker whose speed keeps t_exec_pb[p, b] within T_frio_max.
This mirrors how stage2_scheduling.zpl restricts X_pb's domain to PB_elig
instead of adding a separate constraint (see models/opp_v5/utils/
cold_chain_validation.py) - here it is enforced as a hard feasibility check
on the assignment, the same way every other opp_hc_2 constraint is.

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
        """All opp_hc_2 constraints, plus cold-chain eligibility per batch."""
        if not super().validate_solution(solution):
            return False
        return self._validate_cold_chain(solution)

    def _validate_cold_chain(self, solution) -> bool:
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
        t_exec that scales with picker speed (opp_v5's R_b_time)."""
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
