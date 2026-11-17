"""
Hill Climbing heuristic for the OPP (OPP-HC).

Decides the route of each batch, the picker that runs it and the order of the
batches on each picker. As in the exact models, a batch run by picker p takes
T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p] (setup and picking
do not depend on the speed; travel and service do), and a (picker, batch)
pair is eligible only if T_exec_pb[p, b] <= T_cold. Pickers do not interfere
with each other.

Cold chain. It is a hard constraint on the reported answer and a soft one (a
large cost penalty) during the search, so an initial solution with an
ineligible batch is not discarded before the search can repair it. The only
up-front "infeasible" is exact: a batch no picker could run within T_cold
even with a route time of 0. Otherwise "infeasible" means the search used its
whole budget without reaching a compliant solution.

Search. Stochastic first-improvement hill climbing (Hoos & Stuetzle 2004,
"Stochastic Local Search: Foundations and Applications"; Talbi 2009,
"Metaheuristics: From Design to Implementation", ch. 2): each iteration draws
one random move and one random neighbor and accepts it iff it lowers the
cost. The route move is the exception: it takes the best 2-opt reversal of
the chosen batch's route (Croes 1958). The other two moves -- reassign a
batch to another picker, swap two batches in a picker's sequence -- play the
role of the swap/insert moves of Coruzzolo et al. (2023), Logistics 7:61,
whose nearest-neighbor routing step (p.9) is also the base of the initial
routes (see _initial_route for the rest of its sources).
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
from models.utils.cold_chain_validation import batches_without_eligible_picker, invalid_speeds
from models.utils.input_validation import orders_without_exactly_one_batch
from models.utils.sla import sla_on_time_pct


class OPPHillClimbing(Model):
    """Hill Climbing solver for the OPP with picker speeds and a cold-chain limit."""

    # Multiplier of a cold-chain overrun (in time units) when it is added to a
    # search cost. Large enough to dominate the objective's marginal cost per
    # unit of time (W_c); it is a plain cost comparison, not a big-M.
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
        # Per-solve caches: which orders are in which batch never changes
        # during a run, so they are filled once in solve().
        self._fixed_time_cache: Dict[str, float] = {}
        self._batches_with_orders_cache: List[str] = []

    def solve(self, params: SolveHCModelDTO):
        """
        Solve the OPP using Hill Climbing on routes with full constraint
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

        # Batch composition is fixed for the whole run: compute these once.
        self._fixed_time_cache = {}
        self._batches_with_orders_cache = [b for b in self.B if batch_assignments[b]]

        # V_p[p] is a divisor in _T_exec_pb: a speed of 0 would divide by zero
        # and a negative one would give a negative T_exec_pb that looks
        # eligible for any T_cold. Reject it up front.
        bad_speeds = invalid_speeds(self._picker_speeds(params))
        if bad_speeds:
            print(f"ERROR: V_p must be strictly positive for every picker; got non-positive speed for {sorted(bad_speeds)}")
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        # Exact impossibility pre-check: fixed_time(b) alone (setup + picking)
        # gives the best possible T_exec_pb for any picker, since route_time >= 0,
        # so feeding batches_without_eligible_picker a route_time of exactly 0.0
        # asks "is there a picker fast enough even for a zero-distance route?".
        # A batch flagged here is impossible under ANY route or picker.
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

        # current_cost (objective + cold-chain penalty) drives accept/reject.
        # What is reported is best_feasible_*: the real objective of the best
        # fully compliant solution seen.
        current_cost, current_objective, current_violation = self._search_cost(current_solution, evaluator, validator)
        evaluator.commit(current_solution)
        validator.commit(current_solution)

        best_feasible_solution = None
        best_feasible_cost = float("inf")
        # Iteration at which best_feasible_solution last improved (0 = the
        # initial construction).
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

            # First-improvement acceptance of one random neighbor.
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
            # The whole budget went by without a cold-chain-compliant solution.
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
        """Setup + picking time of a batch: the part of T_exec_pb that does not
        depend on the picker. Cached, since it never changes during a run."""
        cached = self._fixed_time_cache.get(batch)
        if cached is not None:
            return cached
        orders = batch_assignments.get(batch, set())
        picking_capacity = sum(params.C_n.get(o, 0) for o in orders) if isinstance(params.C_n, dict) else 0
        fixed_time = params.T_setup + params.T_pick * picking_capacity
        self._fixed_time_cache[batch] = fixed_time
        return fixed_time

    def _route_time(self, route: List, params: SolveHCModelDTO, distance: Optional[float] = None) -> float:
        """Travel + service time of a route: the part of T_exec_pb the picker's
        speed divides. `distance` may be passed when the caller already has it."""
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
        """T_exec_pb[picker, batch] for `route` (`distance` as in _route_time)."""
        fixed_time = self._fixed_time(batch, batch_assignments, params)
        speed = self._picker_speed(picker, params)
        return fixed_time + self._route_time(route, params, distance=distance) / speed

    def _eligible_pickers_for_batch(
        self, batch: str, route: List, batch_assignments: Dict[str, Set[str]], params: SolveHCModelDTO,
    ) -> List[str]:
        """Pickers p for which T_exec_pb[p, batch] <= T_cold, given `route`."""
        # The distance does not depend on the picker: compute it once.
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
        Initial solution that respects topology, capacity and one picker per
        batch. Returns None only if some batch cannot be routed at all (e.g.
        a disconnected graph); a batch that comes out cold-chain-ineligible
        is kept for the search to repair.
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
        Initial route of a batch: the shortest of
        - the nearest-neighbor construction (_generate_feasible_route),
        - the farthest-insertion order, forwards and backwards
          (route_construction.insertion_route; Rosenkrantz, Stearns & Lewis
          1977),
        - _MULTI_START_CONSTRUCTIONS randomized pick-to-pick constructions,
          alternating forwards and backwards (stitch_route_either_way, after
          Chen et al. 2013), each tightened by improve_route,
        then polished with route_construction.polish_route. The exhaustive
        best-first search (_generate_feasible_route_bff) runs only if every
        construction fails.

        The nearest-neighbor start with 2-opt alone gives routes clearly
        longer than OPP-Split's Stage 1 routes, and on hard batches it can
        find no route at all; hence the portfolio (multi-start local search,
        as Coruzzolo et al. 2023 use for batching).
        """
        candidates = []
        greedy = self._generate_feasible_route(required_locations)
        if greedy is not None:
            candidates.append(greedy)
        # Farthest-insertion order, forwards and on the reversed graph.
        for graph, flip in ((self.location_graph, False), (self._reversed_graph, True)):
            full = route_construction.insertion_route(graph, required_locations)
            if full is not None:
                full = full[::-1] if flip else full
                candidates.append(full[1:-1])
        beta = self._MULTI_START_BETA
        for attempt in range(self._MULTI_START_CONSTRUCTIONS):
            # Alternate forwards and backwards constructions.
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
        Distribute the batches across pickers, balancing the load among each
        batch's cold-chain-eligible pickers. A batch with no eligible picker
        under its current route goes to the picker that minimizes T_exec_pb,
        the closest to compliant, for the search to repair.
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
        Nearest-neighbor route over shortest-path distances (the routing step
        of Coruzzolo et al. 2023, Logistics 7:61, p.9), on paths that never
        revisit a location, as the exact models require.
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
        """Distance-minimizing 2-opt over `route` (route_construction.two_opt_tighten_route)."""
        return route_construction.two_opt_tighten_route(self.location_graph, route)

    # Cap on the node expansions of the best-first search. Most batches of
    # 20-26 required locations on grids of 50-256 nodes resolve well below it;
    # a batch that exhausts it is larger than the search was designed for.
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
        Objective plus a large penalty for any cold-chain overrun: what every
        accept/reject decision of the search compares. Returns (cost,
        objective, violation) so solve() can reuse the last two.

        Both are computed incrementally against the last committed solution,
        so solve() must commit() on the evaluator and the validator whenever
        it accepts `solution`.
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
        Cost of one batch's route (distance plus its own cold-chain overrun),
        used only to pick the best 2-opt candidate without re-evaluating the
        whole solution for each of the O(n^2) reversals. Whether the move is
        kept is decided in solve() with _search_cost.
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
        Generate a neighbor with one of three moves: 2-opt on a batch's
        route, reassigning a batch to another picker, or swapping two batches
        in a picker's sequence. Moves are only checked for topology; solve()
        judges the cold chain through _search_cost.
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
        Best 2-opt reversal of a randomly chosen batch's route, scored by
        _route_local_search_cost. A reversal that reduces the cold-chain
        overrun without removing it still counts as an improvement.

        Each candidate is scored from its distance delta instead of building
        and re-validating a new route: a reversal keeps the node set, so only
        the existence of the reversed edges has to be checked, and for a
        fixed batch and picker T_exec_pb is an affine function of the
        distance. Distances and edges are not assumed symmetric.
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

        # Prefix arrays of _build_reversal_prefix_arrays; a single pass, since
        # only the best move is returned.
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
        Move a random batch to another picker, keeping its route. Any picker
        is allowed: _search_cost penalizes an overrun, so the move can bring
        an ineligible batch closer to compliance.
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
        """Build the solution information dictionary for OutputHandler."""
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
        Same formula as RouteEvaluator's; this copy feeds the reported times.
        """
        return self._T_exec_pb(batch, route, picker, params.extract_batch_assignments(), params)
