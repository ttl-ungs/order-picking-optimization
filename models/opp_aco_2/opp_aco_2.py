"""
Ant Colony Optimization (ACO) heuristic for OPP v4 with ALL constraints validation.

Same problem as opp_model_v4.zpl:
- Receives: same SolveModelDTO parameters, plus a set of pickers (P)
- Validates: ALL constraints from the exact model
- Optimizes: routes within batches (probabilistic ACO construction) AND the
  assignment/sequencing of batches to pickers (X_pb), so that batches on
  different pickers run in parallel and batches on the same picker are
  sequenced without overlap
- Output: compatible with build_output

Each ant constructs a complete solution: a route per batch (as in opp_aco)
plus a picker assignment for every batch that has orders, guided by a second
pheromone table over (batch, picker) pairs. This extends the classic ACO
construction step to also decide "which machine runs this job", the ACO
analogue of the neighbor moves opp_hc_2 adds on top of opp_hc.
"""

import time
import random
import heapq
from collections import deque
from typing import Dict, List, Set, Optional, Tuple

from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from dtos.opp.solve_result import SolveResult
from dtos.opp.model_dto import ModelDTO
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
import models.utils.solve_registry as solve_registry
from models.opp_aco_2.utils.route_solution import RouteSolution
from models.opp_aco_2.utils.route_evaluator import RouteEvaluator
from models.opp_aco_2.utils.constraints_validator import ConstraintsValidator


class OPPAntColonyOptimization(Model):
    """ACO solver for OPP v4 - validates ALL constraints, parallelizes over pickers."""

    # How many times a single batch's route construction may be retried within
    # one ant before that ant gives up entirely. Without this, one ant needs
    # EVERY batch's random construction to come out loop-free simultaneously --
    # with per-batch clean rates as low as ~5-10% on a 10x10+ grid, requiring
    # all of them at once in one draw is effectively impossible past a
    # handful of batches. Retrying just the batch that failed
    # -- instead of discarding the whole multi-batch solution --
    # is what fixes that, since each batch's route is independent of the others.
    _MAX_ROUTE_ATTEMPTS_PER_BATCH = 100

    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time
        # P: pickers. Falls back to a single implicit picker for callers that
        # don't provide one (equivalent to the old, non-parallel behaviour).
        self.P = sorted(dto.P) if getattr(dto, "P", None) else ["P1"]
        self._sp_dist = self._precompute_shortest_paths()

    def solve(self, params: SolveAcoModelDTO):
        """
        Solves the OPP v4 using the Ant Colony Optimization (ACO) heuristic.

        Args:
            params (SolveAcoModelDTO): DTO containing exact model and ACO parameters.
        """
        start_time = time.time()

        # Initial validation analogous to opp_v3 / opp_hc_2
        if params.Bn is None:
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        if not (params.is_capacity_valid() and params.is_batch_assignment_valid()):
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        batch_assignments = params.extract_batch_assignments()

        # ACO specific parameters safely extracted from the DTO
        num_ants = getattr(params, "_A_ants", 15)
        max_it = getattr(params, "_Max_it", 60)
        alpha = getattr(params, "_Alpha", 1.0)
        beta = getattr(params, "_Beta", 2.5)
        evaporation_rate = getattr(params, "_E", 0.15)
        q_factor = getattr(params, "_Q", 100.0)

        validator = ConstraintsValidator(
            N=self.N,
            B=self.B,
            location_graph=self.location_graph,
            batch_assignments=batch_assignments,
            C_n=params.C_n,
            C_v=params.C_v,
            A=params.A,
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
        )

        # 1. Pheromone Initialization (edges + batch/picker assignment)
        pheromones = self._initialize_pheromones()
        picker_pheromones = self._initialize_picker_pheromones()

        best_global_solution = None
        best_global_cost = float("inf")
        iteration = 0

        # Main ACO loop
        while iteration < max_it:
            iteration += 1
            ant_solutions = []

            # 2. Solution construction per ant
            for ant in range(num_ants):
                ant_solution = self._build_ant_solution(
                    batch_assignments, pheromones, picker_pheromones, params, alpha, beta
                )

                if ant_solution is not None and validator.validate_solution(ant_solution):
                    cost = evaluator.evaluate(ant_solution)
                    ant_solutions.append((ant_solution, cost))

            if not ant_solutions:
                continue  # No ant found a feasible solution in this iteration

            # 3. Update the global best solution
            iter_best_solution, iter_best_cost = min(ant_solutions, key=lambda x: x[1])
            if iter_best_cost < best_global_cost:
                best_global_solution = iter_best_solution.copy()
                best_global_cost = iter_best_cost

            # 4. Pheromone Update
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

        # Notify the OutputHandler (Observer Pattern)
        solution_info = self._build_solution_info(
            best_global_solution, best_global_cost, params
        )
        self.last_solution_info = solution_info
        super().notify(solution_info=solution_info)

        # Build and register the final result
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

    def _register_infeasible(self, params: SolveAcoModelDTO, elapsed: float) -> None:
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
        params: SolveAcoModelDTO,
        alpha: float,
        beta: float,
    ) -> Optional[RouteSolution]:
        """
        Each ant constructs a feasible route per batch AND assigns every
        batch that has orders to a picker (X_pb). Returns a RouteSolution,
        or None if the ant got stuck building a route.
        """
        solution = RouteSolution(self.B, self.location_graph, batch_assignments, self.P)
        picker_load = {p: 0 for p in self.P}

        for batch in self.B:
            if not batch_assignments.get(batch):
                continue  # No orders -> no route and no picker required

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
                    return None  # Batch never came out loop-free even after retrying
                # Routes are stored excluding depot/final (RouteSolution convention)
                solution.set_batch_route(batch, route[1:-1])

            picker = self._select_picker(batch, picker_pheromones, picker_load, alpha, beta)
            solution.assign_batch_to_picker(batch, picker)
            picker_load[picker] += 1

        # Fix (2026-08-28): a picker's processing queue used to always be
        # the sorted-by-batch-ID subsequence of its assigned batches (since
        # the loop above always appends in `self.B` order, i.e. sorted
        # batch IDs, which have no relationship to due dates) -- ACO never
        # searched or even considered WHICH order to process a picker's
        # batches in, unlike opp_hc_2's `_generate_sequence_swap_neighbor`,
        # which explicitly explores swapping two batches' order. Sort each
        # picker's queue by earliest-due-date instead (classic single-
        # machine scheduling heuristic for reducing tardiness) so
        # sequencing is at least informed by due dates, closing most of the
        # gap versus HC without adding a new pheromone dimension.
        self._sort_picker_queues_by_due_date(solution, batch_assignments, params.Dd)

        return solution

    def _sort_picker_queues_by_due_date(
        self,
        solution: "RouteSolution",
        batch_assignments: Dict[str, Set[str]],
        due_dates: Dict[str, float],
    ) -> None:
        """
        Reorders every picker's queue by ascending earliest-due-date among
        the orders in each batch (ties broken by batch id for determinism).
        A batch with no orders (shouldn't normally reach here) sorts last.
        """
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
    ) -> str:
        """
        Roulette-wheel selection of a picker for a batch, combining the
        (batch, picker) pheromone with a load-balancing visibility term
        (favors currently less-loaded pickers), analogous to the distance
        visibility used for route construction.
        """
        weights = []
        total_weight = 0.0
        for picker in self.P:
            tau = picker_pheromones.get((batch, picker), 1.0) ** alpha
            eta = (1.0 / (1.0 + picker_load[picker])) ** beta
            weight = tau * eta
            weights.append((picker, weight))
            total_weight += weight

        if total_weight <= 0:
            return random.choice(self.P)

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

        # Safety valve for the backtracking fallback below: bounds how long a
        # single ant can wander before giving up, so allowing revisits can't
        # turn into an unbounded walk on an unlucky draw.
        max_steps = 4 * max(len(self.location_graph.get_vertices()), 1)
        steps = 0

        # Phase 1: Visit all required nodes
        while unvisited_req:
            steps += 1
            if steps > max_steps:
                return None  # Genuinely stuck wandering, not just one dead end

            neighbors = [
                n
                for n in self.location_graph.get_neighbors(current)
                if n not in visited
                and n != final
            ]

            if not neighbors:
                # Fall back to allowing a step onto an already-visited,
                # non-required node so the ant can retrace its way out.
                neighbors = [
                    n
                    for n in self.location_graph.get_neighbors(current)
                    if n != final
                ]
                if not neighbors:
                    return None  # Truly isolated node

            # Roulette wheel selection based on pheromones and visibility
            probabilities = []
            total_prob = 0.0

            for n in neighbors:
                # Batch-specific pheromone query
                tau = pheromones.get((current, n), 1.0) ** alpha

                dist = self.location_graph.get_distance(current, n)
                dist = dist if dist > 0 else 0.01

                # Dynamic visibility oriented towards the nearest remaining target
                if n in unvisited_req:
                    eta = (1.5 / dist) ** beta  # High priority because it is an immediately required node
                else:
                    # Shortest-path distance to nearest required node (not just direct edge)
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

        # Optimal deterministic connection (BFS) to the final node to avoid deadlocks.
        # Try the clean path first (avoiding every node Phase 1 already stepped on --
        # keeps the route loop-free). Only if THAT
        # fails do we allow BFS to revisit an already-used node -- strictly a last
        # resort, since trying the  unrestricted search first could pick a revisiting
        # path over an equally-short clean one that was actually available.
        tail_route = self._find_shortest_path_bfs(current, final, visited)
        if tail_route is None:
            tail_route = self._find_shortest_path_bfs(current, final, set())
        if tail_route is None:
            return None  # There is no physical connection to the output node

        # Phase 2: Connect to the final node
        route.extend(tail_route[1:])
        return route

    def _find_shortest_path_bfs(self, start: str, end: str, visited_nodes: Set[str]) -> Optional[List[str]]:
        if start == end:
            return [start]
        queue = deque([[start]])
        explored = set(visited_nodes) - {end}  # Mandatory allow discovery of the final node
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
        ant_solutions: List[Tuple[RouteSolution, float]],
        evaporation_rate: float,
        q_factor: float,
        best_global_solution: Optional[RouteSolution] = None,
        best_global_cost: float = float('inf')
    ) -> None:
        """
        Applies evaporation and pheromone deposit based on ant solutions, on
        both the edge pheromone table (routing) and the batch/picker
        assignment pheromone table (X_pb). Elite upgrade: provides a strong
        additional boost to the best historical solution found.
        """
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        # Evaporation
        for edge in pheromones:
            pheromones[edge] *= (1.0 - evaporation_rate)
            pheromones[edge] = max(pheromones[edge], 0.01)

        for key in picker_pheromones:
            picker_pheromones[key] *= (1.0 - evaporation_rate)
            picker_pheromones[key] = max(picker_pheromones[key], 0.01)

        # Deposit (iterating over all ants that found a feasible solution)
        for solution, cost in ant_solutions:
            if cost <= 0:
                continue
            deposit_amount = q_factor / cost
            self._deposit_solution(solution, pheromones, picker_pheromones, deposit_amount, depot, final)

        # Elite Component: Extra bonus deposit for the best historical solution
        if best_global_solution and best_global_cost < float('inf') and best_global_cost > 0:
            elitist_deposit = (q_factor / best_global_cost) * 2.0
            self._deposit_solution(best_global_solution, pheromones, picker_pheromones, elitist_deposit, depot, final)

    def _deposit_solution(
        self,
        solution: RouteSolution,
        pheromones: Dict[Tuple[str, str], float],
        picker_pheromones: Dict[Tuple[str, str], float],
        amount: float,
        depot: str,
        final: str,
    ) -> None:
        """Deposit pheromone on the edges and (batch, picker) pair used by a solution."""
        for batch in self.B:
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
        self, route: List[str], orders: Set[str], params: SolveAcoModelDTO
    ) -> float:
        """EXACT V3 t_exec formula (Constraint 18 replication)."""
        picking_capacity = sum(params.C_n.get(o, 0) for o in orders) if isinstance(params.C_n, dict) else 0
        picking_time = params.B_picking * picking_capacity
        travel_time = params.B_time * self._calculate_route_distance(route)
        service_time = sum(params.S.get(loc, 0) for loc in route) if isinstance(params.S, dict) else 0
        return params.B_setup + picking_time + travel_time + service_time

    def _build_solution_info(
        self, solution: RouteSolution, cost: float, params: SolveAcoModelDTO
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
        }

        batch_assignments = params.extract_batch_assignments()
        # Each picker processes its assigned batches sequentially, starting
        # from T_0; different pickers run in parallel.
        base_time = self.T_0 if self.T_0 is not None else 0

        for picker in self.P:
            current_time = base_time
            for batch in solution.get_picker_sequence(picker):
                route = solution.get_batch_route(batch)
                orders = batch_assignments.get(batch, set())

                t_exec_b = self._calculate_batch_execution_time(route, orders, params)
                current_time += t_exec_b

                solution_info["batch_times"][batch] = t_exec_b
                solution_info["batch_completions"][batch] = current_time
                solution_info["picker_assignments"][batch] = picker
                solution_info["routes"][batch] = route

        # Earliness and Tardiness calculations
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
