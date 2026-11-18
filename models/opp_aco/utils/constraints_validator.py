"""
Constraints validator for opp_aco.

Extends the base validator (topology, capacity and assignment, all hard) with
the cold chain, which is deliberately kept out of validate_solution(): one
batch with a tight margin would make it reject the ant's whole solution, and
if no ant built a short enough route for that batch no solution of the
iteration would validate and the pheromone would never update. So the cold
chain is soft during the search (cold_chain_violation(), an objective penalty
in route_evaluator.py) and hard only on the reported answer (only a solution
with cold_chain_violation() == 0 is kept as the answer).
"""

from typing import Dict, List, Set

from models.utils.base_constraints_validator import (
    ConstraintsValidator as BaseConstraintsValidator,
)
from models.opp_aco.utils import exec_time
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

    def validate_solution(self, solution) -> bool:
        """
        The base hard constraints only (topology, capacity, one picker per
        batch). This is what gates the pheromone updates; the cold chain is
        not checked here (see the module docstring).
        """
        return super().validate_solution(solution)

    def cold_chain_violation(self, solution) -> float:
        """
        Total cold-chain overrun: the sum over the batches with orders of
        max(0, T_exec_pb[picker, b] - T_cold - COLD_CHAIN_TOLERANCE). It is
        zero exactly when every batch with orders is within T_cold (the
        tolerance is subtracted here too, so that state is reachable); only
        such solutions are reported.
        """
        total = 0.0
        for batch in self.B:
            orders = self.batch_assignments.get(batch)
            if not orders:
                continue

            picker = solution.get_batch_picker(batch)
            if picker is None or picker not in self.P:
                # Structurally invalid; validate_solution() rejects it first.
                continue

            route = solution.get_batch_route(batch)
            overrun = self.T_exec_pb(batch, route, picker) - self.T_cold - COLD_CHAIN_TOLERANCE
            if overrun > 0:
                total += overrun

        return total

    def compliant_batches(self, solution) -> Set[str]:
        """
        Batches that are cold-chain-compliant on their own under `solution`
        (a batch without orders is). Only these deposit pheromone for the ant
        (see opp_aco.py's _deposit_solution).
        """
        compliant = set()
        for batch in self.B:
            orders = self.batch_assignments.get(batch)
            if not orders:
                compliant.add(batch)
                continue

            picker = solution.get_batch_picker(batch)
            if picker is None or picker not in self.P:
                continue

            route = solution.get_batch_route(batch)
            if self.T_exec_pb(batch, route, picker) <= self.T_cold + 1e-9:
                compliant.add(batch)

        return compliant

    def T_exec_pb(self, batch: str, route: list, picker: str) -> float:
        """T_exec_pb as in opp_split_stage2_scheduling.zpl: setup and picking
        time plus the travel + service time divided by the picker's speed."""
        orders = self.batch_assignments.get(batch, set())
        return exec_time.T_exec_pb(
            self.location_graph, route, orders, picker,
            self.C_n, self.T_setup, self.T_pick, self.T_travel, self.S, self.V_p,
        )

    def _route_time(self, route: list) -> float:
        """Travel time (T_travel * distance) + service time -- the part of
        t_exec that scales with picker speed (opp_split's R_b)."""
        return exec_time.route_time(self.location_graph, route, self.T_travel, self.S)
