"""
Constraints validator for opp_aco_4.

Extends opp_aco_2's validator (all topology/capacity/assignment
constraints, unchanged and still enforced as HARD constraints via
validate_solution()) with cold-chain eligibility. Unlike those, cold chain
is deliberately NOT folded into validate_solution() -- see the 2026-09-09
audit finding this addresses:

Cold chain used to be an extra hard check inside validate_solution(),
exactly like models/opp_hc_4/utils/constraints_validator.py still does it
for Hill Climbing. That works for HC because 2-opt/reassignment moves are
deterministic and self-restrict to stay eligible. For ACO it back-fired: a
SINGLE batch with a tight cold-chain margin made validate_solution() reject
the WHOLE ant solution (every batch, not just the tight one), so if no ant
ever happened to build a short-enough route for that one batch, NO ant
solution in an entire iteration would ever validate -- pheromones (both
tables) never update (evaporation AND deposit are only ever called on
validated ant_solutions), freezing the search at its initial uniform state
for as long as that batch stays hard. The instance could end up reported
"infeasible" despite the upfront pre-check (batches_without_eligible_picker)
having confirmed a compliant assignment exists.

Fix: cold chain is now a SOFT constraint during search (see
cold_chain_violation(), consumed as a large objective penalty by
models/opp_aco_4/utils/route_evaluator.py) and a HARD constraint only on
what gets reported as the final answer (see validate_cold_chain_strict(),
called from opp_aco_4.py's main loop to decide what may become
best_global_solution). validate_solution() itself now checks ONLY
opp_aco_2's original hard constraints (topology/capacity/one-picker-per-
batch) -- every ant that clears those deposits pheromone (route AND
picker-assignment edges), so the search keeps learning good routes/
assignments for every OTHER batch even while one stays cold-chain-tight,
and the penalty naturally biases the roulette/deposit trajectory towards
whichever picker gets closest to (and eventually within) T_frio_max.

No congestion here (unlike opp_aco_3): this model's only addition over
opp_aco_2 is picker speed + cold chain, kept orthogonal to congestion.
"""

from typing import Dict, List, Set

from models.opp_aco_2.utils.constraints_validator import (
    ConstraintsValidator as BaseConstraintsValidator,
)
from models.opp_aco_4.utils import exec_time
from models.opp_v5_2_split.utils.cold_chain_validation import COLD_CHAIN_TOLERANCE


class ConstraintsValidator(BaseConstraintsValidator):
    """opp_aco_2's validator plus a cold-chain eligibility check on x_pb."""

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
        opp_aco_2's ORIGINAL hard constraints only (topology, capacity,
        exactly-one-picker-per-batch) -- cold chain is intentionally NOT
        checked here anymore (see module docstring). This is what gates
        pheromone updates: any ant clearing this deposits pheromone,
        regardless of whether it also happens to violate cold chain.
        """
        return super().validate_solution(solution)

    def validate_cold_chain_strict(self, solution) -> bool:
        """
        HARD cold-chain check: every batch with orders must be assigned to
        a picker whose t_exec_pb is within T_frio_max. Used to decide
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
            if self.t_exec_pb(batch, route, picker) > self.T_frio_max + COLD_CHAIN_TOLERANCE:
                return False

        return True

    def cold_chain_violation(self, solution) -> float:
        """
        Total cold-chain overrun across every batch with orders: sum of
        max(0, t_exec_pb[assigned_picker, b] - T_frio_max - COLD_CHAIN_TOLERANCE).
        Zero exactly when validate_cold_chain_strict() would return True --
        the tolerance is subtracted here too (2026-09-26 audit finding: it
        used to be omitted, so a t_exec_pb within tolerance of T_frio_max
        still had overrun > 0, kept it out of feasible_ant_solutions in
        opp_aco_4.py's main loop, and could make the whole run report
        "infeasible" despite validate_cold_chain_strict considering it
        compliant). Consumed by RouteEvaluator as a large objective
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
            overrun = self.t_exec_pb(batch, route, picker) - self.T_frio_max - COLD_CHAIN_TOLERANCE
            if overrun > 0:
                total += overrun

        return total

    def compliant_batches(self, solution) -> Set[str]:
        """
        Batch ids that are individually cold-chain-compliant under
        `solution` (or have no orders, trivially compliant). Used to
        decide, per batch, whether that batch's route/picker-assignment
        pheromone should be deposited for this ant -- see opp_aco_4.py's
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
            if self.t_exec_pb(batch, route, picker) <= self.T_frio_max + 1e-9:
                compliant.add(batch)

        return compliant

    def t_exec_pb(self, batch: str, route: list, picker: str) -> float:
        """Same formula as opp_model_v5_2_split_stage2_scheduling.zpl's t_exec_pb: fixed setup/
        picking time (speed-independent) plus travel+service time divided
        by the picker's speed."""
        orders = self.batch_assignments.get(batch, set())
        return exec_time.t_exec_pb(
            self.location_graph, route, orders, picker,
            self.C_n, self.B_setup, self.B_picking, self.B_time, self.S, self.V_p,
        )

    def _route_time(self, route: list) -> float:
        """Travel time (B_time * distance) + service time -- the part of
        t_exec that scales with picker speed (opp_v5_2_split's R_b)."""
        return exec_time.route_time(self.location_graph, route, self.B_time, self.S)
