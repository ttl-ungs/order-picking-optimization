"""
Ant Colony Optimization (ACO) heuristic for OPP v4 with picker speed and
cold chain.

Same problem as opp_aco_2 (multi-picker, all constraints validated):
- Receives: same SolveModelDTO parameters, plus a set of pickers (P)
- Validates: ALL constraints from opp_aco_2, plus cold-chain eligibility
- Optimizes: routes within batches (probabilistic ACO construction) AND
  the assignment/sequencing of batches to pickers (X_pb), so that batches
  on different pickers run in parallel and batches on the same picker are
  sequenced without overlap
- Output: compatible with build_output

Added on top of opp_aco_2 - picker speed and cold chain, the ACO
counterpart of opp_hc_4 (itself the Hill Climbing counterpart of opp_v5's
stage2_scheduling.zpl additions over opp_v4):

- Picker speed (V_p): a batch's execution time is no longer a single
  t_exec_b fixed for every picker. Instead t_exec_pb[p, b] = fixed_time(b)
  + route_time(b) / V_p[p], where fixed_time (setup + picking) doesn't
  depend on speed and route_time (travel + service) does. Faster pickers
  finish the same route sooner. This changes _select_picker's roulette:
  the (batch, picker) pheromone table is unchanged (still learns which
  picker suits which batch), but at selection time the candidate pool is
  filtered down to the batch's CURRENT ant's route's cold-chain-eligible
  pickers (see below) before the roulette runs.
- Cold chain (T_frio_max): a (picker, batch) pair is only eligible if
  t_exec_pb[p, b] <= T_frio_max. Since each ant builds a batch's route
  BEFORE picking its picker (same order as opp_aco_2's _build_ant_solution
  loop), eligibility for _select_picker is computed EXACTLY against that
  ant's own just-built route, not an approximation. If that particular
  route leaves zero pickers eligible, _select_picker falls back to the
  full unrestricted roulette -- see below for what happens to that ant's
  solution.

Cold chain is enforced as a HARD constraint on the reported final answer,
but a SOFT one (a large objective penalty) during the search itself -- see
models/opp_aco_4/utils/constraints_validator.py's module docstring for the
2026-09-09 audit finding this fixes (a single cold-chain-tight batch used
to make ConstraintsValidator.validate_solution() reject an ant's WHOLE
solution, starving pheromone updates for every batch, not just the tight
one) and _deposit_solution's docstring for why pheromone deposit is
filtered per-batch (compliant_batches), not per-solution.

Infeasibility detection is now HONEST: there is no upfront estimate-based
pre-check that can produce a false "infeasible" before the search ever
gets to try (a 2026-09-10 audit finding -- an earlier version of this file
pre-checked a greedy nearest-neighbor route-time ESTIMATE, which could be
worse than what an ant might actually construct, incorrectly declaring a
genuinely feasible instance infeasible). The ONLY upfront short-circuit
left is mathematically exact, not an estimate: batches_without_eligible_
picker is fed a route_time of EXACTLY 0.0 for every batch (the best
physically possible case -- real route_time is always >= 0), so a batch
flagged there is impossible under ANY route/picker whatsoever, not just
the one this run happened to try. Every other batch gets a genuine full
run of the ACO loop; best_global_solution is only ever set from a fully
cold-chain-compliant ant (see solve()), so if the loop finishes without
ever finding one, "infeasible" reflects an honest, exhausted search --
not a shortcut that gave up before trying.

Deliberately WITHOUT congestion between concurrent pickers (unlike
opp_aco_3): congestion and picker-speed/cold-chain are orthogonal
additions over opp_aco_2, and this model only needs the latter. opp_aco_3's
incremental CongestionTracker reservation and multi-pheromone (m-ACO4)
architecture are NOT adopted here, matching how opp_hc_4 leaves opp_hc_3's
congestion pricing out - kept focused on the speed/cold-chain trade-off,
matching opp_v5 itself, which also has no congestion (see analysis/config.py).
"""

import time
import random
import heapq
from collections import deque
from typing import Dict, List, Set, Optional, Tuple

from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO
from dtos.opp.solve_result import SolveResult
from dtos.opp.model_dto import ModelDTO
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
import models.utils.solve_registry as solve_registry
from models.opp_aco_2.utils.route_solution import RouteSolution
from models.opp_aco_4.utils.route_evaluator import RouteEvaluator
from models.opp_aco_4.utils.constraints_validator import ConstraintsValidator
from models.opp_v5.utils.cold_chain_validation import batches_without_eligible_picker


class OPPAntColonyOptimization(Model):
    """ACO solver for OPP v4 - picker speed + cold chain, no congestion."""

    _MAX_ROUTE_ATTEMPTS_PER_BATCH = 100

    # Multiplier applied to ConstraintsValidator.cold_chain_violation() (a
    # time-unit overrun) before adding it to an ant solution's cost -- see
    # constraints_validator.py's module docstring for why cold chain is a
    # SOFT constraint during search now (2026-09-09 audit fix). Large
    # enough to dominate the search away from violations (typical marginal
    # objective contribution per unit of recollection time is W_full,
    # usually single-to-low-double digits) without using an arbitrarily
    # huge Big-M-style constant -- this is a continuous heuristic penalty,
    # not a MIP constraint, so there's no SCIP-presolve-numerics failure
    # mode to worry about the way there was with opp_v5's M_seq.
    _COLD_CHAIN_PENALTY_WEIGHT = 1000.0

    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time
        self.P = sorted(dto.P) if getattr(dto, "P", None) else ["P1"]
        self._sp_dist = self._precompute_shortest_paths()

    def solve(self, params: SolveAco4ModelDTO):
        """
        Solves OPP v4 using the Ant Colony Optimization (ACO) heuristic,
        with picker speed and cold chain eligibility.
        """
        if params.Seed is not None:
            random.seed(params.Seed)

        start_time = time.time()

        if params.Bn is None:
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        if not (params.is_capacity_valid() and params.is_batch_assignment_valid()):
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        batch_assignments = params.extract_batch_assignments()

        num_ants = getattr(params, "_A_ants", 15)
        max_it = getattr(params, "_Max_it", 60)
        alpha = getattr(params, "_Alpha", 1.0)
        beta = getattr(params, "_Beta", 2.5)
        evaporation_rate = getattr(params, "_E", 0.15)
        q_factor = getattr(params, "_Q", 100.0)

        # Exact (not estimated) impossibility pre-check: fixed_time(b)
        # alone (setup + picking, independent of route/picker) already
        # tells us the BEST possible t_exec_pb for any picker, since
        # route_time is always >= 0 -- feeding batches_without_eligible_
        # picker a route_time of exactly 0.0 for every batch asks it "is
        # there a picker fast enough even for a zero-distance route?".
        # A batch flagged here is impossible under ANY route or picker,
        # not just one this run happened to try -- unlike the estimate-
        # based pre-check this replaces (2026-09-10 audit finding: a
        # greedy-nearest-neighbor ESTIMATE could be worse than what an ant
        # might actually construct, incorrectly declaring a genuinely
        # feasible instance infeasible before a single ant ever ran). See
        # header for the full rationale.
        best_case_route_time = {batch: 0.0 for batch in self.B}
        impossible_batches = batches_without_eligible_picker(
            self.P, self.B, self.N, params.C_n, params.Bn,
            params.B_setup, params.B_picking, best_case_route_time,
            self._picker_speeds(params), params.T_frio_max,
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
            B_time=params.B_time,
            B_setup=params.B_setup,
            B_picking=params.B_picking,
            S=params.S,
            V_p=params.V_p,
            T_frio_max=params.T_frio_max,
            P=self.P,
        )

        evaluator = RouteEvaluator(
            N=self.N,
            B=self.B,
            P=self.P,
            location_graph=self.location_graph,
            batch_assignments=batch_assignments,
            W_full=params.W_full,
            W_ea_ta=params.W_ea_ta,
            W_ea=params.W_ea,
            W_ta=params.W_ta,
            C_n=params.C_n,
            C_v=params.C_v,
            A=params.A,
            B_time=params.B_time,
            B_setup=params.B_setup,
            B_picking=params.B_picking,
            S=params.S,
            Dd=params.Dd,
            M=params.M,
            V_p=params.V_p,
        )

        pheromones = self._initialize_pheromones()
        picker_pheromones = self._initialize_picker_pheromones()

        best_global_solution = None
        best_global_cost = float("inf")
        iteration = 0

        while iteration < max_it:
            iteration += 1
            ant_solutions = []
            feasible_ant_solutions = []

            for ant in range(num_ants):
                ant_solution = self._build_ant_solution(
                    batch_assignments, pheromones, picker_pheromones, params, alpha, beta
                )

                # validate_solution() now checks ONLY opp_aco_2's original
                # hard constraints (topology/capacity/one-picker-per-batch)
                # -- cold chain is a soft penalty below, not a hard reject
                # here, so a single cold-chain-tight batch can no longer
                # starve pheromone updates for every OTHER batch in the
                # same ant (see constraints_validator.py's module docstring).
                if ant_solution is None or not validator.validate_solution(ant_solution):
                    continue

                base_cost = evaluator.evaluate(ant_solution)
                violation = validator.cold_chain_violation(ant_solution)
                cost = base_cost + self._COLD_CHAIN_PENALTY_WEIGHT * violation
                # Per-batch compliance set: which batches' route/picker
                # pheromone this ant is allowed to reinforce (see
                # _deposit_solution's docstring for why this must be
                # per-batch, not all-or-nothing for the whole solution).
                compliant_batches = validator.compliant_batches(ant_solution)
                ant_solutions.append((ant_solution, cost, compliant_batches))

                if violation == 0.0:
                    feasible_ant_solutions.append((ant_solution, base_cost))

            if not ant_solutions:
                continue

            # best_global_solution is tracked ONLY among cold-chain-COMPLIANT
            # ants (base_cost, unpenalized -- violation is 0 for these
            # anyway) so the reported final answer always satisfies
            # T_frio_max exactly, even though the search itself tolerates
            # temporary violations to keep learning.
            if feasible_ant_solutions:
                iter_best_feasible_solution, iter_best_feasible_cost = min(
                    feasible_ant_solutions, key=lambda x: x[1]
                )
                if iter_best_feasible_cost < best_global_cost:
                    best_global_solution = iter_best_feasible_solution.copy()
                    best_global_cost = iter_best_feasible_cost

            self._update_pheromones(
                pheromones,
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
                "W_full": params.W_full,
                "W_ea_ta": params.W_ea_ta,
                "W_ea": params.W_ea,
                "W_ta": params.W_ta,
                "C_v": params.C_v,
                "B_time": params.B_time,
                "B_setup": params.B_setup,
                "B_picking": params.B_picking,
                "M": params.M,
                "V_p": dict(params.V_p),
                "T_frio_max": params.T_frio_max,
                "N": len(self.N),
                "B": len(self.B),
                "P": len(self.P),
                "V": len(self.location_graph.get_vertices()),
                "A_ants": num_ants,
                "Max_it": max_it,
                "Alpha": alpha,
                "Beta": beta,
                "Max_route_attempts_per_batch": self._MAX_ROUTE_ATTEMPTS_PER_BATCH,
            },
        )
        solve_registry.register(solve_result)
        return solve_result

    def _register_infeasible(self, params: SolveAco4ModelDTO, elapsed: float) -> None:
        solve_registry.register(SolveResult(
            status="infeasible",
            output=None,
            elapsed=elapsed,
            params={
                "W_full": getattr(params, "W_full", None),
                "W_ea_ta": getattr(params, "W_ea_ta", None),
                "W_ea": getattr(params, "W_ea", None),
                "W_ta": getattr(params, "W_ta", None),
                "C_v": getattr(params, "C_v", None),
                "B_time": getattr(params, "B_time", None),
                "B_setup": getattr(params, "B_setup", None),
                "B_picking": getattr(params, "B_picking", None),
                "M": getattr(params, "M", None),
                "V_p": dict(getattr(params, "V_p", {}) or {}),
                "T_frio_max": getattr(params, "T_frio_max", None),
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

    def _picker_speed(self, picker: str, params: SolveAco4ModelDTO) -> float:
        return (params.V_p or {}).get(picker, 1.0)

    def _picker_speeds(self, params: SolveAco4ModelDTO) -> Dict[str, float]:
        return {p: self._picker_speed(p, params) for p in self.P}

    def _fixed_time(self, batch: str, batch_assignments: Dict[str, Set[str]], params: SolveAco4ModelDTO) -> float:
        """Setup + picking time -- the part of t_exec_pb that does NOT depend on picker speed."""
        orders = batch_assignments.get(batch, set())
        picking_capacity = sum(params.C_n.get(o, 0) for o in orders) if isinstance(params.C_n, dict) else 0
        return params.B_setup + params.B_picking * picking_capacity

    def _route_time(self, route: List[str], params: SolveAco4ModelDTO) -> float:
        """Travel time (B_time * distance) + service time -- opp_v5's R_b_time, the part scaled by V_p."""
        if not route:
            return 0.0
        service_time = sum(params.S.get(loc, 0) for loc in route) if isinstance(params.S, dict) else 0
        return params.B_time * self._calculate_route_distance(route) + service_time

    def _t_exec_pb(
        self, batch: str, route: List[str], picker: str,
        batch_assignments: Dict[str, Set[str]], params: SolveAco4ModelDTO,
    ) -> float:
        fixed_time = self._fixed_time(batch, batch_assignments, params)
        speed = self._picker_speed(picker, params)
        return fixed_time + self._route_time(route, params) / speed

    def _eligible_pickers_for_batch(
        self, batch: str, route: List[str], batch_assignments: Dict[str, Set[str]], params: SolveAco4ModelDTO,
    ) -> List[str]:
        """Pickers p for which t_exec_pb[p, batch] <= T_frio_max, given `route`."""
        return [
            p for p in self.P
            if self._t_exec_pb(batch, route, p, batch_assignments, params) <= params.T_frio_max + 1e-9
        ]

    # NOTE: this model used to have a route-time ESTIMATE (greedy nearest-
    # neighbor over _sp_dist, 2-opt-tightened) here, feeding a pre-check
    # that could declare a genuinely feasible instance "infeasible" before
    # a single ant ever ran (2026-09-09/10 audit findings -- see header).
    # Removed: the only pre-check left is the exact, estimate-free one in
    # solve() (route_time = 0.0 for every batch), and every batch that
    # survives it gets a real, full run of the ACO loop instead.

    def _precompute_shortest_paths(self) -> Dict[Tuple[str, str], float]:
        """Dijkstra from every node to get shortest-path distances."""
        vertices = self.location_graph.get_vertices()
        dist = {}
        for src in vertices:
            d = {src: 0.0}
            heap = [(0.0, src)]
            while heap:
                cost, node = heapq.heappop(heap)
                if cost > d.get(node, float("inf")):
                    continue
                for nbr in vertices:
                    if self.location_graph.has_edge(node, nbr):
                        new_cost = cost + self.location_graph.get_distance(node, nbr)
                        if new_cost < d.get(nbr, float("inf")):
                            d[nbr] = new_cost
                            heapq.heappush(heap, (new_cost, nbr))
            for dst in vertices:
                dist[(src, dst)] = d.get(dst, float("inf"))
        return dist

    def _initialize_pheromones(self) -> Dict[Tuple[str, str], float]:
        """Initializes the edge pheromone matrix 2D (origin, destination) with a base value of 1.0 for valid edges."""
        pheromones = {}
        vertices = self.location_graph.get_vertices()
        for i in vertices:
            for j in vertices:
                if self.location_graph.has_edge(i, j):
                    pheromones[(i, j)] = 1.0
        return pheromones

    def _initialize_picker_pheromones(self) -> Dict[Tuple[str, str], float]:
        """Initializes the batch/picker assignment pheromone table (X_pb) with a base value of 1.0."""
        return {(b, p): 1.0 for b in self.B for p in self.P}

    def _build_ant_solution(
        self,
        batch_assignments: Dict[str, Set[str]],
        pheromones: Dict[Tuple[str, str], float],
        picker_pheromones: Dict[Tuple[str, str], float],
        params: SolveAco4ModelDTO,
        alpha: float,
        beta: float,
    ) -> Optional[RouteSolution]:
        """
        Each ant constructs a feasible route per batch AND assigns every
        batch that has orders to a COLD-CHAIN-ELIGIBLE picker (X_pb).
        Returns a RouteSolution, or None if the ant got stuck building a route.
        """
        solution = RouteSolution(self.B, self.location_graph, batch_assignments, self.P)
        picker_load = {p: 0 for p in self.P}

        for batch in self.B:
            if not batch_assignments.get(batch):
                continue

            required_locations = self._find_required_locations(
                batch, batch_assignments[batch], params.A
            )

            if required_locations:
                route = None
                for _ in range(self._MAX_ROUTE_ATTEMPTS_PER_BATCH):
                    candidate = self._build_batch_route(required_locations, pheromones, alpha, beta)
                    if candidate is not None and len(candidate) == len(set(candidate)):
                        route = candidate
                        break
                if route is None:
                    return None
                solution.set_batch_route(batch, route[1:-1])

            picker = self._select_picker(
                batch, picker_pheromones, picker_load, alpha, beta,
                solution.get_batch_route(batch), batch_assignments[batch], params,
            )
            solution.assign_batch_to_picker(batch, picker)
            picker_load[picker] += 1

        self._sort_picker_queues_by_due_date(solution, batch_assignments, params.Dd)

        return solution

    def _sort_picker_queues_by_due_date(
        self,
        solution: "RouteSolution",
        batch_assignments: Dict[str, Set[str]],
        due_dates: Dict[str, float],
    ) -> None:
        """Reorders every picker's queue by ascending earliest-due-date among the orders in each batch."""
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
        params: SolveAco4ModelDTO,
    ) -> str:
        """
        Roulette-wheel selection of a picker for a batch, combining the
        (batch, picker) pheromone with a load-balancing visibility term,
        restricted to pickers that are cold-chain-eligible for THIS ant's
        just-built route. Falls back to the unrestricted pool if none are
        eligible (see header) so the ant still produces a complete
        solution -- it will simply fail the cold-chain validator and get
        discarded, like any other infeasible ant.
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
    ) -> Optional[List[str]]:
        """Probabilistically constructs a batch route visiting all required locations."""
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        route = [depot]
        visited = {depot}
        unvisited_req = set(required_locations)
        current = depot

        max_steps = 4 * max(len(self.location_graph.get_vertices()), 1)
        steps = 0

        while unvisited_req:
            steps += 1
            if steps > max_steps:
                return None

            neighbors = [
                n
                for n in self.location_graph.get_neighbors(current)
                if n not in visited
                and n != final
            ]

            if not neighbors:
                neighbors = [
                    n
                    for n in self.location_graph.get_neighbors(current)
                    if n != final
                ]
                if not neighbors:
                    return None

            probabilities = []
            total_prob = 0.0

            for n in neighbors:
                tau = pheromones.get((current, n), 1.0) ** alpha

                dist = self.location_graph.get_distance(current, n)
                dist = dist if dist > 0 else 0.01

                if n in unvisited_req:
                    eta = (1.5 / dist) ** beta
                else:
                    min_dist_to_req = min(self._sp_dist.get((n, req), float("inf")) for req in unvisited_req)
                    min_dist_to_req = min_dist_to_req if min_dist_to_req > 0 else 0.01
                    eta = (1.0 / (dist + min_dist_to_req)) ** beta

                prob = tau * eta
                probabilities.append((n, prob))
                total_prob += prob

            if total_prob == 0:
                return None

            rand_val = random.uniform(0, total_prob)
            cumulative = 0.0
            next_node = neighbors[-1]

            for n, p in probabilities:
                cumulative += p
                if rand_val <= cumulative:
                    next_node = n
                    break

            route.append(next_node)
            visited.add(next_node)
            if next_node in unvisited_req:
                unvisited_req.remove(next_node)
            current = next_node

        tail_route = self._find_shortest_path_bfs(current, final, visited)
        if tail_route is None:
            tail_route = self._find_shortest_path_bfs(current, final, set())
        if tail_route is None:
            return None

        route.extend(tail_route[1:])
        return route

    def _find_shortest_path_bfs(self, start: str, end: str, visited_nodes: Set[str]) -> Optional[List[str]]:
        if start == end:
            return [start]
        queue = deque([[start]])
        explored = set(visited_nodes) - {end}
        while queue:
            path = queue.popleft()
            node = path[-1]
            if node == end:
                return path
            for neighbor in self.location_graph.get_neighbors(node):
                if neighbor not in explored:
                    explored.add(neighbor)
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)
        return None

    def _find_required_locations(
        self, batch: str, orders: Set[str], A: Dict
    ) -> Set[str]:
        """Finds all locations that MUST be visited for a given batch's orders."""
        required = set()
        for order in orders:
            for vertex in self.location_graph.get_vertices():
                if (
                    vertex != self.location_graph.get_depot()
                    and vertex != self.location_graph.get_final()
                ):
                    if A.get((order, vertex), 0) > 0:
                        required.add(vertex)
        return required

    def _update_pheromones(
        self,
        pheromones: Dict[Tuple[str, str], float],
        picker_pheromones: Dict[Tuple[str, str], float],
        ant_solutions: List[Tuple[RouteSolution, float, Optional[Set[str]]]],
        evaporation_rate: float,
        q_factor: float,
        best_global_solution: Optional[RouteSolution] = None,
        best_global_cost: float = float('inf')
    ) -> None:
        """
        Evaporation + deposit on both the edge and (batch, picker)
        pheromone tables. Each entry in `ant_solutions` is now a
        (solution, cost, compliant_batches) triple -- see
        _deposit_solution's docstring for why deposit is filtered to
        `compliant_batches` instead of depositing for the whole solution.
        """
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        for edge in pheromones:
            pheromones[edge] *= (1.0 - evaporation_rate)
            pheromones[edge] = max(pheromones[edge], 0.01)

        for key in picker_pheromones:
            picker_pheromones[key] *= (1.0 - evaporation_rate)
            picker_pheromones[key] = max(picker_pheromones[key], 0.01)

        for solution, cost, compliant_batches in ant_solutions:
            if cost <= 0:
                continue
            deposit_amount = q_factor / cost
            self._deposit_solution(
                solution, pheromones, picker_pheromones, deposit_amount, depot, final,
                batches=compliant_batches,
            )

        if best_global_solution and best_global_cost < float('inf') and best_global_cost > 0:
            elitist_deposit = (q_factor / best_global_cost) * 2.0
            # best_global_solution is only ever set from a cold-chain-
            # compliant ant (see solve()'s feasible_ant_solutions), so every
            # one of its batches is compliant -- deposit for all of them.
            self._deposit_solution(best_global_solution, pheromones, picker_pheromones, elitist_deposit, depot, final)

    def _deposit_solution(
        self,
        solution: RouteSolution,
        pheromones: Dict[Tuple[str, str], float],
        picker_pheromones: Dict[Tuple[str, str], float],
        amount: float,
        depot: str,
        final: str,
        batches: Optional[Set[str]] = None,
    ) -> None:
        """
        Deposit pheromone on the edges and (batch, picker) pair used by a
        solution, restricted to `batches` (None means every batch in
        self.B -- used for the elitist best_global_solution deposit, always
        fully cold-chain-compliant by construction).

        Restricting to cold-chain-COMPLIANT batches only (rather than
        depositing for the whole ant solution whenever its overall
        cold-chain PENALTY happens to still let it through, which is what
        the very first version of this soft-constraint fix did) matters a
        lot in practice: depositing for a batch's route/picker pheromone
        even when THAT batch violates T_frio_max reinforces exactly the
        edges/assignment that caused the violation. Verified empirically
        (2026-09-09) on an adversarial two-node instance where the
        violating construction was ~94% likely per ant vs. ~6% for the
        compliant one: depositing indiscriminately made the violating
        edges' pheromone grow while the compliant edges' decayed to the
        floor within ~10 iterations, and the compliant route was NEVER
        found again after that (pheromone-reinforced premature convergence
        onto the wrong pattern) -- worse than not touching cold chain
        during search at all. Skipping deposit for individually-violating
        batches (while still depositing for every OTHER, compliant batch
        in the same ant solution) avoids that: a batch's own edges only
        ever get reinforced when it happens to be built compliant, exactly
        like a hard per-solution reject would behave for a single-batch
        instance, while still letting sibling batches in a multi-batch
        instance learn normally even while one stays cold-chain-tight --
        the actual goal of making cold chain soft in the first place.
        """
        target_batches = batches if batches is not None else self.B
        for batch in target_batches:
            route = solution.get_batch_route(batch)
            if route:
                full_route = [depot] + route + [final]
                for i in range(len(full_route) - 1):
                    edge = (full_route[i], full_route[i + 1])
                    if edge in pheromones:
                        pheromones[edge] += amount

            picker = solution.get_batch_picker(batch)
            if picker is not None and (batch, picker) in picker_pheromones:
                picker_pheromones[(batch, picker)] += amount

    def _calculate_route_distance(self, route: List[str]) -> float:
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

    def _calculate_batch_execution_time(
        self, route: List[str], orders: Set[str], picker: str, params: SolveAco4ModelDTO
    ) -> float:
        """
        t_exec_pb = B_setup + B_picking * sum(C_n)          [fixed, no speed]
                  + (B_time * travel_distance + service_time) / V_p[picker]
        (same formula as RouteEvaluator._calculate_batch_execution_time --
        kept here too since this copy also drives the reported
        batch_times/batch_completions/tardiness/earliness, same split
        opp_aco_2/opp_hc_4 use between the search's evaluator and this
        reporting-only helper).
        """
        picking_capacity = sum(params.C_n.get(o, 0) for o in orders) if isinstance(params.C_n, dict) else 0
        picking_time = params.B_picking * picking_capacity
        travel_time = params.B_time * self._calculate_route_distance(route)
        service_time = sum(params.S.get(loc, 0) for loc in route) if isinstance(params.S, dict) else 0
        speed = self._picker_speed(picker, params)
        return params.B_setup + picking_time + (travel_time + service_time) / speed

    def _build_solution_info(
        self, solution: RouteSolution, cost: float, params: SolveAco4ModelDTO
    ) -> dict:
        """Structures the data expected by the output_handler (Picker assignments, Tardiness, Earliness)."""
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
            "T_frio_max": params.T_frio_max,
        }

        batch_assignments = params.extract_batch_assignments()
        base_time = self.T_0 if self.T_0 is not None else 0

        for picker in self.P:
            current_time = base_time
            for batch in solution.get_picker_sequence(picker):
                route = solution.get_batch_route(batch)
                orders = batch_assignments.get(batch, set())

                t_exec_pb = self._calculate_batch_execution_time(route, orders, picker, params)
                current_time += t_exec_pb

                solution_info["batch_times"][batch] = t_exec_pb
                solution_info["batch_completions"][batch] = current_time
                solution_info["picker_assignments"][batch] = picker
                solution_info["routes"][batch] = route

        for order in self.N:
            order_batch = next(
                (b for b, orders in batch_assignments.items() if order in orders), None
            )
            if order_batch and order_batch in solution_info["batch_completions"]:
                v_b = solution_info["batch_completions"][order_batch]
                due_date = params.Dd.get(order, float("inf"))

                solution_info["tardiness"][order] = max(0, v_b - due_date)
                solution_info["earliness"][order] = max(0, due_date - v_b)

        return solution_info

    def _build_solution_output(self, solution: RouteSolution) -> OPPLocationGraph:
        """Converts the ACO route solution into the OPPLocationGraph format required by the output builder."""
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
