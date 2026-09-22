"""
Hill Climbing heuristic for OPP v3 with ALL constraints validation.

Same problem as opp_model_v3.py:
- Receives: same SolveModelDTO parameters
- Validates: ALL constraints from the exact model
- Optimizes: routes within batches using 2-opt
- Output: compatible with build_output
"""

import time
import random
from collections import deque
from typing import Dict, List, Set, Optional

from dtos.hc.solve_hc_model_dto import SolveHCModelDTO
from dtos.opp.solve_result import SolveResult
import models.utils.solve_registry as solve_registry
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_hc_1.utils.route_solution import RouteSolution
from models.opp_hc_1.utils.route_evaluator import RouteEvaluator
from models.opp_hc_1.utils.constraints_validator import ConstraintsValidator


class OPPHillClimbing(Model):
    """Hill Climbing solver for OPP v3 - validates ALL constraints."""

    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time

    def solve(self, params: SolveHCModelDTO):
        """
        Solve OPP v3 using Hill Climbing on routes with full constraint validation.

        Receives: Same parameters as opp_model_v3
        Validates: All constraints
        Returns: Compatible output
        """
        start_time = self.T_0 if self.T_0 is not None else time.time()

        # Guard: Bn=None means no batch assignments were provided
        if params.Bn is None:
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        # Check for orders assigned to more than one batch (violates sum_b y_nb = 1)
        # Check vehicle capacity constraint per batch before doing any work
        if not (params.is_capacity_valid() and params.is_batch_assignment_valid()):
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        # Extract batch assignments from Bn parameter
        batch_assignments = params.extract_batch_assignments()

        # Create validator
        validator = ConstraintsValidator(
            N=self.N,
            B=self.B,
            location_graph=self.location_graph,
            batch_assignments=batch_assignments,
            C_n=params.C_n,
            C_v=params.C_v,
            A=params.A,
        )

        # Create evaluator
        evaluator = RouteEvaluator(
            N=self.N,
            B=self.B,
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

        max_iterations = params.Max_it
        max_no_improvement = params.Max_imp

        # Generate initial FEASIBLE solution
        current_solution = self._generate_initial_feasible_solution(
            batch_assignments, validator, params.C_n, params.A
        )

        if current_solution is None:
            print("ERROR: Could not generate initial feasible solution")
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

        current_cost = evaluator.evaluate(current_solution)

        iteration = 0
        no_improvement_count = 0

        # Hill climbing main loop
        while iteration < max_iterations and no_improvement_count < max_no_improvement:
            iteration += 1

            # Generate neighbor (maintaining feasibility)
            neighbor_solution = self._generate_feasible_neighbor(
                current_solution, batch_assignments, validator, params.C_n, params.A
            )

            if neighbor_solution is None:
                no_improvement_count += 1
                continue

            neighbor_cost = evaluator.evaluate(neighbor_solution)

            # Accept if better
            if neighbor_cost < current_cost:
                current_solution = neighbor_solution
                current_cost = neighbor_cost
                no_improvement_count = 0
            else:
                no_improvement_count += 1

        elapsed = time.time() - start_time

        print(f"\nHill Climbing execution time: {elapsed:.4f}s")
        print(f"Final objective value: {current_cost:.4f}")
        print(f"Iterations: {iteration}")

        # Build output compatible with build_output format
        output = self._build_solution_output(current_solution)

        # Notify observers with solution information
        solution_info = self._build_solution_info(current_solution, current_cost, params)
        super().notify(solution_info=solution_info)

        solve_result = SolveResult(
            status="optimal",
            output=output,
            elapsed=elapsed,
            params={
                "obj_val": current_cost,
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
                "V": len(self.location_graph.get_vertices()),
                "Max_it": params.Max_it,
                "Max_imp": params.Max_imp,
            },
        )
        solve_registry.register(solve_result)
        return solve_result

    def _register_infeasible(self, params: SolveHCModelDTO, elapsed: float) -> None:
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
                "V": len(self.location_graph.get_vertices()),
                "Max_it": getattr(params, "Max_it", None),
                "Max_imp": getattr(params, "Max_imp", None),
            },
        ))

    def _generate_initial_feasible_solution(
        self,
        batch_assignments: Dict[str, Set[str]],
        validator: "ConstraintsValidator",
        C_n: Dict,
        A: Dict,
    ) -> Optional[RouteSolution]:
        """
        Generate initial FEASIBLE solution respecting ALL constraints.
        Returns None if any batch with required locations cannot be routed
        """
        solution = RouteSolution(self.B, self.location_graph, batch_assignments)

        # Build a route for every batch that has picking requirements
        for batch in self.B:
            if not batch_assignments[batch]:
                continue

            required_locations = self._find_required_locations(batch, batch_assignments[batch], A)

            if not required_locations:
                continue

            route = self._generate_feasible_route_bff(required_locations)

            if route is None:
                # Graph is disconnected or required locations are unreachable
                print(f"WARNING: Could not generate feasible route for batch {batch}")
                return None

            solution.set_batch_route(batch, route)

        # Validate the complete solution once all routes are in place
        if not validator.validate_solution(solution):
            return None

        return solution

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

    def _generate_feasible_route(self, required_locations: Set) -> Optional[List]:
        """
        Generate a feasible route visiting all required locations.
        Uses nearest neighbor starting from depot.
        Constraints:
        - Start at depot
        - End at final
        - Visit all required locations
        - Use only valid edges
        - No cycles
        """
        if not required_locations:
            return []

        route = []
        current = self.location_graph.get_depot()
        remaining = set(required_locations)

        while remaining:
            # Find nearest unvisited location with valid edge
            nearest = None
            min_distance = float('inf')

            for loc in remaining:
                if self.location_graph.has_edge(current, loc):
                    distance = self.location_graph.get_distance(current, loc)
                    if distance < min_distance:
                        nearest = loc
                        min_distance = distance

            if nearest is None:
                # No valid edge to remaining locations - try any remaining
                for loc in remaining:
                    if self.location_graph.has_edge(current, loc):
                        nearest = loc
                        break

            if nearest is None:
                # Cannot reach remaining locations
                return None

            route.append(nearest)
            remaining.remove(nearest)
            current = nearest

        # Verify route can reach final node
        if not self.location_graph.has_edge(current, self.location_graph.get_final()):
            return None

        return route

    def _generate_feasible_route_bff(self, required_locations: Set) -> Optional[List]:
        """
        Generate a feasible route visiting all required locations.

        Uses BFS over states (current_node, frozenset(remaining_required)) to
        find the shortest path from depot through all required locations
        to final, without using final as an intermediate stop.

        Intermediate nodes are included so the returned list represents the
        full physical traversal (excluding depot and final).  Returns None
        when no valid path exists.
        """
        if not required_locations:
            return []

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        vertices = self.location_graph.get_vertices()

        initial_remaining = frozenset(required_locations)
        # Each queue entry: (current_node, remaining_required, path_so_far)
        queue: deque = deque([(depot, initial_remaining, [depot])])
        seen: Set = {(depot, initial_remaining)}

        while queue:
            node, remaining, path = queue.popleft()
            visited = set(path)

            for vertex in vertices:  # sorted → deterministic exploration
                if vertex in visited or not self.location_graph.has_edge(node, vertex):
                    continue

                if vertex == final:
                    if not remaining:
                        # path[1:] = intermediate nodes after depot (final not in path)
                        return path[1:]
                    continue

                new_remaining = remaining - {vertex}
                new_state = (vertex, new_remaining)
                if new_state not in seen:
                    seen.add(new_state)
                    queue.append((vertex, new_remaining, path + [vertex]))

        return None  # No feasible path exists


    def _generate_feasible_neighbor(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        validator: "ConstraintsValidator",
        C_n: Dict,
        A: Dict,
    ) -> Optional[RouteSolution]:
        """
        Generate a neighbor by applying 2-opt ONLY if it maintains feasibility.
        """
        neighbor = solution.copy()

        # Select random batch with non-empty route
        batches_with_routes = [b for b in self.B if neighbor.get_batch_route(b)]

        if not batches_with_routes:
            return None

        batch = random.choice(batches_with_routes)
        route = neighbor.get_batch_route(batch)

        if len(route) <= 1:
            return None

        # Try 2-opt swaps (limited attempts)
        for attempt in range(10):
            i = random.randint(0, len(route) - 2)
            j = random.randint(i + 1, len(route) - 1)

            # Apply 2-opt: reverse segment
            new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]

            # Verify new route is feasible
            if self._is_route_feasible(new_route, batch, batch_assignments, A):
                neighbor.set_batch_route(batch, new_route)
                return neighbor

        return None

    def _is_route_feasible(
        self, route: List, batch: str, batch_assignments: Dict[str, Set[str]], A: Dict
    ) -> bool:
        """
        Check if a route is feasible:
        - Starts at depot
        - Ends at final
        - Visits all required locations
        - Uses only valid edges
        - No repeated nodes
        """
        if not route:
            return True

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        # No repeated nodes
        if len(route) != len(set(route)):
            return False

        # Check all edges are valid
        if not self.location_graph.has_edge(depot, route[0]):
            return False

        for i in range(len(route) - 1):
            if not self.location_graph.has_edge(route[i], route[i+1]):
                return False

        if not self.location_graph.has_edge(route[-1], final):
            return False

        # Check all required locations are visited
        required = self._find_required_locations(batch, batch_assignments[batch], A)
        if not required.issubset(set(route)):
            return False

        return True

    def _build_solution_output(self, solution: RouteSolution) -> OPPLocationGraph:
        """
        Convert RouteSolution to OPPLocationGraph format compatible with build_output.
        """
        output_graph = OPPLocationGraph(
            depot_node=self.location_graph.get_depot(),
            final_node=self.location_graph.get_final()
        )

        # Add all vertices
        for vertex in self.location_graph.get_vertices():
            output_graph.add_vertex(vertex, "picking")

        # Add arcs from routes
        for batch in self.B:
            route = solution.get_batch_route(batch)
            if not route:
                continue

            depot = self.location_graph.get_depot()
            final = self.location_graph.get_final()

            # Add depot -> first location
            if self.location_graph.has_edge(depot, route[0]):
                output_graph.add_edge(
                    depot, route[0],
                    self.location_graph.get_distance(depot, route[0])
                )

            # Add edges between locations in route
            for i in range(len(route) - 1):
                if self.location_graph.has_edge(route[i], route[i+1]):
                    output_graph.add_edge(
                        route[i], route[i+1],
                        self.location_graph.get_distance(route[i], route[i+1])
                    )

            # Add last location -> final
            if self.location_graph.has_edge(route[-1], final):
                output_graph.add_edge(
                    route[-1], final,
                    self.location_graph.get_distance(route[-1], final)
                )

        return output_graph

    def _build_solution_info(self, solution: RouteSolution, objective_value: float, params: SolveModelDTO) -> dict:
        """
        Build solution information dictionary for OutputHandler.
        Compatible with the format expected by opp_hc_1 OutputHandler.
        """
        solution_info = {
            "status": "optimal",
            "objective_value": objective_value,
            "batch_times": {},
            "batch_completions": {},
            "tardiness": {},
            "earliness": {},
            "routes": {}
        }

        # Calculate times for each batch
        current_time = self.T_0 if self.T_0 is not None else 0

        for batch in self.B:
            route = solution.get_batch_route(batch)
            if not route:
                continue

            # Calculate execution time for this batch
            t_exec_b = self._calculate_batch_execution_time(batch, route, params)
            current_time += t_exec_b

            solution_info["batch_times"][batch] = t_exec_b
            solution_info["batch_completions"][batch] = current_time
            solution_info["routes"][batch] = route

        # Calculate tardiness and earliness for each order
        batch_assignments = params.extract_batch_assignments()
        for order in self.N:
            # Find which batch this order belongs to
            order_batch = None
            for batch, orders in batch_assignments.items():
                if order in orders:
                    order_batch = batch
                    break

            if order_batch is not None and order_batch in solution_info["batch_completions"]:
                completion_time = solution_info["batch_completions"][order_batch]
                due_date = params.Dd.get(order, float('inf'))

                if completion_time > due_date:
                    solution_info["tardiness"][order] = completion_time - due_date
                    solution_info["earliness"][order] = 0
                else:
                    solution_info["tardiness"][order] = 0
                    solution_info["earliness"][order] = due_date - completion_time

        return solution_info

    def _calculate_batch_execution_time(self, batch: str, route: List, params: SolveModelDTO) -> float:
        """Calculate execution time for a batch given its route."""
        if not route:
            return 0

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        # Travel time
        travel_time = 0
        current = depot
        for location in route:
            if self.location_graph.has_edge(current, location):
                travel_time += self.location_graph.get_distance(current, location)
            current = location
        if self.location_graph.has_edge(current, final):
            travel_time += self.location_graph.get_distance(current, final)

        # Setup time
        setup_time = params.B_setup

        # Picking time (sum of service times for orders in this batch)
        picking_time = 0
        batch_assignments = params.extract_batch_assignments()
        for order in batch_assignments.get(batch, set()):
            picking_time += params.S.get(order, 0) if isinstance(params.S, dict) else 0

        # Capacity weight (from objective function)
        capacity_weight = params.B_picking

        total_time = params.B_time * travel_time + setup_time + capacity_weight * picking_time
        return total_time
