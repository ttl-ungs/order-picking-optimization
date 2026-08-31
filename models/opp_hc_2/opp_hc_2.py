"""
Hill Climbing heuristic for OPP v4 with ALL constraints validation.

Same problem as opp_model_v4.zpl:
- Receives: same SolveModelDTO parameters, plus a set of pickers (P)
- Validates: ALL constraints from the exact model
- Optimizes: routes within batches (2-opt) AND the assignment/sequencing of
  batches to pickers, so that batches on different pickers run in parallel
  and batches on the same picker are sequenced without overlap
- Output: compatible with build_output
"""

import time
import random
import heapq
from collections import deque
from typing import Dict, List, Set, Optional, Tuple

from dtos.hc.solve_hc_model_dto import SolveHCModelDTO
from dtos.opp.solve_result import SolveResult
import models.utils.solve_registry as solve_registry
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_hc_2.utils.route_solution import RouteSolution
from models.opp_hc_2.utils.route_evaluator import RouteEvaluator
from models.opp_hc_2.utils.constraints_validator import ConstraintsValidator


class OPPHillClimbing(Model):
    """Hill Climbing solver for OPP v4 - validates ALL constraints, parallelizes over pickers."""

    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time
        # P: pickers. Falls back to a single implicit picker for callers that
        # don't provide one (equivalent to the old, non-parallel behaviour).
        self.P = sorted(dto.P) if getattr(dto, "P", None) else ["P1"]

    def solve(self, params: SolveHCModelDTO):
        """
        Solve OPP v4 using Hill Climbing on routes with full constraint validation.

        Receives: Same parameters as opp_model_v4
        Validates: All constraints
        Returns: Compatible output
        """
        # Optional reproducibility (2026-08-28 audit finding): seeds the
        # shared global `random` module state used throughout this file's
        # neighbor-move selection. Default None (params.Seed unset) leaves
        # global random state untouched, preserving prior behavior exactly.
        if params.Seed is not None:
            random.seed(params.Seed)

        # Real wall-clock reference for timing/timeout purposes. This is
        # intentionally separate from `self.T_0`, which is a domain value
        # (the picking schedule's start time) used only to offset reported
        # batch completion times, and may not be an actual timestamp.
        wall_clock_start = time.time()

        # Guard: Bn=None means no batch assignments were provided
        if params.Bn is None:
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        # Check for orders assigned to more than one batch (violates sum_b y_nb = 1)
        # Check vehicle capacity constraint per batch before doing any work
        if not (params.is_capacity_valid() and params.is_batch_assignment_valid()):
            self._register_infeasible(params, time.time() - wall_clock_start)
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
            P=self.P,
        )

        # Create evaluator
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

        max_iterations = params.Max_it
        max_no_improvement = params.Max_imp

        # Generate initial FEASIBLE solution
        current_solution = self._generate_initial_feasible_solution(
            batch_assignments, validator, params.C_n, params.A
        )

        if current_solution is None:
            print("ERROR: Could not generate initial feasible solution")
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        current_cost = evaluator.evaluate(current_solution)

        max_time = params.Max_time if getattr(params, "Max_time", None) else 30.0

        iteration = 0
        no_improvement_count = 0
        timed_out = False

        # Hill climbing main loop, capped by iterations, stagnation, AND a
        # wall-clock budget so a single solve() call can't run indefinitely.
        while iteration < max_iterations and no_improvement_count < max_no_improvement:
            if time.time() - wall_clock_start > max_time:
                timed_out = True
                break

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

        elapsed = time.time() - wall_clock_start

        print(f"\nHill Climbing execution time: {elapsed:.4f}s")
        print(f"Final objective value: {current_cost:.4f}")
        print(f"Iterations: {iteration}" + (" (stopped: time budget exceeded)" if timed_out else ""))

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
                "P": len(self.P),
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
        solution = RouteSolution(self.B, self.location_graph, batch_assignments, self.P)

        # Build a route for every batch that has picking requirements
        for batch in self.B:
            if not batch_assignments[batch]:
                continue

            required_locations = self._find_required_locations(batch, batch_assignments[batch], A)

            if not required_locations:
                continue

            # Fast path: Dijkstra-based nearest neighbor. Fall back to the
            # exhaustive state-space search only if the greedy construction
            # couldn't complete a route (keeps the completeness guarantee).
            route = self._generate_feasible_route(required_locations)
            if route is None:
                route = self._generate_feasible_route_bff(required_locations)

            if route is None:
                # Graph is disconnected or required locations are unreachable
                print(f"WARNING: Could not generate feasible route for batch {batch}")
                return None

            solution.set_batch_route(batch, route)

        # Assign every batch with orders to a picker (X_pb), distributing the
        # batches round-robin across pickers so work is parallelized. Hill
        # climbing later explores reassignments/reorderings to improve on this.
        self._assign_batches_to_pickers(solution, batch_assignments)

        # Validate the complete solution once all routes are in place
        if not validator.validate_solution(solution):
            return None

        return solution

    def _assign_batches_to_pickers(
        self, solution: RouteSolution, batch_assignments: Dict[str, Set[str]]
    ) -> None:
        """Distribute batches with orders across pickers round-robin (X_pb)."""
        batches_to_assign = [b for b in self.B if batch_assignments[b]]
        for index, batch in enumerate(batches_to_assign):
            picker = self.P[index % len(self.P)]
            solution.assign_batch_to_picker(batch, picker)

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
        """
        Shortest-path distances/predecessors from `source` over the subgraph
        that excludes `forbidden` vertices (source itself is always allowed,
        even if present in `forbidden`). Uses get_neighbors() (adjacency
        list, O(1) amortized) instead of scanning every vertex and checking
        has_edge per candidate -- that used to make this O(V) per node
        expansion regardless of actual degree; profiling opp_aco_2 on a
        100-node stress instance found the equivalent scan responsible for
        ~82% of total runtime, so it's worth avoiding here too even though
        opp_hc_2 was already comparatively fast.
        """
        dist = {source: 0.0}
        prev: Dict = {}
        visited: Set = set()
        heap = [(0.0, source)]

        while heap:
            d, u = heapq.heappop(heap)
            if u in visited:
                continue
            visited.add(u)

            for v in self.location_graph.get_neighbors(u):
                if v == u or (v in forbidden and v != source):
                    continue
                nd = d + self.location_graph.get_distance(u, v)
                if nd < dist.get(v, float("inf")):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, v))

        return dist, prev

    def _reconstruct_path(self, prev: Dict, source, target) -> List:
        """Rebuild the path source -> target (inclusive) from a `prev` map."""
        if target == source:
            return [source]
        path = [target]
        node = target
        while node != source:
            node = prev[node]
            path.append(node)
        path.reverse()
        return path

    def _generate_feasible_route(self, required_locations: Set) -> Optional[List]:
        """
        Generate a feasible route visiting all required locations using a
        Dijkstra-based nearest-neighbor construction: at each step, move to
        the closest still-required location by real shortest-path distance
        (not just a direct edge), stitching in whatever intermediate nodes
        the shortest path passes through. Polynomial time - the fast path
        used before falling back to the exhaustive `_generate_feasible_route_bff`.

        Constraints:
        - Start at depot, end at final
        - Visit all required locations
        - Use only valid edges, no repeated nodes (simple path)
        - Never uses final as an intermediate stop
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
                return None  # No feasible simple path reaches the remaining stops

            nearest = min(reachable, key=lambda loc: dist[loc])
            path = self._reconstruct_path(prev, current, nearest)[1:]  # exclude current

            if any(node in visited for node in path):
                return None  # Defensive: shouldn't happen given `forbidden`

            visited.update(path)
            remaining.difference_update(path)
            route.extend(path)
            current = nearest

        # Route from the last stop to final, possibly through optional nodes
        dist, prev = self._dijkstra(current, forbidden=visited - {current})
        if final not in dist:
            return None

        path_to_final = self._reconstruct_path(prev, current, final)[1:-1]
        if any(node in visited for node in path_to_final):
            return None
        route.extend(path_to_final)

        return route

    # Safety valve for the unmemoized last-resort search in
    # _generate_feasible_route_bff -- see that method's docstring.
    _MAX_BFF_EXPANSIONS = 200_000

    def _generate_feasible_route_bff(self, required_locations: Set) -> Optional[List]:
        """
        Generate a feasible route visiting all required locations.

        Two-tier search:
        1. Memoized BFS -- fast (bounded by O(V * 2^|required|) states via
           the (node, remaining_required) cache), but can have false
           negatives: pruning a state just because some OTHER path already
           reached it can discard the only path that could actually finish,
           since completability also depends on which non-required nodes
           got "spent" along the way, not just (node, remaining) (found
           2026-08-27, repro: depot D, required {A,B}, edges D-P, D-Q, P-A,
           Q-A, P-B, B-final -- the discarded branch via D-Q-A was the only
           one that could still reach B through P).
        2. Only if (1) returns None: an unmemoized BFS (no cross-path
           pruning at all) as a genuine last resort, bounded by
           _MAX_BFF_EXPANSIONS -- correct (can't discard a working path) but
           worst-case exponential, so only worth trying once the cheap tier
           already failed.

        Tier 1 alone regressed real stress instances when tier 2's
        unmemoized search replaced it outright (2026-08-28): removing all
        pruning made the search blow up before finding a completion on
        graphs with more than a handful of required locations, turning
        previously-solvable stress cases into false negatives -- the
        opposite failure mode. Layering tier 2 behind tier 1 keeps tier 1's
        speed for everything it already solved, and only pays tier 2's cost
        on the rarer case tier 1 gets wrong.

        Intermediate nodes are included so the returned list represents the
        full physical traversal (excluding depot and final). Returns None
        when no valid path exists (or none was found within tier 2's
        expansion budget).
        """
        if not required_locations:
            return []

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()
        initial_remaining = frozenset(required_locations)

        route = self._bff_search(depot, final, initial_remaining, memoize=True)
        if route is None:
            route = self._bff_search(depot, final, initial_remaining, memoize=False)
        return route

    def _bff_search(
        self, depot, final, initial_remaining: frozenset, memoize: bool
    ) -> Optional[List]:
        """BFS over states (current_node, remaining_required, path_so_far).
        See _generate_feasible_route_bff's docstring for the two-tier
        rationale -- memoize=True is tier 1 (fast, cross-path state
        pruning), memoize=False is tier 2 (exhaustive, expansion-bounded)."""
        # Each queue entry: (current_node, remaining_required, path_so_far)
        queue: deque = deque([(depot, initial_remaining, [depot])])
        seen: Set = {(depot, initial_remaining)} if memoize else None
        expansions = 0

        while queue:
            if not memoize:
                expansions += 1
                if expansions > self._MAX_BFF_EXPANSIONS:
                    return None  # Search budget exhausted, not necessarily infeasible

            node, remaining, path = queue.popleft()
            visited = set(path)

            # get_neighbors() returns them sorted, same order get_vertices()
            # used to give here -> deterministic exploration, unchanged.
            for vertex in self.location_graph.get_neighbors(node):
                if vertex in visited:
                    continue

                if vertex == final:
                    if not remaining:
                        # path[1:] = intermediate nodes after depot (final not in path)
                        return path[1:]
                    continue

                new_remaining = remaining - {vertex}
                if memoize:
                    new_state = (vertex, new_remaining)
                    if new_state in seen:
                        continue
                    seen.add(new_state)
                queue.append((vertex, new_remaining, path + [vertex]))

        return None  # No feasible path exists (or within tier 2's expansion budget)


    def _generate_feasible_neighbor(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        validator: "ConstraintsValidator",
        C_n: Dict,
        A: Dict,
    ) -> Optional[RouteSolution]:
        """
        Generate a neighbor via one of three feasibility-preserving moves:
        - 2-opt on a batch's route (routing only, picker assignment untouched)
        - Reassign a batch to a different picker (X_pb), to rebalance load
        - Swap the processing order of two batches on the same picker

        The picker moves never touch routes, so they are always feasible;
        only the 2-opt move needs an explicit feasibility check.
        """
        batches_with_orders = [b for b in self.B if batch_assignments[b]]

        moves = [self._generate_route_neighbor]
        if len(self.P) > 1 and batches_with_orders:
            moves.append(self._generate_picker_reassignment_neighbor)
        if any(len(solution.get_picker_sequence(p)) > 1 for p in self.P):
            moves.append(self._generate_sequence_swap_neighbor)

        move = random.choice(moves)
        return move(solution, batch_assignments, A)

    def _generate_route_neighbor(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        A: Dict,
    ) -> Optional[RouteSolution]:
        """
        Generate a neighbor via full 2-opt on a randomly selected batch's
        route: systematically evaluate every pair of edges (every reversal
        segment), keep only feasible reversals, and return the single best
        (steepest-descent) improving one - or None if no feasible reversal
        improves on the current route distance.
        """
        batches_with_routes = [b for b in self.B if solution.get_batch_route(b)]
        if not batches_with_routes:
            return None

        batch = random.choice(batches_with_routes)
        route = solution.get_batch_route(batch)

        if len(route) <= 1:
            return None

        best_route = None
        best_distance = self._calculate_route_distance(route)

        for i in range(len(route) - 1):
            for j in range(i + 1, len(route)):
                new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]

                if not self._is_route_feasible(new_route, batch, batch_assignments, A):
                    continue

                new_distance = self._calculate_route_distance(new_route)
                if new_distance < best_distance - 1e-9:
                    best_distance = new_distance
                    best_route = new_route

        if best_route is None:
            return None

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
        A: Dict,
    ) -> Optional[RouteSolution]:
        """Move a random batch to a different picker (X_pb), routes untouched."""
        batches_with_orders = [b for b in self.B if batch_assignments[b]]
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
        A: Dict,
    ) -> Optional[RouteSolution]:
        """Swap the processing order of two batches assigned to the same picker."""
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
        Compatible with the format expected by opp_hc OutputHandler.
        """
        solution_info = {
            "status": "optimal",
            "objective_value": objective_value,
            "batch_times": {},
            "batch_completions": {},
            "picker_assignments": {},
            "tardiness": {},
            "earliness": {},
            "routes": {}
        }

        # Each picker processes its assigned batches sequentially, starting
        # from T_0; different pickers run in parallel.
        base_time = self.T_0 if self.T_0 is not None else 0

        for picker in self.P:
            current_time = base_time
            for batch in solution.get_picker_sequence(picker):
                route = solution.get_batch_route(batch)

                t_exec_b = self._calculate_batch_execution_time(batch, route, params)
                current_time += t_exec_b

                solution_info["batch_times"][batch] = t_exec_b
                solution_info["batch_completions"][batch] = current_time
                solution_info["picker_assignments"][batch] = picker
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
        """
        Calculate execution time for a batch given its route:
        t_exec = B_setup + B_picking * sum(C_n) + B_time * travel_distance + service_time
        (same formula as RouteEvaluator._calculate_batch_execution_time and
        opp_hc_3's own version of this method -- this used to diverge from
        it: it indexed the service-time dict `S` (keyed by LOCATION) by
        ORDER id instead, which always returned 0 since order/location ids
        are disjoint key spaces, and it dropped the real C_n-based picking
        term entirely. That only corrupted the batch_times/batch_completions/
        tardiness/earliness reported here (solution_info, printed output) --
        the actual hill-climbing search and obj_val always used
        RouteEvaluator's correct formula, so acceptance decisions and the
        reported objective were never affected).
        """
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        # Travel time (batches with no required locations don't travel at all)
        travel_time = 0
        if route:
            current = depot
            for location in route:
                if self.location_graph.has_edge(current, location):
                    travel_time += self.location_graph.get_distance(current, location)
                current = location
            if self.location_graph.has_edge(current, final):
                travel_time += self.location_graph.get_distance(current, final)

        # Setup time
        setup_time = params.B_setup

        # Picking time: B_picking * sum of C_n (vehicle-capacity units) for
        # orders in this batch.
        batch_assignments = params.extract_batch_assignments()
        orders = batch_assignments.get(batch, set())
        picking_capacity = sum(params.C_n.get(o, 0) for o in orders) if isinstance(params.C_n, dict) else 0
        picking_time = params.B_picking * picking_capacity

        # Service time: sum of service times for each location in the route.
        service_time = sum(params.S.get(loc, 0) for loc in route) if isinstance(params.S, dict) else 0

        total_time = setup_time + picking_time + params.B_time * travel_time + service_time
        return total_time
