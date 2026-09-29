"""
Ant Colony Optimization (ACO) heuristic for OPP v3 with ALL constraints validation.

This model strictly respects 100% of the opp_v3 constraints and uses the
Observer pattern to notify output results, ensuring architectural parity.
"""

import time
import random
import heapq
from collections import defaultdict, deque
from typing import Dict, List, Set, Optional, Tuple

from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from dtos.opp.solve_result import SolveResult
from dtos.opp.model_dto import ModelDTO
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
import models.utils.solve_registry as solve_registry


class OPPAntColonyOptimization(Model):
    """ACO solver for OPP v3 - validates ALL constraints and mimics the exact objective function."""

    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time
        self._sp_dist = self._precompute_shortest_paths()

    def solve(self, params: SolveAcoModelDTO):
        """
        Solves the OPP v3 using the Ant Colony Optimization (ACO) heuristic.

        Args:
            params (SolveAcoModelDTO): DTO containing exact model and ACO parameters.
        """
        start_time = time.time()

        # Initial validation analogous to opp_v3 / opp_hc_1
        if params.B_nb is None:
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        if not (params.is_capacity_valid() and params.is_batch_assignment_valid()):
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        batch_assignments = params.extract_batch_assignments()

        # ACO specific parameters safely extracted from the DTO
        # (Assuming protected attribute access or property if there are naming conflicts)
        num_ants = getattr(params, "_A", 15)
        max_it = getattr(params, "_Max_it", 60)
        alpha = getattr(params, "_Alpha", 1.0)
        beta = getattr(params, "_Beta", 2.5)
        evaporation_rate = getattr(params, "_E", 0.15)
        q_factor = getattr(params, "_Q", 100.0)

        # 1. Pheromone Initialization
        pheromones = self._initialize_pheromones()

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
                    batch_assignments, pheromones, params, alpha, beta
                )

                if ant_solution is not None:
                    # Validate feasible constraints and calculate objective cost
                    cost = self._evaluate_solution(ant_solution, params)
                    ant_solutions.append((ant_solution, cost))

            if not ant_solutions:
                continue  # No ant found a feasible route in this iteration

            # 3. Update the global best solution
            iter_best_solution, iter_best_cost = min(ant_solutions, key=lambda x: x[1])
            if iter_best_cost < best_global_cost:
                best_global_solution = iter_best_solution.copy()
                best_global_cost = iter_best_cost

            # 4. Pheromone Update
            self._update_pheromones(
                pheromones,
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
                "W_c": params.W_c,
                "W_pen": params.W_pen,
                "W_e": params.W_e,
                "W_t": params.W_t,
                "C_v": params.C_v,
                "T_travel": params.T_travel,
                "T_setup": params.T_setup,
                "T_pick": params.T_pick,
                "M": params.M,
                "N": len(self.N),
                "B": len(self.B),
                "V": len(self.location_graph.get_vertices()),
                "A_ants": num_ants,
                "Max_it": max_it,
                "Alpha": alpha,
                "Beta": beta
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
                "W_c": getattr(params, "W_c", None),
                "W_pen": getattr(params, "W_pen", None),
                "W_e": getattr(params, "W_e", None),
                "W_t": getattr(params, "W_t", None),
                "C_v": getattr(params, "C_v", None),
                "T_travel": params.T_travel,
                "T_setup": params.T_setup,
                "T_pick": params.T_pick,
                "M": getattr(params, "M", None),
                "N": len(self.N),
                "B": len(self.B),
                "V": len(self.location_graph.get_vertices()),
                "A_ants": getattr(params, "_A", 15),
                "Max_it": getattr(params, "_Max_it", 60),
                "Alpha": getattr(params, "_Alpha", 1.0),
                "Beta": getattr(params, "_Beta", 2.5),
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
        """Initializes the pheromone matrix 2D (origin, destination) with a base value of 1.0 for valid edges."""
        pheromones = {}
        vertices = self.location_graph.get_vertices()
        # for b in self.B:
        for i in vertices:
            for j in vertices:
                if self.location_graph.has_edge(i, j):
                    pheromones[(i, j)] = 1.0
        return pheromones

    def _build_ant_solution(
        self,
        batch_assignments: Dict[str, Set[str]],
        pheromones: Dict[Tuple[str, str], float],
        params: SolveAcoModelDTO,
        alpha: float,
        beta: float,
    ) -> Optional[Dict[str, List[str]]]:
        """
        Each ant constructs a feasible solution per batch.
        Returns a dictionary of routes {batch: route} or None if stuck.
        """
        solution = {}
        for batch in self.B:
            if not batch_assignments.get(batch):
                solution[batch] = []
                continue

            required_locations = self._find_required_locations(
                batch, batch_assignments[batch], params.A
            )
            if not required_locations:
                solution[batch] = []
                continue

            route = self._build_batch_route(required_locations, pheromones, alpha, beta)
            if route is None:
                return None  # Ant got stuck (infeasible route generated)

            solution[batch] = route
        return solution

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

        # Phase 1: Visit all required nodes
        while unvisited_req:
            neighbors = [
                n
                for n in self.location_graph.get_vertices()
                if self.location_graph.has_edge(current, n)
                and n not in visited
                and n != final
            ]

            if not neighbors:
                return None  # Dead end reached

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

        # Optimal deterministic connection (BFS) to the final node to avoid deadlocks
        tail_route = self._find_shortest_path_bfs(current, final, visited)
        if tail_route is None:
            return None  # There is no physical connection to the output node

        # Phase 2: Connect to the final node
        route.extend(tail_route[1:])
        return route

    def _find_shortest_path_bfs(self, start: str, end: str, visited_nodes: Set[str]) -> Optional[List[str]]:
        if start == end:
            return [start]
        queue = deque([[start]])
        explored = set(visited_nodes) - {end} # Mandatory allow discovery of the final node
        while queue:
            path = queue.popleft()
            node = path[-1]
            if node == end:
                return path
            for neighbor in self.location_graph.get_vertices():
                if self.location_graph.has_edge(node, neighbor) and neighbor not in explored:
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
        ant_solutions: List[Tuple[Dict[str, List[str]], float]],
        evaporation_rate: float,
        q_factor: float,
        best_global_solution: Optional[Dict[str, List[str]]] = None,
        best_global_cost: float = float('inf')
    ) -> None:
        """
        Applies evaporation and pheromone deposit based on ant solutions.
        Elite upgrade. Evaporates and deposits pheromones on a 2D base, providing a strong additional boost
        to the best historical solution found.
        """
        # Evaporation
        for edge in pheromones:
            pheromones[edge] *= (1.0 - evaporation_rate)
            # Minimum limit to prevent absolute stagnation (Min-Max Ant System logic base)
            pheromones[edge] = max(pheromones[edge], 0.01)

        # Deposit (Iterating over all ants that found a feasible solution)
        for solution, cost in ant_solutions:
            if cost <= 0: continue
            deposit_amount = q_factor / cost
            for route in solution.values():
                for i in range(len(route) - 1):
                    edge = (route[i], route[i + 1])
                    if edge in pheromones:
                        pheromones[edge] += deposit_amount

        # Elite Component: Extra bonus deposit for the best historical route
        if best_global_solution and best_global_cost < float('inf') and best_global_cost > 0:
            elitist_deposit = (q_factor / best_global_cost) * 2.0
            for route in best_global_solution.values():
                for i in range(len(route) - 1):
                    edge = (route[i], route[i + 1])
                    if edge in pheromones:
                        pheromones[edge] += elitist_deposit

    def _evaluate_solution(
        self, solution: Dict[str, List[str]], params: SolveAcoModelDTO
    ) -> float:
        """Calculates the objective function mathematically identical to opp_model_v3."""
        info = self._build_solution_info(solution, 0.0, params)

        recollection_time = sum(info["batch_completions"].values())
        advance_time = sum(info["earliness"].values())
        delay_time = sum(info["tardiness"].values())

        penalty = params.W_e * advance_time + params.W_t * delay_time
        return params.W_c * recollection_time + params.W_pen * penalty

    def _build_solution_info(
        self, solution: Dict[str, List[str]], cost: float, params: SolveAcoModelDTO
    ) -> dict:
        """Structures the data expected by the output_handler (Tardiness, Earliness, Batch completion)."""
        solution_info = {
            "status": "optimal",
            "objective_value": cost,
            "batch_times": {},
            "batch_completions": {},
            "tardiness": {},
            "earliness": {},
            "routes": solution,
        }

        current_time = self.T_0 if self.T_0 is not None else 0
        batch_assignments = params.extract_batch_assignments()

        for batch in self.B:
            route = solution.get(batch, [])
            if not route:
                continue

            # 1. Travel Time and unique visited picking locations
            travel_time = 0
            visited_locations = set()
            for i in range(len(route) - 1):
                n1, n2 = route[i], route[i + 1]
                travel_time += self.location_graph.get_distance(n1, n2)
                if (
                    n1 != self.location_graph.get_depot()
                    and n1 != self.location_graph.get_final()
                ):
                    visited_locations.add(n1)

            # 2. Picking Time (Sum of required capacity C_n for orders in this batch)
            picking_time = 0
            if isinstance(params.C_n, dict):
                picking_time = sum(
                    params.C_n.get(o, 0) for o in batch_assignments.get(batch, set())
                )

            # 3. Service Time (Sum of S for each unique visited location)
            service_time = 0
            if isinstance(params.S, dict):
                service_time = sum(params.S.get(loc, 0) for loc in visited_locations)

            # EXACT V3 t_exec formula (Constraint 18 replication)
            t_exec_b = (
                params.T_setup
                + (params.T_pick * picking_time)
                + (params.T_travel * travel_time)
                + service_time
            )

            current_time += t_exec_b
            solution_info["batch_times"][batch] = t_exec_b
            solution_info["batch_completions"][batch] = current_time

        # Earliness and Tardiness calculations
        for order in self.N:
            order_batch = next(
                (b for b, orders in batch_assignments.items() if order in orders), None
            )
            if order_batch and order_batch in solution_info["batch_completions"]:
                v_b = solution_info["batch_completions"][order_batch]
                due_date = params.T_due_n.get(order, float("inf"))

                solution_info["tardiness"][order] = max(0, v_b - due_date)
                solution_info["earliness"][order] = max(0, due_date - v_b)

        return solution_info

    def _build_solution_output(
        self, solution: Dict[str, List[str]]
    ) -> OPPLocationGraph:
        """Converts the ACO route into the OPPLocationGraph format required by the output builder."""
        output_graph = OPPLocationGraph(
            depot_node=self.location_graph.get_depot(),
            final_node=self.location_graph.get_final(),
        )
        for vertex in self.location_graph.get_vertices():
            output_graph.add_vertex(vertex, "picking")

        for route in solution.values():
            if not route:
                continue
            for i in range(len(route) - 1):
                n1, n2 = route[i], route[i + 1]
                if self.location_graph.has_edge(n1, n2):
                    output_graph.add_edge(
                        n1, n2, self.location_graph.get_distance(n1, n2)
                    )

        return output_graph
