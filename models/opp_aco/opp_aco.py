"""
Ant Colony Optimization heuristic for the OPP (OPP-ACO).

Each ant builds, batch by batch, a route (probabilistic pick-to-pick
construction after Chen et al. 2013, see _build_batch_route) and then chooses
the batch's picker; each picker's batches are sequenced by due date. As in
the exact models, a batch run by picker p takes T_exec_pb[p, b] =
fixed_time(b) + route_time(b) / V_p[p] (setup and picking do not depend on
the speed; travel and service do), and a (picker, batch) pair is eligible
only if T_exec_pb[p, b] <= T_cold. Pickers do not interfere with each other.

Cold chain. The ant builds a batch's route before choosing its picker, so the
picker roulette runs over the pickers that are eligible for that very route.
The limit is a hard constraint on the reported answer and a soft one (a large
objective penalty) during the search: one tight batch must not make the
validator reject the ant's whole solution and starve the pheromone of every
other batch (see utils/constraints_validator.py and _deposit_solution, which
deposits per batch). The only up-front "infeasible" verdicts are exact: a
batch no picker could run within T_cold even with a route time of 0, or a
required location that cannot be reached. Otherwise "infeasible" means the
search ended without a compliant ant.
"""

import time
import random
import heapq
from typing import Dict, List, Set, Optional, Tuple

from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from dtos.opp.solve_result import SolveResult
from dtos.opp.solution_record_dto import SolutionRecordDTO
from dtos.opp.model_dto import ModelDTO
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
import models.utils.solve_registry as solve_registry
import models.utils.route_construction as route_construction
from models.utils.route_solution import RouteSolution
from models.opp_aco.utils.route_evaluator import RouteEvaluator
from models.opp_aco.utils.constraints_validator import ConstraintsValidator
from models.opp_aco.utils import exec_time
from models.utils.cold_chain_validation import batches_without_eligible_picker, invalid_speeds
from models.utils.input_validation import orders_without_exactly_one_batch
from models.utils.sla import sla_on_time_pct


class OPPAntColonyOptimization(Model):
    """ACO solver for the OPP with picker speeds and a cold-chain limit."""

    # Construction attempts per batch and ant before falling back to
    # _fallback_route. An attempt is cheap and succeeds on most batches, so a
    # few retries keep the ants diverse; the cached fallback bounds the cost of
    # the hard batches.
    _MAX_ROUTE_ATTEMPTS_PER_BATCH = 10

    # Cap on the node expansions of the best-first fallback search (the value
    # opp_hc uses; see route_construction.best_first_route).
    _MAX_BFF_EXPANSIONS = 2_000_000

    # Local search (route_construction.improve_route) on every ant's route.
    _IMPROVE_ANT_ROUTES = True

    # The other local-search components. Each has its own switch so that
    # experiments/heuristics/aco/run_aco_ablation_study.py can measure it
    # separately; all are on by default:
    # - elite-route polishing of each batch's record route
    #   (route_construction.polish_route, in solve() and _fallback_route);
    _POLISH_ELITE_ROUTES = True
    # - swapping each batch's shortest-known route into the best solution
    #   (_recombine_shortest_routes);
    _RECOMBINE_SHORTEST_ROUTES = True
    # - schedule local search on the best solution (_schedule_local_search).
    _SCHEDULE_LOCAL_SEARCH = True

    # Route pheromone bounds, MAX-MIN Ant System style (Stuetzle & Hoos 2000; the
    # variant described in Alaya & Solnon, "Ant Colony Optimization for
    # Multi-objective Optimization Problems", pp.3-4): pheromone starts at tau_max,
    # only the best routes deposit (delta tau = 1) and tau stays within
    # [tau_min, tau_max]. Each batch reinforces at most 2 routes per iteration
    # (iteration-best and best-so-far, see _update_route_pheromones), so the steady
    # state of tau <- (1 - rho) tau + 2 is 2 / rho: tau_max = 2 / rho. tau_min =
    # tau_max / 50 keeps every pick pair choosable (the ratio is our choice;
    # Stuetzle & Hoos derive it from n and a target probability, of the same order
    # for n ~ 20-26 picks). Lesch et al. (2023), "Optimizing storage assignment,
    # order picking, and their interaction in mezzanine warehouses", Applied
    # Intelligence 53:18605-18629, use the same bounds for ACO picker routing (tau
    # in [1, 25], alpha = 1, beta = 2, rho = 0.02, p.18620), with the same 1/d
    # visibility core (their Eq. 6, p.18617).
    #
    # Route pheromone learns from the route length only, per batch (Chen et al.
    # (2013), Eqs. 3-5, deposit 1 / L_k with L_k the tour length); the full
    # objective drives the picker pheromone and the best-so-far solution.
    _MMAS_TAU_MIN_RATIO = 1.0 / 50.0

    # Share of params.Max_time the ants may use (once a compliant solution
    # exists); the rest is kept for the elite-route polishing and the schedule
    # local search. It only matters on instances that reach the budget.
    _ANT_BUDGET_SHARE = 0.5

    # Multiplier of a cold-chain overrun (in time units) when it is added to an
    # ant's cost. Large enough to dominate the objective's marginal cost per
    # unit of time (W_c); it is a plain cost comparison, not a big-M.
    _COLD_CHAIN_PENALTY_WEIGHT = 1000.0

    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time
        self.P = sorted(dto.P) if getattr(dto, "P", None) else ["P1"]
        self._fallback_cache: Dict[frozenset, Optional[List[str]]] = {}
        self._fallback_calls = 0
        self._required_by_batch: Dict[str, Set[str]] = {}
        # Undirected adjacency, for the completability check of
        # route_construction.stitch_route (keeps_route_completable).
        self._undirected_adjacency = route_construction.undirected_adjacency(self.location_graph)
        # The same warehouse with its edges reversed, to build routes backwards
        # (route_construction.stitch_route_either_way).
        self._reversed_graph = route_construction.reversed_graph(self.location_graph)

    def solve(self, params: SolveAcoModelDTO):
        """
        Solves the OPP using the Ant Colony Optimization (ACO) heuristic,
        with picker speed and cold chain eligibility.
        """
        if params.Seed is not None:
            random.seed(params.Seed)

        start_time = time.time()

        if params.B_nb is None:
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        if not (params.is_capacity_valid() and params.is_batch_assignment_valid()):
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        # is_batch_assignment_valid only rejects an order in TWO+ batches.
        unassigned_or_duplicated = orders_without_exactly_one_batch(params.B_nb, self.N)
        if unassigned_or_duplicated:
            print(
                "ERROR: every order must be in exactly one batch; not the case for "
                f"{sorted(unassigned_or_duplicated)}"
            )
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        batch_assignments = params.extract_batch_assignments()

        num_ants = getattr(params, "_A_ants", 15)
        max_it = getattr(params, "_Max_it", 60)
        max_time = getattr(params, "_Max_time", None) or float("inf")
        # Deadline of the whole solve, post-processing included. None = no budget.
        self._deadline = start_time + max_time if max_time != float("inf") else None
        alpha = getattr(params, "_Alpha", 1.0)
        beta = getattr(params, "_Beta", 2.5)
        evaporation_rate = getattr(params, "_E", 0.15)
        q_factor = getattr(params, "_Q", 100.0)

        # V_p[p] is a divisor in _T_exec_pb: a speed of 0 would divide by zero and a
        # negative one would give a negative T_exec_pb that looks eligible for any
        # T_cold. Reject it up front.
        bad_speeds = invalid_speeds(self._picker_speeds(params))
        if bad_speeds:
            print(f"ERROR: V_p must be strictly positive for every picker; got non-positive speed for {sorted(bad_speeds)}")
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        # Exact impossibility pre-check: fixed_time(b) alone (setup + picking) gives the
        # best possible T_exec_pb for any picker, since route_time >= 0, so feeding
        # batches_without_eligible_picker a route_time of exactly 0.0 asks "is there a
        # picker fast enough even for a zero-distance route?". A batch flagged here is
        # impossible under ANY route or picker.
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
            self._register_infeasible(params, time.time() - start_time)
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

        picker_pheromones = self._initialize_picker_pheromones()

        # The required locations of a batch are fixed for the whole solve:
        # compute them once instead of once per ant and batch.
        required_locations_by_batch = {
            batch: self._find_required_locations(batch, batch_assignments[batch], params.A)
            for batch in self.B
            if batch_assignments.get(batch)
        }
        self._required_by_batch = required_locations_by_batch
        self._tau_max = 2.0 / evaporation_rate
        self._tau_min = self._tau_max * self._MMAS_TAU_MIN_RATIO
        pheromones = self._initialize_pheromones(required_locations_by_batch)

        # Exact reachability pre-check: a required location that cannot be
        # reached from the depot, or cannot reach `final`, is on no route. Two
        # linear-time searches settle it, instead of letting every ant exhaust
        # its attempts on a batch that cannot be routed.
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        from_depot = self._reachable_from(self.location_graph, depot)
        to_final = self._reachable_from(self._reversed_graph, final)
        unreachable_batches = {
            batch
            for batch, required in required_locations_by_batch.items()
            for req in required
            if req not in from_depot or req not in to_final
        }
        if unreachable_batches:
            print(
                "ERROR: No route can visit every required location for "
                f"batches {sorted(unreachable_batches)} (some location is "
                "unreachable from the depot, or can't reach `final`)"
            )
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        best_global_solution = None
        best_global_cost = float("inf")
        iteration = 0
        # Iteration at which best_global_solution last improved.
        best_found_at_iteration = 0
        # Shortest route any ant has found for each batch (see
        # _recombine_shortest_routes).
        shortest_route_by_batch: Dict[str, Tuple[float, List[str]]] = {}

        timed_out = False
        while iteration < max_it and not timed_out:
            iteration += 1
            ant_solutions = []
            feasible_ant_solutions = []
            iteration_best_route_by_batch: Dict[str, Tuple[float, List[str]]] = {}

            for ant in range(num_ants):
                # Max_time is checked per ant, but only once a compliant
                # solution exists, so the budget never produces a false
                # "infeasible". Ants stop at _ANT_BUDGET_SHARE of the budget;
                # the polishing and the schedule search use the rest.
                if (
                    time.time() - start_time > max_time * self._ANT_BUDGET_SHARE
                    and (best_global_solution is not None or feasible_ant_solutions)
                ):
                    timed_out = True
                    break
                ant_solution = self._build_ant_solution(
                    batch_assignments, pheromones, picker_pheromones, params, alpha, beta,
                    required_locations_by_batch,
                )

                # Only the base hard constraints: the cold chain is the soft
                # penalty below (see utils/constraints_validator.py).
                if ant_solution is None or not validator.validate_solution(ant_solution):
                    continue

                for batch in required_locations_by_batch:
                    route = ant_solution.get_batch_route(batch)
                    length = self._calculate_route_distance(route)
                    if length < iteration_best_route_by_batch.get(batch, (float("inf"), None))[0]:
                        iteration_best_route_by_batch[batch] = (length, list(route))

                base_cost = evaluator.evaluate(ant_solution)
                violation = validator.cold_chain_violation(ant_solution)
                cost = base_cost + self._COLD_CHAIN_PENALTY_WEIGHT * violation
                # The batches whose pheromone this ant may reinforce (see
                # _deposit_solution).
                compliant_batches = validator.compliant_batches(ant_solution)
                ant_solutions.append((ant_solution, cost, compliant_batches))

                if violation == 0.0:
                    feasible_ant_solutions.append((ant_solution, base_cost))

            # A batch's iteration-best route that beats its record is polished
            # (route_construction.polish_route) before it becomes the batch's
            # best-so-far route. Only on a new record: a polish is costly on
            # large grids and records are rare.
            records = [
                (batch, route)
                for batch, (length, route) in iteration_best_route_by_batch.items()
                if length < shortest_route_by_batch.get(batch, (float("inf"), None))[0] - 1e-9
            ]
            for index, (batch, route) in enumerate(records):
                # Under a budget each record gets an equal share of the time
                # left, with one more share kept for the schedule local search.
                polish_deadline = None
                if self._deadline is not None:
                    left = max(self._deadline - time.time(), 0.0)
                    polish_deadline = time.time() + left / (len(records) - index + 1)
                if self._POLISH_ELITE_ROUTES:
                    polished = route_construction.polish_route(
                        self.location_graph, route, required_locations_by_batch[batch], deadline=polish_deadline,
                    )
                else:
                    polished = route
                polished_length = self._calculate_route_distance(polished)
                iteration_best_route_by_batch[batch] = (polished_length, polished)
                shortest_route_by_batch[batch] = (polished_length, polished)

            if not ant_solutions:
                continue

            # best_global_solution only ever comes from a cold-chain-compliant
            # ant, so the reported answer always respects T_cold.
            best_improved = False
            if feasible_ant_solutions:
                iter_best_feasible_solution, iter_best_feasible_cost = min(
                    feasible_ant_solutions, key=lambda x: x[1]
                )
                if iter_best_feasible_cost < best_global_cost:
                    best_global_solution = iter_best_feasible_solution.copy()
                    best_global_cost = iter_best_feasible_cost
                    best_found_at_iteration = iteration
                    best_improved = True

            if best_global_solution is not None and self._RECOMBINE_SHORTEST_ROUTES:
                recombined = self._recombine_shortest_routes(
                    best_global_solution, best_global_cost, shortest_route_by_batch, validator, evaluator,
                )
                if recombined is not None:
                    best_global_solution, best_global_cost = recombined
                    best_found_at_iteration = iteration
                    best_improved = True

            if best_improved and self._SCHEDULE_LOCAL_SEARCH:
                best_global_solution, best_global_cost = self._schedule_local_search(
                    best_global_solution, best_global_cost, validator, evaluator,
                )

            self._update_route_pheromones(
                pheromones,
                evaporation_rate,
                [(batch, route) for batch, (_, route) in iteration_best_route_by_batch.items()]
                + [(batch, route) for batch, (_, route) in shortest_route_by_batch.items()],
            )
            self._update_pheromones(
                picker_pheromones,
                ant_solutions,
                evaporation_rate,
                q_factor,
                best_global_solution=best_global_solution,
                best_global_cost=best_global_cost
            )

        elapsed = time.time() - start_time

        print(f"\nACO execution time: {elapsed:.4f}s")
        print(f"Final objective value: {best_global_cost:.4f}")
        print(f"Iterations completed: {iteration}")

        if best_global_solution is None:
            self._register_infeasible(params, elapsed)
            return "infeasible", None

        solution_info = self._build_solution_info(
            best_global_solution, best_global_cost, params
        )
        self.last_solution_info = solution_info
        super().notify(solution_info=solution_info)

        output = self._build_solution_output(best_global_solution)
        solve_result = SolveResult(
            status="optimal",
            output=output,
            elapsed=elapsed,
            params={
                "obj_val": best_global_cost,
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
                "A_ants": num_ants,
                "Max_it": max_it,
                "Alpha": alpha,
                "Beta": beta,
                "Max_route_attempts_per_batch": self._MAX_ROUTE_ATTEMPTS_PER_BATCH,
                "iterations_run": iteration,
                "Max_time": max_time,
                "timed_out": timed_out,
                "best_found_at_iteration": best_found_at_iteration,
            },
        )
        solve_result.solution_record = SolutionRecordDTO(
            model_name="opp_aco",
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

    def _register_infeasible(self, params: SolveAcoModelDTO, elapsed: float) -> None:
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
                "P": len(self.P),
                "V": len(self.location_graph.get_vertices()),
                "A_ants": getattr(params, "_A_ants", 15),
                "Max_it": getattr(params, "_Max_it", 60),
                "Alpha": getattr(params, "_Alpha", 1.0),
                "Beta": getattr(params, "_Beta", 2.5),
                "Max_route_attempts_per_batch": self._MAX_ROUTE_ATTEMPTS_PER_BATCH,
            },
        ))

    def _picker_speed(self, picker: str, params: SolveAcoModelDTO) -> float:
        return (params.V_p or {}).get(picker, 1.0)

    def _picker_speeds(self, params: SolveAcoModelDTO) -> Dict[str, float]:
        return {p: self._picker_speed(p, params) for p in self.P}

    def _fixed_time(self, batch: str, batch_assignments: Dict[str, Set[str]], params: SolveAcoModelDTO) -> float:
        """Setup + picking time of a batch: the part of T_exec_pb that does not depend on the picker."""
        orders = batch_assignments.get(batch, set())
        return exec_time.fixed_time(orders, params.C_n, params.T_setup, params.T_pick)

    def _route_time(
        self, route: List[str], params: SolveAcoModelDTO, distance: Optional[float] = None
    ) -> float:
        """Travel + service time of a route: the part of T_exec_pb the picker's
        speed divides. `distance` may be passed when the caller already has it."""
        return exec_time.route_time(self.location_graph, route, params.T_travel, params.S, distance)

    def _T_exec_pb(
        self, batch: str, route: List[str], picker: str,
        batch_assignments: Dict[str, Set[str]], params: SolveAcoModelDTO,
        distance: Optional[float] = None,
    ) -> float:
        """T_exec_pb[picker, batch] for `route` (`distance` as in _route_time)."""
        orders = batch_assignments.get(batch, set())
        return exec_time.T_exec_pb(
            self.location_graph, route, orders, picker,
            params.C_n, params.T_setup, params.T_pick, params.T_travel, params.S, params.V_p,
            distance=distance,
        )

    def _eligible_pickers_for_batch(
        self, batch: str, route: List[str], batch_assignments: Dict[str, Set[str]], params: SolveAcoModelDTO,
    ) -> List[str]:
        """Pickers p for which T_exec_pb[p, batch] <= T_cold, given `route`."""
        # The distance does not depend on the picker: compute it once.
        distance = self._calculate_route_distance(route)
        return [
            p for p in self.P
            if self._T_exec_pb(batch, route, p, batch_assignments, params, distance=distance) <= params.T_cold + 1e-9
        ]


    @staticmethod
    def _reachable_from(location_graph, source: str) -> Set[str]:
        """
        Every vertex reachable from `source` (BFS, O(V + E)). An all-pairs
        shortest-path computation is out of reach on the 100x100 stress grid
        (V = 10,000).
        """
        seen = {source}
        frontier = [source]
        while frontier:
            next_frontier = []
            for u in frontier:
                for v in location_graph.get_neighbors(u):
                    if v not in seen:
                        seen.add(v)
                        next_frontier.append(v)
            frontier = next_frontier
        return seen

    def _initialize_pheromones(self, required_locations_by_batch: Dict[str, Set[str]]) -> Dict[Tuple[str, str], float]:
        """
        Pheromone on (pick, pick) pairs, after Chen et al. (2013), p.81: per
        batch, every ordered pair among {depot} + its required locations +
        {final} (the depot only as origin, the final node only as
        destination). Pairs are shared across batches: two batches that need
        the same two locations learn from each other.
        """
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        pheromones = {}
        for required in required_locations_by_batch.values():
            origins = [depot] + list(required)
            destinations = list(required) + [final]
            for i in origins:
                for j in destinations:
                    if i != j:
                        pheromones[(i, j)] = self._tau_max
        return pheromones

    def _initialize_picker_pheromones(self) -> Dict[Tuple[str, str], float]:
        """(batch, picker) assignment pheromone, starting at 1.0."""
        return {(b, p): 1.0 for b in self.B for p in self.P}

    def _build_ant_solution(
        self,
        batch_assignments: Dict[str, Set[str]],
        pheromones: Dict[Tuple[str, str], float],
        picker_pheromones: Dict[Tuple[str, str], float],
        params: SolveAcoModelDTO,
        alpha: float,
        beta: float,
        required_locations_by_batch: Dict[str, Set[str]],
    ) -> Optional[RouteSolution]:
        """
        One ant: a route per batch and, for every batch with orders, a picker
        chosen among those eligible for that route. Returns a RouteSolution,
        or None if the ant could not build some route.
        """
        solution = RouteSolution(self.B, self.location_graph, batch_assignments, self.P)
        picker_load = {p: 0 for p in self.P}

        for batch in self.B:
            if not batch_assignments.get(batch):
                continue

            required_locations = required_locations_by_batch[batch]

            if required_locations:
                route = None
                # Alternate the construction direction between attempts,
                # starting from a random side.
                first_backwards = random.random() < 0.5
                for attempt in range(self._MAX_ROUTE_ATTEMPTS_PER_BATCH):
                    backwards = first_backwards != (attempt % 2 == 1)
                    candidate = self._build_batch_route(required_locations, pheromones, alpha, beta, backwards)
                    if candidate is not None and len(candidate) == len(set(candidate)):
                        route = candidate
                        break
                if route is None:
                    route = self._fallback_route(required_locations)
                if route is None:
                    return None
                solution.set_batch_route(batch, route[1:-1])

            picker = self._select_picker(
                batch, picker_pheromones, picker_load, alpha, beta,
                solution.get_batch_route(batch), batch_assignments[batch], params,
            )
            solution.assign_batch_to_picker(batch, picker)
            picker_load[picker] += 1

        self._sort_picker_queues_by_due_date(solution, batch_assignments, params.T_due_n)

        return solution

    def _sort_picker_queues_by_due_date(
        self,
        solution: "RouteSolution",
        batch_assignments: Dict[str, Set[str]],
        due_dates: Dict[str, float],
    ) -> None:
        """Order every picker's queue by the earliest due date among each batch's orders."""
        due_dates = due_dates if isinstance(due_dates, dict) else {}

        def due_date_key(batch: str):
            orders = batch_assignments.get(batch, set())
            earliest = min((due_dates.get(o, float("inf")) for o in orders), default=float("inf"))
            return (earliest, batch)

        for picker in self.P:
            sequence = solution.get_picker_sequence(picker)
            if len(sequence) > 1:
                solution.set_picker_sequence(picker, sorted(sequence, key=due_date_key))

    def _select_picker(
        self,
        batch: str,
        picker_pheromones: Dict[Tuple[str, str], float],
        picker_load: Dict[str, int],
        alpha: float,
        beta: float,
        route: List[str],
        orders: Set[str],
        params: SolveAcoModelDTO,
    ) -> str:
        """
        Roulette-wheel choice of a batch's picker: the (batch, picker)
        pheromone times a load-balancing visibility, over the pickers that
        are cold-chain-eligible for the route this ant just built. If none
        is, the roulette runs over every picker, so the ant still yields a
        complete solution (penalized for the overrun).
        """
        eligible = self._eligible_pickers_for_batch(batch, route, {batch: orders}, params)
        candidates = eligible if eligible else self.P

        weights = []
        total_weight = 0.0
        for picker in candidates:
            tau = picker_pheromones.get((batch, picker), 1.0) ** alpha
            eta = (1.0 / (1.0 + picker_load[picker])) ** beta
            weight = tau * eta
            weights.append((picker, weight))
            total_weight += weight

        if total_weight <= 0:
            return random.choice(candidates)

        rand_val = random.uniform(0, total_weight)
        cumulative = 0.0
        for picker, weight in weights:
            cumulative += weight
            if rand_val <= cumulative:
                return picker
        return weights[-1][0]

    def _build_batch_route(
        self,
        required_locations: Set[str],
        pheromones: Dict[Tuple[str, str], float],
        alpha: float,
        beta: float,
        backwards: bool = False,
    ) -> Optional[List[str]]:
        """
        Probabilistic route for a batch (depot ... final, a simple path)
        through every required location.

        Pick-to-pick construction after Chen et al. (2013), "An ant colony
        optimization routing algorithm for two order pickers with congestion
        consideration", Computers & Industrial Engineering 66:77-85: the ant
        travels from one pick to another, choosing the next required location
        r with the Ant System random-proportional rule (their Eq. 2, p.81),

            p(r) = tau[last, r]^alpha * eta[r]^beta / sum(...),
            eta[r] = 1 / dist(current, r)

        and walks the shortest path to it. Coruzzolo et al. (2023), Logistics
        7:61 (pp.6-9), route over precomputed shortest paths in the same way.
        Choosing among picks instead of single edges matters: with 23-26
        required locations on a grid, a random self-avoiding walk boxes
        itself in long before finishing.

        Unlike Chen et al., who read pick-to-pick distances from a static
        table and may re-walk an aisle, the exact models forbid revisiting a
        vertex. So the distance in eta and the path walked are recomputed at
        every step with Dijkstra, avoiding the vertices already on the route
        (and `final`, which may only close it).

        Returns None when the construction corners itself (no candidate pick
        passes route_construction.keeps_route_completable, or `final` cannot
        be reached without a revisit). _build_ant_solution retries and, after
        _MAX_ROUTE_ATTEMPTS_PER_BATCH failures, uses _fallback_route.

        With _IMPROVE_ANT_ROUTES the route is then tightened by
        route_construction.improve_route (2-opt alternated with segment
        re-routing). Hybridizing ant tours with local search is standard ACO
        practice (Dorigo & Stuetzle 2004, "Ant Colony Optimization", ch.
        3.7); without it the routes are clearly longer than OPP-Split's Stage
        1 routes.
        """
        # The pheromone is indexed by (previous pick, next pick) in the route's
        # depot -> final direction, so when building backwards the step
        # current -> r is the route's pair (r, current).
        if backwards:
            def weight(current, r, d):
                return (pheromones.get((r, current), self._tau_min) ** alpha) * ((1.0 / d) ** beta)
        else:
            def weight(current, r, d):
                return (pheromones.get((current, r), self._tau_min) ** alpha) * ((1.0 / d) ** beta)
        route = route_construction.stitch_route_either_way(
            self.location_graph, self._reversed_graph, required_locations, weight,
            self._undirected_adjacency, backwards,
        )
        if route is None:
            return None

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        if self._IMPROVE_ANT_ROUTES:
            stops = route_construction.improve_route(self.location_graph, route[1:-1], required_locations)
            route = [depot] + stops + [final]
        return route

    def _recombine_shortest_routes(
        self,
        best_solution: RouteSolution,
        best_cost: float,
        shortest_route_by_batch: Dict[str, Tuple[float, List[str]]],
        validator: ConstraintsValidator,
        evaluator: RouteEvaluator,
    ) -> Optional[Tuple[RouteSolution, float]]:
        """
        Try the best-so-far solution with every batch's route replaced by the
        shortest route any ant has built for that batch, keeping pickers and
        sequence. Returns (solution, cost) if the result is valid, cold-chain
        compliant and strictly cheaper, else None.

        An ant's cost couples all its batches, so a short route inside an
        otherwise worse ant gets no credit. This elitist memory per batch (in
        the spirit of the best-so-far deposit of elitist Ant System and MMAS,
        Dorigo & Stuetzle 2004, ch. 3.3-3.4) recovers it; routes of different
        batches are independent. A shorter route is not always cheaper
        (finishing earlier can add earliness), hence the evaluator decides.
        """
        candidate = best_solution.copy()
        changed = False
        for batch, (_, route) in shortest_route_by_batch.items():
            if candidate.get_batch_route(batch) != route:
                candidate.set_batch_route(batch, list(route))
                changed = True
        if not changed or not validator.validate_solution(candidate):
            return None
        if validator.cold_chain_violation(candidate) != 0.0:
            return None
        cost = evaluator.evaluate(candidate)
        if cost < best_cost - 1e-9:
            return candidate, cost
        return None

    def _schedule_local_search(
        self,
        solution: RouteSolution,
        cost: float,
        validator: ConstraintsValidator,
        evaluator: RouteEvaluator,
    ) -> Tuple[RouteSolution, float]:
        """
        First-improvement local search on the schedule of `solution`, routes
        fixed: (1) move a batch to any position of another picker's sequence;
        (2) swap two batches within a picker's sequence; (3) exchange two
        batches between pickers. A move is kept only if the result is valid,
        cold-chain compliant and strictly cheaper; it repeats until no move
        improves. Returns the solution and its cost.

        Chen et al.'s ACO only routes. Here ants pick pickers by roulette and
        sequence each picker by earliest due date, a good rule but not
        optimal for this objective, so even with optimal routes the schedule
        alone can lose to OPP-Split's Stage 2. These are opp_hc's
        neighborhoods, applied exhaustively to the best-so-far solution (a
        sweep is O(B^2 * P) evaluations).
        """
        deadline = self._deadline

        def out_of_time():
            return deadline is not None and time.time() > deadline

        def accept(candidate):
            if not validator.validate_solution(candidate):
                return None
            if validator.cold_chain_violation(candidate) != 0.0:
                return None
            candidate_cost = evaluator.evaluate(candidate)
            return candidate_cost if candidate_cost < cost - 1e-9 else None

        batches = [b for b in self.B if solution.get_batch_picker(b) is not None]
        for _ in range(10 * max(len(batches), 1)):
            improved = False
            if out_of_time():
                break  # out of time: keep the best schedule so far

            for batch in batches:
                if out_of_time():
                    return solution, cost
                source = solution.get_batch_picker(batch)
                for target in self.P:
                    target_len = len(solution.get_picker_sequence(target)) - (1 if target == source else 0)
                    for position in range(target_len + 1):
                        candidate = solution.copy()
                        candidate.assign_batch_to_picker(batch, target, position)
                        if candidate.get_picker_sequence(target) == solution.get_picker_sequence(target):
                            continue
                        new_cost = accept(candidate)
                        if new_cost is not None:
                            solution, cost, improved = candidate, new_cost, True
                            break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                continue

            for i, first in enumerate(batches):
                if out_of_time():
                    return solution, cost
                for second in batches[i + 1:]:
                    p_first, p_second = solution.get_batch_picker(first), solution.get_batch_picker(second)
                    candidate = solution.copy()
                    if p_first == p_second:
                        sequence = candidate.get_picker_sequence(p_first)
                        a, b = sequence.index(first), sequence.index(second)
                        sequence[a], sequence[b] = sequence[b], sequence[a]
                        candidate.set_picker_sequence(p_first, sequence)
                    else:
                        seq_first = candidate.get_picker_sequence(p_first)
                        seq_second = candidate.get_picker_sequence(p_second)
                        seq_first[seq_first.index(first)] = second
                        seq_second[seq_second.index(second)] = first
                        candidate.set_picker_sequence(p_first, seq_first)
                        candidate.set_picker_sequence(p_second, seq_second)
                    new_cost = accept(candidate)
                    if new_cost is not None:
                        solution, cost, improved = candidate, new_cost, True
                        break
                if improved:
                    break

            if not improved:
                break

        return solution, cost

    def _fallback_route(self, required_locations: Set[str]) -> Optional[List[str]]:
        """
        Deterministic route for a batch whose ant constructions all failed:
        the farthest-insertion order (route_construction.insertion_route;
        Rosenkrantz, Stearns & Lewis 1977) forwards, else on the reversed
        graph, else the exhaustive best-first search (best_first_route,
        within _MAX_BFF_EXPANSIONS), polished with polish_route. Returns the
        full depot ... final list, or None if no simple route is found.

        Insertion goes first because it is cheap and gives a short route; the
        first route best_first_route finds can be long enough to break the
        cold chain. Cached per set of required locations, since the result
        is deterministic.
        """
        key = frozenset(required_locations)
        if key not in self._fallback_cache:
            depot = self.location_graph.get_depot()
            final = self.location_graph.get_final()
            full = route_construction.insertion_route(self.location_graph, required_locations)
            if full is None:
                backwards = route_construction.insertion_route(self._reversed_graph, required_locations)
                full = backwards[::-1] if backwards is not None else None
            if full is None:
                stops = route_construction.best_first_route(
                    self.location_graph, required_locations, self._MAX_BFF_EXPANSIONS
                )
                full = [depot] + stops + [final] if stops is not None else None
            if full is not None and self._POLISH_ELITE_ROUTES:
                full = [depot] + route_construction.polish_route(
                    self.location_graph, full[1:-1], required_locations, deadline=self._deadline,
                ) + [final]
            self._fallback_cache[key] = full
        self._fallback_calls += 1
        cached = self._fallback_cache[key]
        return list(cached) if cached is not None else None

    def _find_required_locations(
        self, batch: str, orders: Set[str], A: Dict
    ) -> Set[str]:
        """Find all locations that must be visited for a batch's orders."""
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        required = set()
        for order in orders:
            for vertex in self.location_graph.get_vertices():
                if vertex != depot and vertex != final:
                    if A.get((order, vertex), 0) > 0:
                        required.add(vertex)
        return required

    def _update_route_pheromones(
        self,
        pheromones: Dict[Tuple[str, str], float],
        evaporation_rate: float,
        batch_routes: List[Tuple[str, List[str]]],
    ) -> None:
        """
        MAX-MIN update of the (pick, pick) route pheromone (sources at
        _MMAS_TAU_MIN_RATIO): evaporate every pair, tau <- (1 - rho) tau,
        deposit 1 on the consecutive-pick pairs of each (batch, route) in
        `batch_routes` (per batch, its iteration-best and its best-so-far
        route) and clamp to [tau_min, tau_max].

        Pairs follow the order in which the route first reaches its picks,
        depot first and final last, as _build_batch_route chooses them. No
        cold-chain filter is needed: these are the shortest routes found, and
        a shorter route can only lower T_exec_pb.
        """
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        for pair in pheromones:
            pheromones[pair] = max(pheromones[pair] * (1.0 - evaporation_rate), self._tau_min)

        for batch, route in batch_routes:
            required = self._required_by_batch.get(batch, set())
            picks = [depot] + [v for v in route if v in required] + [final]
            for i in range(len(picks) - 1):
                pair = (picks[i], picks[i + 1])
                if pair in pheromones:
                    pheromones[pair] = min(pheromones[pair] + 1.0, self._tau_max)

    def _update_pheromones(
        self,
        picker_pheromones: Dict[Tuple[str, str], float],
        ant_solutions: List[Tuple[RouteSolution, float, Optional[Set[str]]]],
        evaporation_rate: float,
        q_factor: float,
        best_global_solution: Optional[RouteSolution] = None,
        best_global_cost: float = float('inf')
    ) -> None:
        """
        Evaporation and deposit on the (batch, picker) pheromone (the route
        pheromone has its own update, _update_route_pheromones). Each entry
        of `ant_solutions` is (solution, cost, compliant_batches). Ant System
        style: every ant deposits Q / cost, and the best-so-far solution
        deposits twice.
        """
        for key in picker_pheromones:
            picker_pheromones[key] *= (1.0 - evaporation_rate)
            picker_pheromones[key] = max(picker_pheromones[key], 0.01)

        for solution, cost, compliant_batches in ant_solutions:
            if cost <= 0:
                continue
            self._deposit_solution(solution, picker_pheromones, q_factor / cost, batches=compliant_batches)

        if best_global_solution and best_global_cost < float('inf') and best_global_cost > 0:
            # Every batch of best_global_solution is compliant: deposit for all.
            self._deposit_solution(best_global_solution, picker_pheromones, (q_factor / best_global_cost) * 2.0)

    def _deposit_solution(
        self,
        solution: RouteSolution,
        picker_pheromones: Dict[Tuple[str, str], float],
        amount: float,
        batches: Optional[Set[str]] = None,
    ) -> None:
        """
        Deposit on the (batch, picker) pairs of a solution, restricted to
        `batches` (None = every batch).

        Only cold-chain-compliant batches deposit: reinforcing the assignment
        of a batch that breaks T_cold would make the search converge on the
        very pattern that causes the violation. The other batches of the same
        ant still deposit, so they keep learning while one stays tight.
        """
        target_batches = batches if batches is not None else self.B
        for batch in target_batches:
            picker = solution.get_batch_picker(batch)
            if picker is not None and (batch, picker) in picker_pheromones:
                picker_pheromones[(batch, picker)] += amount

    def _calculate_route_distance(self, route: List[str]) -> float:
        """Total travel distance of depot -> route... -> final."""
        return exec_time.calculate_route_distance(self.location_graph, route)

    def _calculate_batch_execution_time(
        self, route: List[str], orders: Set[str], picker: str, params: SolveAcoModelDTO
    ) -> float:
        """
        T_exec_pb = T_setup + T_pick * sum(C_n)          [fixed, no speed]
                  + (T_travel * travel_distance + service_time) / V_p[picker]
        Same formula as RouteEvaluator's; this copy feeds the reported times.
        """
        return exec_time.T_exec_pb(
            self.location_graph, route, orders, picker,
            params.C_n, params.T_setup, params.T_pick, params.T_travel, params.S, params.V_p,
        )

    def _build_solution_info(
        self, solution: RouteSolution, cost: float, params: SolveAcoModelDTO
    ) -> dict:
        """Build the solution information dictionary for OutputHandler."""
        solution_info = {
            "status": "optimal",
            "objective_value": cost,
            "batch_times": {},
            "batch_completions": {},
            "picker_assignments": {},
            "tardiness": {},
            "earliness": {},
            "routes": {},
            "V_p": dict(params.V_p),
            "T_cold": params.T_cold,
        }

        batch_assignments = params.extract_batch_assignments()
        base_time = self.T_0 if self.T_0 is not None else 0

        for picker in self.P:
            current_time = base_time
            for batch in solution.get_picker_sequence(picker):
                route = solution.get_batch_route(batch)
                orders = batch_assignments.get(batch, set())

                T_exec_pb = self._calculate_batch_execution_time(route, orders, picker, params)
                current_time += T_exec_pb

                solution_info["batch_times"][batch] = T_exec_pb
                solution_info["batch_completions"][batch] = current_time
                solution_info["picker_assignments"][batch] = picker
                solution_info["routes"][batch] = route

        for order in self.N:
            order_batch = next(
                (b for b, orders in batch_assignments.items() if order in orders), None
            )
            if order_batch and order_batch in solution_info["batch_completions"]:
                c_b = solution_info["batch_completions"][order_batch]
                due_date = params.T_due_n.get(order, float("inf"))

                solution_info["tardiness"][order] = max(0, c_b - due_date)
                solution_info["earliness"][order] = max(0, due_date - c_b)

        return solution_info

    def _build_solution_output(self, solution: RouteSolution) -> OPPLocationGraph:
        """Convert the route solution into the OPPLocationGraph the output builder expects."""
        output_graph = OPPLocationGraph(
            depot_node=self.location_graph.get_depot(),
            final_node=self.location_graph.get_final(),
        )
        for vertex in self.location_graph.get_vertices():
            output_graph.add_vertex(vertex, "picking")

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        for batch in self.B:
            route = solution.get_batch_route(batch)
            if not route:
                continue

            if self.location_graph.has_edge(depot, route[0]):
                output_graph.add_edge(
                    depot, route[0], self.location_graph.get_distance(depot, route[0])
                )

            for i in range(len(route) - 1):
                n1, n2 = route[i], route[i + 1]
                if self.location_graph.has_edge(n1, n2):
                    output_graph.add_edge(
                        n1, n2, self.location_graph.get_distance(n1, n2)
                    )

            if self.location_graph.has_edge(route[-1], final):
                output_graph.add_edge(
                    route[-1], final, self.location_graph.get_distance(route[-1], final)
                )

        return output_graph
