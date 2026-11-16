"""
Constraints validator for opp_aco.

Extends the base validator (models/utils/base_constraints_validator.py: all
topology/capacity/assignment constraints, enforced as HARD constraints via
validate_solution()) with cold-chain eligibility. Unlike those, cold chain is
deliberately NOT folded into validate_solution():

A SINGLE batch with a tight cold-chain margin would make validate_solution()
reject the WHOLE ant solution (every batch, not just the tight one). If no ant
happened to build a short-enough route for that batch, no ant solution of an
iteration would validate, and the pheromones (evaporation AND deposit are only
called on validated solutions) would never update, freezing the search.

So cold chain is a SOFT constraint during the search (see
cold_chain_violation(), consumed as a large objective penalty by
models/opp_aco/utils/route_evaluator.py) and a HARD constraint only on what is
reported as the final answer (see validate_cold_chain_strict(), called from
opp_aco.py's main loop to decide what may become best_global_solution).
validate_solution() itself checks ONLY the base hard constraints, so every ant
that clears them deposits pheromone (route AND picker-assignment edges) and the
search keeps learning good routes and assignments for every other batch while
one stays cold-chain-tight; the penalty biases the roulette and the deposits
towards the picker that gets closest to (and eventually within) T_cold.
"""

from typing import Dict, List, Set

from models.utils.base_constraints_validator import (
    ConstraintsValidator as BaseConstraintsValidator,
)
from models.opp_aco.utils import exec_time
from models.opp_split.utils.cold_chain_validation import COLD_CHAIN_TOLERANCE


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
        The base hard constraints only (topology, capacity,
        exactly-one-picker-per-batch) -- cold chain is intentionally NOT
        checked here anymore (see module docstring). This is what gates
        pheromone updates: any ant clearing this deposits pheromone,
        regardless of whether it also happens to violate cold chain.
        """
        return super().validate_solution(solution)

    def validate_cold_chain_strict(self, solution) -> bool:
        """
        HARD cold-chain check: every batch with orders must be assigned to
        a picker whose T_exec_pb is within T_cold. Used to decide
        whether a solution may become the reported best_global_solution --
        NOT used to gate pheromone updates (see cold_chain_violation() for
        that; module docstring explains why).
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
        of T_cold has no overrun (otherwise a solution that
        validate_cold_chain_strict accepts could still be kept out of
        feasible_ant_solutions in opp_aco.py's main loop). Consumed by RouteEvaluator as a large objective
        penalty, so the search is biased toward (and, once it reaches
        zero, satisfies) cold chain without needing to hard-reject every
        ant that hasn't gotten there yet.
        """
        total = 0.0
        for batch in self.B:
            orders = self.batch_assignments.get(batch)
            if not orders:
                continue

            picker = solution.get_batch_picker(batch)
            if picker is None or picker not in self.P:
                # Structurally invalid (should never reach here in
                # practice: validate_solution() already rejects this
                # before cold_chain_violation() is ever called on it).
                continue

            route = solution.get_batch_route(batch)
            overrun = self.T_exec_pb(batch, route, picker) - self.T_cold - COLD_CHAIN_TOLERANCE
            if overrun > 0:
                total += overrun

        return total

    def compliant_batches(self, solution) -> Set[str]:
        """
        Batch ids that are individually cold-chain-compliant under
        `solution` (or have no orders, trivially compliant). Used to
        decide, per batch, whether that batch's route/picker-assignment
        pheromone should be deposited for this ant -- see opp_aco.py's
        _deposit_solution docstring for why deposit is filtered this way
        instead of all-or-nothing per solution.
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
        """Same formula as opp_split_stage2_scheduling.zpl's T_exec_pb: fixed setup/
        picking time (speed-independent) plus travel+service time divided
        by the picker's speed."""
        orders = self.batch_assignments.get(batch, set())
        return exec_time.T_exec_pb(
            self.location_graph, route, orders, picker,
            self.C_n, self.T_setup, self.T_pick, self.T_travel, self.S, self.V_p,
        )

    def _route_time(self, route: list) -> float:
        """Travel time (T_travel * distance) + service time -- the part of
        t_exec that scales with picker speed (opp_split's R_b)."""
        return exec_time.route_time(self.location_graph, route, self.T_travel, self.S)
