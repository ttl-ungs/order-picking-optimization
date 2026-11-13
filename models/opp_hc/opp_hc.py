"""
Hill Climbing heuristic for OPP v4 with picker speed and cold chain.

Same problem as opp_hc_2 (multi-picker, all constraints validated):
- Receives: same SolveModelDTO parameters, plus a set of pickers (P)
- Validates: ALL constraints from opp_hc_2, plus cold-chain eligibility
- Optimizes: routes within batches (2-opt) AND the assignment/sequencing of
  batches to pickers, so that batches on different pickers run in parallel
  and batches on the same picker are sequenced without overlap
- Output: compatible with build_output

Added on top of opp_hc_2 - picker speed and cold chain, the Hill Climbing
counterpart of opp_split's opp_split_stage2_scheduling.zpl additions over opp_v4:

- Picker speed (V_p): a batch's execution time is no longer a single
  d_b fixed for every picker. Instead T_exec_pb[p, b] = fixed_time(b)
  + route_time(b) / V_p[p], where fixed_time (setup + picking) doesn't
  depend on speed and route_time (travel + service) does. Faster pickers
  finish the same route sooner.
- Cold chain (T_cold): a (picker, batch) pair is only eligible if
  T_exec_pb[p, b] <= T_cold.

Cold chain is enforced as a HARD constraint on the reported final answer,
but a SOFT one (a large cost penalty, _search_cost/_route_local_search_
cost) during the search itself -- see models/opp_hc/utils/
constraints_validator.py's module docstring for the 2026-09-10 audit
finding this fixes (a cold-chain-ineligible batch used to make the
initial solution get discarded outright, right after construction,
before Hill Climbing ever got a chance to fix it via 2-opt/reassignment).

Infeasibility detection is now HONEST: there is no upfront estimate-based
pre-check that can produce a false "infeasible" before the search ever
gets to try (a 2026-09-09 audit finding -- an earlier version of this
file pre-checked batches_without_eligible_picker against the initial
(heuristic, even after 2-opt-tightening) route, which could still be
worse than what further search would achieve, incorrectly declaring a
genuinely feasible instance infeasible). The ONLY upfront short-circuit
left is mathematically exact, not an estimate: batches_without_eligible_
picker is fed a route_time of EXACTLY 0.0 for every batch (the best
physically possible case -- real route_time is always >= 0), so a batch
flagged there is impossible under ANY route/picker whatsoever, not just
the one this run happened to construct. Every other batch gets a genuine
full run of the Hill Climbing loop; the reported answer (best_feasible_
solution) is only ever set when every batch is fully cold-chain-compliant
(see solve()), so if the loop finishes without ever reaching that,
"infeasible" reflects an honest, exhausted search budget -- not a
shortcut that gave up before trying.

Search scheme and sources. The main loop is stochastic, first-improvement
hill climbing (Hoos & Stuetzle 2004, "Stochastic Local Search:
Foundations and Applications"; see also Talbi 2009, "Metaheuristics: From
Design to Implementation", ch. 2): each iteration draws ONE random move
and ONE random neighbor and accepts it iff it lowers the current cost --
it does not scan the whole neighborhood first (not steepest descent). The
one exception is inside the route move, which takes the best 2-opt
reversal of the chosen batch's route (Croes 1958, "A method for solving
traveling-salesman problems"). The neighborhoods -- reassign a batch to
another picker, swap two batches in a picker's sequence -- play the role
of the swap/insert moves Coruzzolo et al. (2023), Logistics 7:61, use in
their local search for order batching/sequencing; the nearest-neighbor
initial routing follows their routing step (p.9). None of the papers in
the thesis bibliography uses Hill Climbing itself; the initial-route
portfolio (_initial_route) cites its own sources.

Deliberately WITHOUT congestion between concurrent pickers (unlike
opp_hc_3): congestion and picker-speed/cold-chain are orthogonal additions
over opp_hc_2, and this model only needs the latter. Adding congestion on
top would require re-pricing T_exec_pb's route/service time against other
pickers' reservations (models/utils/congestion.py::CongestionTracker) every
time a batch's route OR its assigned picker's speed changes - left out here
to keep the search space (and what's being measured) focused on the
speed/cold-chain trade-off, matching opp_split itself, which also has no
congestion (see analysis/config.py).
"""

import time
import random
from typing import Dict, List, Set, Optional, Tuple

from dtos.hc.solve_hc_model_dto import SolveHCModelDTO
from dtos.opp.solve_result import SolveResult
from dtos.opp.solution_record_dto import SolutionRecordDTO
import models.utils.solve_registry as solve_registry
import models.utils.route_construction as route_construction
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO
from models.utils.route_solution import RouteSolution
from models.opp_hc.utils.route_evaluator import RouteEvaluator
from models.opp_hc.utils.constraints_validator import ConstraintsValidator
from models.opp_split.utils.cold_chain_validation import batches_without_eligible_picker, invalid_speeds
from models.utils.input_validation import orders_without_exactly_one_batch
from models.utils.sla import sla_on_time_pct


class OPPHillClimbing(Model):
    """Hill Climbing solver for OPP v4 - picker speed + cold chain, no congestion."""

    # Multiplier applied to a cold-chain overrun (a time-unit amount)
    # before adding it to a search cost -- see constraints_validator.py's
    # module docstring for why cold chain is a SOFT constraint during
    # search now (2026-09-10 audit fix). Large enough to dominate the
    # search away from violations (typical marginal objective contribution
    # per unit of recollection time is W_c, usually single-to-low-
    # double digits) without using an arbitrarily huge Big-M-style
    # constant -- this is a plain Python cost comparison, not a MIP
    # constraint, so there's no SCIP-presolve-numerics failure mode to
    # worry about the way there was with opp_split's M_seq.
    _COLD_CHAIN_PENALTY_WEIGHT = 1000.0

    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time
        self.P = sorted(dto.P) if getattr(dto, "P", None) else ["P1"]
        self._undirected_adjacency = route_construction.undirected_adjacency(self.location_graph)
        self._reversed_graph = route_construction.reversed_graph(self.location_graph)
        # Per-solve() caches for values that are invariant for the whole
        # search (batch_assignments never changes once a run starts -- only
        # picker/route/sequence do): reset at the top of solve(), read-only
        # afterwards. See _fixed_time and _generate_feasible_neighbor.
        self._fixed_time_cache: Dict[str, float] = {}
        self._batches_with_orders_cache: List[str] = []

    def solve(self, params: SolveHCModelDTO):
        """
        Solve OPP v4 using Hill Climbing on routes with full constraint
        validation, picker speed and cold chain eligibility.
        """
        if params.Seed is not None:
            random.seed(params.Seed)

        wall_clock_start = time.time()

        if params.B_nb is None:
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        if not (params.is_capacity_valid() and params.is_batch_assignment_valid()):
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        # is_batch_assignment_valid only rejects an order in TWO+ batches.
        unassigned_or_duplicated = orders_without_exactly_one_batch(params.B_nb, self.N)
        if unassigned_or_duplicated:
            print(
                "ERROR: every order must be in exactly one batch; not the case for "
                f"{sorted(unassigned_or_duplicated)}"
            )
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        batch_assignments = params.extract_batch_assignments()

        # batch_assignments is fixed for the rest of this run (only picker/
        # route/sequence change during search), so these two per-batch
        # values -- recomputed from scratch on every call otherwise -- can
        # be built once here instead.
        self._fixed_time_cache = {}
        self._batches_with_orders_cache = [b for b in self.B if batch_assignments[b]]

        # V_p[p] is a divisor in _T_exec_pb (fixed_time(b) + route_time(b)
        # / V_p[p]): a speed of exactly 0 is a ZeroDivisionError waiting
        # to happen the first time any batch/picker pair gets evaluated
        # (the eligibility pre-check below, if nothing else); a negative
        # one silently produces a negative T_exec_pb that would look
        # "eligible" for any T_cold. Reject up front instead of
        # crashing or accepting nonsensical input (2026-09-10 audit finding).
        bad_speeds = invalid_speeds(self._picker_speeds(params))
        if bad_speeds:
            print(f"ERROR: V_p must be strictly positive for every picker; got non-positive speed for {sorted(bad_speeds)}")
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        # Exact (not estimated) impossibility pre-check: fixed_time(b)
        # alone (setup + picking, independent of route/picker) already
        # tells us the BEST possible T_exec_pb for any picker, since
        # route_time is always >= 0 -- feeding batches_without_eligible_
        # picker a route_time of exactly 0.0 for every batch asks it "is
        # there a picker fast enough even for a zero-distance route?". A
        # batch flagged here is impossible under ANY route or picker, not
        # just one this run happened to construct -- unlike the estimate-
        # based pre-check this replaces (2026-09-09 audit finding). See
        # header for the full rationale.
        best_case_route_time = {batch: 0.0 for batch in self.B}
        impossible_batches = batches_without_eligible_picker(
            self.P, self.B, self.N, params.C_n, params.B_nb,
            params.T_setup, params.T_pick, best_case_route_time,
            self._picker_speeds(params), params.T_cold,
        )
        if impossible_batches:
            print(
                "ERROR: No picker satisfies the cold-chain deadline for "
                f"batches {sorted(impossible_batches)}, even with a zero-distance route"
            )
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        validator = ConstraintsValidator(
            N=self.N,
            B=self.B,
            location_graph=self.location_graph,
            batch_assignments=batch_assignments,
            C_n=params.C_n,
            C_v=params.C_v,
            A=params.A,
            T_travel=params.T_travel,
            T_setup=params.T_setup,
            T_pick=params.T_pick,
            S=params.S,
            V_p=params.V_p,
            T_cold=params.T_cold,
            P=self.P,
        )

        evaluator = RouteEvaluator(
            N=self.N,
            B=self.B,
            P=self.P,
            location_graph=self.location_graph,
            batch_assignments=batch_assignments,
            W_c=params.W_c,
            W_pen=params.W_pen,
            W_e=params.W_e,
            W_t=params.W_t,
            C_n=params.C_n,
            C_v=params.C_v,
            A=params.A,
            T_travel=params.T_travel,
            T_setup=params.T_setup,
            T_pick=params.T_pick,
            S=params.S,
            T_due_n=params.T_due_n,
            M=params.M,
            V_p=params.V_p,
        )

        max_iterations = params.Max_it
        max_no_improvement = params.Max_imp

        current_solution = self._generate_initial_feasible_solution(
            batch_assignments, validator, params
        )

        if current_solution is None:
            print("ERROR: Could not generate initial feasible solution")
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        # current_cost drives ACCEPT/REJECT decisions during the search
        # (objective + cold-chain penalty, see _search_cost) -- it is NOT
        # the reported obj_val. best_feasible_solution/best_feasible_cost
        # (tracked separately, using the real objective with zero penalty)
        # are what actually get reported: the search is free to wander
        # through cold-chain-violating states along the way, but only ever
        # reports one that's fully compliant.
        current_cost, current_objective, current_violation = self._search_cost(current_solution, evaluator, validator)
        evaluator.commit(current_solution)
        validator.commit(current_solution)

        best_feasible_solution = None
        best_feasible_cost = float("inf")
        # "Iteration of convergence": WHEN best_feasible_solution was last
        # improved (not current_cost/search_cost, which can wander through
        # cold-chain-violating states -- see comment above). 0 means the
        # initial construction was already the best feasible answer found.
        best_found_at_iteration = 0
        if current_violation == 0.0:
            best_feasible_solution = current_solution.copy()
            best_feasible_cost = current_objective

        max_time = params.Max_time if getattr(params, "Max_time", None) else 30.0

        iteration = 0
        no_improvement_count = 0
        timed_out = False

        while iteration < max_iterations and no_improvement_count < max_no_improvement:
            if time.time() - wall_clock_start > max_time:
                timed_out = True
                break

            iteration += 1

            neighbor_solution = self._generate_feasible_neighbor(
                current_solution, batch_assignments, params
            )

            if neighbor_solution is None:
                no_improvement_count += 1
                continue

            neighbor_cost, neighbor_objective, neighbor_violation = self._search_cost(
                neighbor_solution, evaluator, validator
            )

            # First-improvement acceptance of one random neighbor
            # (stochastic hill climbing, Hoos & Stuetzle 2004 -- see header).
            if neighbor_cost < current_cost:
                current_solution = neighbor_solution
                current_cost = neighbor_cost
                no_improvement_count = 0
                evaluator.commit(current_solution)
                validator.commit(current_solution)

                if neighbor_violation == 0.0:
                    true_cost = neighbor_objective
                    if true_cost < best_feasible_cost:
                        best_feasible_solution = current_solution.copy()
                        best_feasible_cost = true_cost
                        best_found_at_iteration = iteration
            else:
                no_improvement_count += 1

        elapsed = time.time() - wall_clock_start

        print(f"\nHill Climbing execution time: {elapsed:.4f}s")
        print(f"Iterations: {iteration}" + (" (stopped: time budget exceeded)" if timed_out else ""))

        if best_feasible_solution is None:
            # The search ran its full budget (iterations, stagnation, or
            # time) and never reached a cold-chain-compliant solution --
            # an honest "infeasible", not a shortcut that gave up before
            # trying (see header/constraints_validator.py docstrings).
            print("ERROR: Hill Climbing never found a cold-chain-compliant solution within its search budget")
            self._register_infeasible(params, elapsed)
            return "infeasible", None

        print(f"Final objective value: {best_feasible_cost:.4f}")

        output = self._build_solution_output(best_feasible_solution)

        solution_info = self._build_solution_info(best_feasible_solution, best_feasible_cost, params)
        super().notify(solution_info=solution_info)

        solve_result = SolveResult(
            status="optimal",
            output=output,
            elapsed=elapsed,
            params={
                "obj_val": best_feasible_cost,
                "sla_on_time_pct": sla_on_time_pct(solution_info["tardiness"]),
                "W_c": params.W_c,
                "W_pen": params.W_pen,
                "W_e": params.W_e,
                "W_t": params.W_t,
                "C_v": params.C_v,
                "T_travel": params.T_travel,
                "T_setup": params.T_setup,
                "T_pick": params.T_pick,
                "M": params.M,
                "V_p": dict(params.V_p),
                "T_cold": params.T_cold,
                "N": len(self.N),
                "B": len(self.B),
                "P": len(self.P),
                "V": len(self.location_graph.get_vertices()),
                "Max_it": params.Max_it,
                "Max_imp": params.Max_imp,
                "iterations_run": iteration,
                "best_found_at_iteration": best_found_at_iteration,
            },
        )
        solve_result.solution_record = SolutionRecordDTO(
            model_name="opp_hc",
            N=self.N,
            B=self.B,
            P=self.P,
            location_graph=self.location_graph,
            start_time=self.T_0 if self.T_0 is not None else 0,
            params=params,
            solution_info=solution_info,
        )
        solve_registry.register(solve_result)
        return solve_result

    def _register_infeasible(self, params: SolveHCModelDTO, elapsed: float) -> None:
        solve_registry.register(SolveResult(
            status="infeasible",
            output=None,
            elapsed=elapsed,
            params={
                "W_c": getattr(params, "W_c", None),
                "W_pen": getattr(params, "W_pen", None),
                "W_e": getattr(params, "W_e", None),
                "W_t": getattr(params, "W_t", None),
                "C_v": getattr(params, "C_v", None),
                "T_travel": getattr(params, "T_travel", None),
                "T_setup": getattr(params, "T_setup", None),
                "T_pick": getattr(params, "T_pick", None),
                "M": getattr(params, "M", None),
                "V_p": dict(getattr(params, "V_p", {}) or {}),
                "T_cold": getattr(params, "T_cold", None),
                "N": len(self.N),
                "B": len(self.B),
                "V": len(self.location_graph.get_vertices()),
                "Max_it": getattr(params, "Max_it", None),
                "Max_imp": getattr(params, "Max_imp", None),
            },
        ))

    def _picker_speed(self, picker: str, params: SolveHCModelDTO) -> float:
        return (params.V_p or {}).get(picker, 1.0)

    def _picker_speeds(self, params: SolveHCModelDTO) -> Dict[str, float]:
        return {p: self._picker_speed(p, params) for p in self.P}

    def _fixed_time(self, batch: str, batch_assignments: Dict[str, Set[str]], params: SolveHCModelDTO) -> float:
        """Setup + picking time -- the part of T_exec_pb that does NOT depend
        on picker speed. Cached per batch (see solve()'s _fixed_time_cache):
        batch_assignments/C_n/T_setup/T_pick are all invariant for the
        duration of a run, so this is the same value every time for a given
        batch."""
        cached = self._fixed_time_cache.get(batch)
        if cached is not None:
            return cached
        orders = batch_assignments.get(batch, set())
        picking_capacity = sum(params.C_n.get(o, 0) for o in orders) if isinstance(params.C_n, dict) else 0
        fixed_time = params.T_setup + params.T_pick * picking_capacity
        self._fixed_time_cache[batch] = fixed_time
        return fixed_time

    def _route_time(self, route: List, params: SolveHCModelDTO, distance: Optional[float] = None) -> float:
        """
        Travel time (T_travel * distance) + service time -- opp_split's
        R_b, the part scaled by V_p. Pass `distance` when the caller
        already computed it (e.g. a 2-opt candidate's distance) to avoid
        recomputing it a second time via _calculate_route_distance
        (2026-09-10 audit finding: this and _T_exec_pb used to each
        recompute the route's distance independently, doubling the work
        of every 2-opt candidate evaluation in _generate_route_neighbor).
        """
        if not route:
            return 0.0

        if distance is None:
            distance = self._calculate_route_distance(route)

        service_time = sum(params.S.get(loc, 0) for loc in route) if isinstance(params.S, dict) else 0

        return params.T_travel * distance + service_time

    def _T_exec_pb(
        self, batch: str, route: List, picker: str,
        batch_assignments: Dict[str, Set[str]], params: SolveHCModelDTO,
        distance: Optional[float] = None,
    ) -> float:
        """See _route_time's docstring for why `distance` can be passed in precomputed."""
        fixed_time = self._fixed_time(batch, batch_assignments, params)
        speed = self._picker_speed(picker, params)
        return fixed_time + self._route_time(route, params, distance=distance) / speed

    def _eligible_pickers_for_batch(
        self, batch: str, route: List, batch_assignments: Dict[str, Set[str]], params: SolveHCModelDTO,
    ) -> List[str]:
        """Pickers p for which T_exec_pb[p, batch] <= T_cold, given `route`."""
        # Route distance doesn't depend on picker -- compute it once
        # instead of once per picker (each _T_exec_pb call would otherwise
        # recompute it independently; see _route_time's docstring).
        distance = self._calculate_route_distance(route)
        return [
            p for p in self.P
            if self._T_exec_pb(batch, route, p, batch_assignments, params, distance=distance) <= params.T_cold + 1e-9
        ]

    def _generate_initial_feasible_solution(
        self,
        batch_assignments: Dict[str, Set[str]],
        validator: "ConstraintsValidator",
        params: SolveHCModelDTO,
    ) -> Optional[RouteSolution]:
        """
        Generate an initial solution respecting topology/capacity/one-
        picker-per-batch. Returns None only if some batch's required
        locations genuinely can't be routed at all (disconnected graph,
        etc.) -- NOT if a batch comes out cold-chain-ineligible under its
        (heuristic) route: that no longer aborts construction, since the
        exact impossibility pre-check in solve() already ruled out the
        only case where no route could ever fix it, and Hill Climbing gets
        a full search budget to try for every other batch (see header /
        constraints_validator.py's module docstring).
        """
        solution = RouteSolution(self.B, self.location_graph, batch_assignments, self.P)
        route_time: Dict[str, float] = {}

        for batch in self.B:
            if not batch_assignments[batch]:
                route_time[batch] = 0.0
                continue

            required_locations = self._find_required_locations(batch, batch_assignments[batch], params.A)

            if not required_locations:
                route_time[batch] = 0.0
                continue

            route = self._initial_route(required_locations)
            if route is None:
                print(f"WARNING: Could not generate feasible route for batch {batch}")
                return None

            solution.set_batch_route(batch, route)
            route_time[batch] = self._route_time(route, params)

        self._assign_batches_to_pickers(solution, batch_assignments, route_time, params)

        if not validator.validate_solution(solution):
            return None

        return solution

    # Randomized pick-to-pick constructions tried per batch on top of the
    # deterministic nearest-neighbor one (see _initial_route), and the
    # distance exponent of their roulette -- the same beta = 2.5 opp_aco
    # uses by default (SolveAcoModelDTO's _Beta).
    _MULTI_START_CONSTRUCTIONS = 20
    _MULTI_START_BETA = 2.5

    def _initial_route(self, required_locations: Set) -> Optional[List]:
        """
        Initial route for one batch: the shortest of the deterministic
        nearest-neighbor construction (_generate_feasible_route), the
        farthest-insertion order realized forwards and backwards
        (route_construction.insertion_route; Rosenkrantz, Stearns & Lewis
        1977) and _MULTI_START_CONSTRUCTIONS randomized pick-to-pick
        constructions alternating forwards/backwards
        (route_construction.stitch_route_either_way with weight
        (1/d)^beta, each tightened by improve_route), then polished with the elite-route
        local search (route_construction.polish_route: pick-level 2-opt,
        or-opt relocation, vertex 2-opt, segment re-routing). The
        exhaustive best-first search (_generate_feasible_route_bff) only
        runs if every construction fails.

        Multi-start construction + local search is a standard way to
        diversify a Hill Climbing start (e.g. the multi-start local search
        Coruzzolo et al. 2023 use for batching, Logistics 7:61); the pick-
        to-pick construction itself is Chen et al. (2013)'s (see
        stitch_route). Our own choice to use them here, measured
        2026-09-26: with the nearest-neighbor start + vertex 2-opt alone,
        HC's routes summed 490 route-time units on realistic_crew_
        scenario(7) vs 425 for v5's exact Stage 1, and on
        realistic_crew_scenario(14) batch B1 got no route at all
        (nearest-neighbor stuck, best-first search out of budget), which
        made the whole solve "infeasible" although v5 solves it.
        """
        candidates = []
        greedy = self._generate_feasible_route(required_locations)
        if greedy is not None:
            candidates.append(greedy)
        # Farthest-insertion order, forwards and on the reversed graph (see
        # route_construction.insertion_route / reversed_graph).
        for graph, flip in ((self.location_graph, False), (self._reversed_graph, True)):
            full = route_construction.insertion_route(graph, required_locations)
            if full is not None:
                full = full[::-1] if flip else full
                candidates.append(full[1:-1])
        beta = self._MULTI_START_BETA
        for attempt in range(self._MULTI_START_CONSTRUCTIONS):
            # Alternate forwards / backwards construction (see
            # route_construction.stitch_route_either_way for why).
            full = route_construction.stitch_route_either_way(
                self.location_graph, self._reversed_graph, required_locations,
                lambda current, r, d: (1.0 / d) ** beta,
                self._undirected_adjacency, attempt % 2 == 1,
            )
            if full is not None:
                candidates.append(
                    route_construction.improve_route(self.location_graph, full[1:-1], required_locations)
                )
        if not candidates:
            fallback = self._generate_feasible_route_bff(required_locations)
            if fallback is None:
                return None
            candidates.append(fallback)

        best = min(candidates, key=self._calculate_route_distance)
        return route_construction.polish_route(self.location_graph, best, required_locations)

    def _assign_batches_to_pickers(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        route_time: Dict[str, float],
        params: SolveHCModelDTO,
    ) -> None:
        """
        Distribute batches with orders across pickers, greedily balancing
        load among each batch's COLD-CHAIN-ELIGIBLE pickers when it has
        any. A batch with NO eligible picker under its current route
        (possible now that construction no longer aborts on this -- see
        _generate_initial_feasible_solution) gets a best-effort pick: the
        picker that minimizes T_exec_pb, i.e. gets it closest to
        compliant, for Hill Climbing to try to finish the job on.
        """
        load = {p: 0 for p in self.P}
        batches_to_assign = [b for b in self.B if batch_assignments[b]]
        for batch in batches_to_assign:
            route = solution.get_batch_route(batch)
            eligible = self._eligible_pickers_for_batch(batch, route, batch_assignments, params)
            if eligible:
                picker = min(eligible, key=lambda p: (load[p], self.P.index(p)))
            else:
                distance = self._calculate_route_distance(route)
                picker = min(
                    self.P,
                    key=lambda p: self._T_exec_pb(batch, route, p, batch_assignments, params, distance=distance),
                )
            solution.assign_batch_to_picker(batch, picker)
            load[picker] += 1

    def _find_required_locations(
        self, batch: str, orders: Set[str], A: Dict
    ) -> Set:
        """Find all locations that MUST be visited for a batch's orders."""
        required = set()
        for order in orders:
            for vertex in self.location_graph.get_vertices():
                if vertex != self.location_graph.get_depot() and vertex != self.location_graph.get_final():
                    if A.get((order, vertex), 0) > 0:
                        required.add(vertex)
        return required

    def _dijkstra(self, source, forbidden: Set = frozenset()) -> Tuple[Dict, Dict]:
        """Shortest-path distances/predecessors from `source` (see models/utils/route_construction.py)."""
        return route_construction.dijkstra(self.location_graph, source, forbidden)

    def _reconstruct_path(self, prev: Dict, source, target) -> List:
        """Rebuild the path source -> target (inclusive) from a `prev` map."""
        return route_construction.reconstruct_path(prev, source, target)

    def _generate_feasible_route(self, required_locations: Set) -> Optional[List]:
        """
        Dijkstra-based nearest-neighbor route construction (see opp_hc_2's
        twin method) -- the nearest-neighbor TSP heuristic over shortest-
        path distances that Coruzzolo et al. (2023), Logistics 7:61, p.9,
        use for routing, here with no-revisit paths (v5's constraint).
        """
        if not required_locations:
            return []

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        route: List = []
        visited: Set = {depot}
        remaining = set(required_locations)
        current = depot

        while remaining:
            dist, prev = self._dijkstra(current, forbidden=(visited | {final}) - {current})
            reachable = [loc for loc in remaining if loc in dist]
            if not reachable:
                return None

            nearest = min(reachable, key=lambda loc: dist[loc])
            path = self._reconstruct_path(prev, current, nearest)[1:]

            if any(node in visited for node in path):
                return None

            visited.update(path)
            remaining.difference_update(path)
            route.extend(path)
            current = nearest

        dist, prev = self._dijkstra(current, forbidden=visited - {current})
        if final not in dist:
            return None

        path_to_final = self._reconstruct_path(prev, current, final)[1:-1]
        if any(node in visited for node in path_to_final):
            return None
        route.extend(path_to_final)

        return route

    def _build_reversal_prefix_arrays(self, route: List) -> Tuple[List[float], List[float], List[int]]:
        """See models/utils/route_construction.py's build_reversal_prefix_arrays."""
        return route_construction.build_reversal_prefix_arrays(self.location_graph, route)

    def _two_opt_tighten_route(self, route: List) -> List:
        """
        Distance-minimizing 2-opt over `route` (see models/utils/
        route_construction.py's two_opt_tighten_route). Used to tighten the
        nearest-neighbor/BFS construction's route BEFORE it's used for the
        cold-chain eligibility pre-check or as the Hill Climbing search's
        starting point (see _generate_initial_feasible_solution's call
        site for why this matters).
        """
        return route_construction.two_opt_tighten_route(self.location_graph, route)

    # 2026-09-26 audit finding: raising this cap alone (tried up to 10M) was
    # the wrong fix for v5's realistic_crew_scenario stress profile (26
    # orders/batch, ~19-26 required locations) reporting false "infeasible"
    # -- a batch that exhausted even a 10M-expansion cap after ~8 minutes
    # was actually found in well under a second once _bff_search was
    # reordered into a best-first search (by locations still required, then
    # graph distance to the nearest one -- see its docstring) instead of
    # plain FIFO BFS: the real problem was blind BFS wasting almost its
    # whole budget on partial paths still far from finished, not that
    # 200_000 was too small a number.
    #
    # That reordering resolves the vast majority of batches at this size
    # (~20-26 required locations on a ~50-256-node grid) in well under a
    # second. A minority still take 20-70s even with the better ordering
    # (measured on 14x14/16x16 grids specifically) -- kept at 2M rather
    # than 200_000 so those still resolve rather than false-negative,
    # accepting that cost for the ones that need it. Still a hard safety
    # valve, not a knob this class of scenario should need to push further;
    # if a batch still exhausts THIS cap, that is a genuine, larger
    # instance than anything measured so far, worth a fresh look rather
    # than raising the constant again.
    _MAX_BFF_EXPANSIONS = 2_000_000

    def _generate_feasible_route_bff(self, required_locations: Set) -> Optional[List]:
        """
        Last-resort exhaustive route search: best-first search ordered by
        (locations still required, distance to the nearest one) -- see
        models/utils/route_construction.py's _best_first_search.
        """
        return route_construction.best_first_route(
            self.location_graph, required_locations, self._MAX_BFF_EXPANSIONS
        )

    def _search_cost(
        self, solution: RouteSolution, evaluator: "RouteEvaluator", validator: "ConstraintsValidator"
    ) -> Tuple[float, float, float]:
        """
        Objective + a large penalty for any cold-chain overrun -- drives
        ALL accept/reject decisions during the search (initial cost,
        neighbor acceptance). Returns (cost, objective, violation)
        separately (not just cost) so solve() can reuse objective/
        violation after accepting `solution` instead of recomputing them a
        second time -- neither is the reported obj_val: see solve()'s
        best_feasible_solution/best_feasible_cost, tracked separately with
        the real (unpenalized) objective, only from fully compliant states.

        Uses evaluate_incremental()/cold_chain_violation_incremental()
        (diffed against each object's last COMMITTED solution) rather than
        evaluate()/cold_chain_violation() -- solve() is responsible for
        calling evaluator.commit(solution)/validator.commit(solution)
        whenever it actually accepts `solution` as the new current_solution
        (see their docstrings for why a rejected candidate must not
        trigger a commit).
        """
        objective = evaluator.evaluate_incremental(solution)
        violation = validator.cold_chain_violation_incremental(solution)
        cost = objective + self._COLD_CHAIN_PENALTY_WEIGHT * violation
        return cost, objective, violation

    def _route_local_search_cost(
        self, batch: str, route: List, picker: str,
        batch_assignments: Dict[str, Set[str]], params: SolveHCModelDTO,
    ) -> float:
        """
        Cheap per-route proxy used ONLY to pick the best 2-opt candidate
        inside _generate_route_neighbor (distance + cold-chain-overrun
        penalty for THIS batch alone) -- avoids recomputing the whole
        solution's objective (earliness/tardiness across every order) for
        every one of the O(n^2) candidates a 2-opt sweep considers. The
        OUTER accept/reject decision in solve() still uses the real,
        whole-solution _search_cost to decide whether to keep the result.
        """
        distance = self._calculate_route_distance(route)
        t_exec = self._T_exec_pb(batch, route, picker, batch_assignments, params, distance=distance)
        violation = max(0.0, t_exec - params.T_cold)
        return params.T_travel * distance + self._COLD_CHAIN_PENALTY_WEIGHT * violation

    def _generate_feasible_neighbor(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        params: SolveHCModelDTO,
    ) -> Optional[RouteSolution]:
        """
        Generate a neighbor via one of three moves:
        - 2-opt on a batch's route (topology-feasible only -- cold chain
          is judged by the OUTER accept/reject step in solve(), via
          _search_cost, not filtered out here)
        - Reassign a batch to a different picker (any picker -- same
          reasoning: the outer step judges whether it actually helps)
        - Swap the processing order of two batches on the same picker
        """
        batches_with_orders = self._batches_with_orders_cache

        moves = [self._generate_route_neighbor]
        if len(self.P) > 1 and batches_with_orders:
            moves.append(self._generate_picker_reassignment_neighbor)
        if any(len(solution.get_picker_sequence(p)) > 1 for p in self.P):
            moves.append(self._generate_sequence_swap_neighbor)

        move = random.choice(moves)
        return move(solution, batch_assignments, params)

    def _generate_route_neighbor(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        params: SolveHCModelDTO,
    ) -> Optional[RouteSolution]:
        """
        Full 2-opt on a randomly selected batch's route: every
        topologically feasible reversal is scored by the same distance +
        cold-chain-overrun penalty _route_local_search_cost computes
        (this batch's own cost alone), and the single best (steepest-
        descent) improving one is kept -- deliberately NOT required to
        already be fully cold-chain-compliant (see
        _generate_feasible_neighbor's docstring): a move that reduces the
        overrun without eliminating it is still progress, and the outer
        solve() loop decides whether the resulting whole solution is
        actually better.

        Each candidate's cost is derived from a distance DELTA (see
        _two_opt_tighten_route's docstring for why get_distance/has_edge
        are NOT assumed symmetric here) instead of building a new route
        list, re-validating it end-to-end, and re-summing its distance/
        T_exec_pb from scratch for every one of the O(n^2) reversals a
        sweep considers. This is valid because:
        - a reversal never changes `route`'s node set, so a duplicate-
          nodes/required-locations check would trivially pass for any
          candidate (already true of `route` itself) and doesn't need
          doing per candidate -- only topology (edge existence) actually
          varies between candidates;
        - fixed_time and service_time depend on which orders/locations
          are in the batch, not on the route's ORDER, so T_exec_pb is an
          affine function of distance alone for a fixed batch/picker
          (t_exec = intercept + (T_travel / speed) * distance) and can be
          evaluated from a candidate's distance without recomputing
          _T_exec_pb/_route_time per candidate.
        """
        batches_with_routes = [b for b in self.B if solution.get_batch_route(b)]
        if not batches_with_routes:
            return None

        batch = random.choice(batches_with_routes)
        route = solution.get_batch_route(batch)
        picker = solution.get_batch_picker(batch)

        if len(route) <= 1:
            return None

        n = len(route)
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        get_distance = self.location_graph.get_distance
        has_edge = self.location_graph.has_edge

        base_distance = self._calculate_route_distance(route)

        speed = self._picker_speed(picker, params)
        fixed_time = self._fixed_time(batch, batch_assignments, params)
        service_time = sum(params.S.get(loc, 0) for loc in route) if isinstance(params.S, dict) else 0
        t_exec_intercept = fixed_time + service_time / speed
        b_time_over_speed = params.T_travel / speed

        def local_cost(distance: float) -> float:
            t_exec = t_exec_intercept + b_time_over_speed * distance
            violation = max(0.0, t_exec - params.T_cold)
            return params.T_travel * distance + self._COLD_CHAIN_PENALTY_WEIGHT * violation

        # See _build_reversal_prefix_arrays' docstring for what these mean;
        # same construction as _two_opt_tighten_route, just a single pass
        # here (this method returns the single best 2-opt move, not a
        # fully-tightened route).
        fwd_prefix, rev_prefix, rev_broken_count = self._build_reversal_prefix_arrays(route)

        best_i = best_j = None
        best_local_cost = local_cost(base_distance)

        for i in range(n - 1):
            prev_node = route[i - 1] if i > 0 else depot
            removed_head = get_distance(prev_node, route[i])

            for j in range(i + 1, n):
                if rev_broken_count[j] - rev_broken_count[i] != 0:
                    continue  # a reverse-direction edge inside [i, j] is missing

                next_node = route[j + 1] if j + 1 < n else final

                if not has_edge(prev_node, route[j]) or not has_edge(route[i], next_node):
                    continue

                removed = removed_head + (fwd_prefix[j] - fwd_prefix[i]) + get_distance(route[j], next_node)
                added = get_distance(prev_node, route[j]) + (rev_prefix[j] - rev_prefix[i]) + get_distance(route[i], next_node)
                candidate_distance = base_distance + (added - removed)

                candidate_cost = local_cost(candidate_distance)
                if candidate_cost < best_local_cost - 1e-9:
                    best_local_cost = candidate_cost
                    best_i, best_j = i, j

        if best_i is None:
            return None

        best_route = route[:best_i] + route[best_i:best_j + 1][::-1] + route[best_j + 1:]

        neighbor = solution.copy()
        neighbor.set_batch_route(batch, best_route)
        return neighbor

    def _calculate_route_distance(self, route: List) -> float:
        """Total travel distance of depot -> route... -> final."""
        if not route:
            return 0.0

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        total = self.location_graph.get_distance(depot, route[0])
        for i in range(len(route) - 1):
            total += self.location_graph.get_distance(route[i], route[i + 1])
        total += self.location_graph.get_distance(route[-1], final)
        return total

    def _generate_picker_reassignment_neighbor(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        params: SolveHCModelDTO,
    ) -> Optional[RouteSolution]:
        """
        Move a random batch to a different picker (any picker, route
        untouched) -- NOT restricted to cold-chain-eligible ones anymore
        (see _generate_feasible_neighbor's docstring): the outer solve()
        loop's _search_cost penalizes a resulting overrun and rejects the
        move if it doesn't help, so this can freely explore reassigning a
        currently-ineligible batch towards a picker that gets it closer to
        (or all the way to) compliance.
        """
        batches_with_orders = self._batches_with_orders_cache
        if not batches_with_orders:
            return None

        batch = random.choice(batches_with_orders)
        current_picker = solution.get_batch_picker(batch)
        other_pickers = [p for p in self.P if p != current_picker]
        if not other_pickers:
            return None

        neighbor = solution.copy()
        new_picker = random.choice(other_pickers)
        neighbor.assign_batch_to_picker(batch, new_picker)
        return neighbor

    def _generate_sequence_swap_neighbor(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        params: SolveHCModelDTO,
    ) -> Optional[RouteSolution]:
        """Swap the processing order of two batches assigned to the same picker.
        Doesn't touch routes or assignments, so cold-chain eligibility is unaffected."""
        candidate_pickers = [p for p in self.P if len(solution.get_picker_sequence(p)) > 1]
        if not candidate_pickers:
            return None

        neighbor = solution.copy()
        picker = random.choice(candidate_pickers)
        sequence = neighbor.get_picker_sequence(picker)

        i, j = random.sample(range(len(sequence)), 2)
        sequence[i], sequence[j] = sequence[j], sequence[i]
        neighbor.set_picker_sequence(picker, sequence)
        return neighbor

    def _build_solution_output(self, solution: RouteSolution) -> OPPLocationGraph:
        """Convert RouteSolution to OPPLocationGraph format compatible with build_output."""
        output_graph = OPPLocationGraph(
            depot_node=self.location_graph.get_depot(),
            final_node=self.location_graph.get_final()
        )

        for vertex in self.location_graph.get_vertices():
            output_graph.add_vertex(vertex, "picking")

        for batch in self.B:
            route = solution.get_batch_route(batch)
            if not route:
                continue

            depot = self.location_graph.get_depot()
            final = self.location_graph.get_final()

            if self.location_graph.has_edge(depot, route[0]):
                output_graph.add_edge(
                    depot, route[0],
                    self.location_graph.get_distance(depot, route[0])
                )

            for i in range(len(route) - 1):
                if self.location_graph.has_edge(route[i], route[i+1]):
                    output_graph.add_edge(
                        route[i], route[i+1],
                        self.location_graph.get_distance(route[i], route[i+1])
                    )

            if self.location_graph.has_edge(route[-1], final):
                output_graph.add_edge(
                    route[-1], final,
                    self.location_graph.get_distance(route[-1], final)
                )

        return output_graph

    def _build_solution_info(self, solution: RouteSolution, objective_value: float, params: SolveHCModelDTO) -> dict:
        """Build solution information dictionary for OutputHandler (compatible with opp_hc_2's format)."""
        solution_info = {
            "status": "optimal",
            "objective_value": objective_value,
            "batch_times": {},
            "batch_completions": {},
            "picker_assignments": {},
            "tardiness": {},
            "earliness": {},
            "routes": {},
            "V_p": dict(params.V_p),
            "T_cold": params.T_cold,
        }

        base_time = self.T_0 if self.T_0 is not None else 0

        for picker in self.P:
            current_time = base_time
            for batch in solution.get_picker_sequence(picker):
                route = solution.get_batch_route(batch)

                T_exec_pb = self._calculate_batch_execution_time(batch, route, picker, params)
                current_time += T_exec_pb

                solution_info["batch_times"][batch] = T_exec_pb
                solution_info["batch_completions"][batch] = current_time
                solution_info["picker_assignments"][batch] = picker
                solution_info["routes"][batch] = route

        batch_assignments = params.extract_batch_assignments()
        for order in self.N:
            order_batch = None
            for batch, orders in batch_assignments.items():
                if order in orders:
                    order_batch = batch
                    break

            if order_batch is not None and order_batch in solution_info["batch_completions"]:
                completion_time = solution_info["batch_completions"][order_batch]
                due_date = params.T_due_n.get(order, float('inf'))

                if completion_time > due_date:
                    solution_info["tardiness"][order] = completion_time - due_date
                    solution_info["earliness"][order] = 0
                else:
                    solution_info["tardiness"][order] = 0
                    solution_info["earliness"][order] = due_date - completion_time

        return solution_info

    def _calculate_batch_execution_time(
        self, batch: str, route: List, picker: str, params: SolveHCModelDTO
    ) -> float:
        """
        T_exec_pb = T_setup + T_pick * sum(C_n)          [fixed, no speed]
                  + (T_travel * travel_distance + service_time) / V_p[picker]
        (same formula as RouteEvaluator._calculate_batch_execution_time --
        kept here too since this copy also drives the reported
        batch_times/batch_completions/tardiness/earliness, same split
        opp_hc_2/opp_hc_3 use between the search's evaluator and this
        reporting-only helper).
        """
        return self._T_exec_pb(batch, route, picker, params.extract_batch_assignments(), params)
