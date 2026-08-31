"""
Hill Climbing heuristic for OPP v4 with congestion between pickers.

Same problem as opp_model_v4.zpl / opp_hc_2:
- Receives: same SolveModelDTO parameters, plus a set of pickers (P)
- Validates: ALL constraints from the exact model
- Optimizes: routes within batches (2-opt) AND the assignment/sequencing of
  batches to pickers, so that batches on different pickers run in parallel
  and batches on the same picker are sequenced without overlap
- Output: compatible with build_output

Added on top of opp_hc_2 - congestion between concurrent pickers, the
Hill Climbing counterpart of opp_aco_3's congestion mechanism, so both
metaheuristics can be compared under the same physical assumption: every
node and undirected edge is a capacity-1 resource, adapted (not literally
replicated - see models/utils/congestion.py header) from:

    Chen, F., Wang, H., Qi, C., & Xie, Y. (2013). An ant colony
    optimization routing algorithm for two order pickers with congestion
    consideration. Computers & Industrial Engineering, 66(1), 77-85.

Unlike opp_aco_3, Hill Climbing has no pheromones and already builds full,
fixed routes up front (Dijkstra-based nearest neighbor), so congestion is
not woven into route construction: it is priced as a full simulation over
the current solution every time it is evaluated (see
models/opp_hc_3/utils/route_evaluator.py). This is simpler than opp_aco_3's
incremental reservation, and sufficient here because Hill Climbing's
accept-if-better rule already rewards moves that reduce total wait, since
it is folded directly into the objective it optimizes - no separate
congestion-avoidance heuristic/pheromone is needed for a local search.
"""

import time
import random
import heapq
from collections import deque
from typing import Dict, List, Set, Optional, Tuple

from dtos.hc.solve_hc_3_model_dto import SolveHC3ModelDTO
from dtos.opp.solve_result import SolveResult
import models.utils.solve_registry as solve_registry
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.solve_model_dto import SolveModelDTO
from dtos.opp.model_dto import ModelDTO
from models.opp_hc_3.utils.route_solution import RouteSolution
from models.opp_hc_3.utils.route_evaluator import RouteEvaluator
from models.opp_hc_3.utils.constraints_validator import ConstraintsValidator


class OPPHillClimbing(Model):
    """Hill Climbing solver for OPP v4 - congestion-aware, parallelizes over pickers."""

    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time
        # P: pickers. Falls back to a single implicit picker for callers that
        # don't provide one (equivalent to the old, non-parallel behaviour).
        self.P = sorted(dto.P) if getattr(dto, "P", None) else ["P1"]

    def solve(self, params: SolveHC3ModelDTO):
        """
        Solve OPP v4 using Hill Climbing on routes with full constraint
        validation and congestion pricing between concurrent pickers.

        Receives: Same parameters as opp_model_v4, plus Min_dwell (SolveHC3ModelDTO)
        Validates: All constraints
        Returns: Compatible output
        """
        # Optional reproducibility (2026-08-28 audit finding) -- see
        # opp_hc_2.solve()'s identical comment.
        if params.Seed is not None:
            random.seed(params.Seed)

        wall_clock_start = time.time()

        if params.Bn is None:
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        if not (params.is_capacity_valid() and params.is_batch_assignment_valid()):
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        batch_assignments = params.extract_batch_assignments()

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

        min_dwell = getattr(params, "_Min_dwell", 0.0)

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
            Min_dwell=min_dwell,
        )

        max_iterations = params.Max_it
        max_no_improvement = params.Max_imp

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

        while iteration < max_iterations and no_improvement_count < max_no_improvement:
            if time.time() - wall_clock_start > max_time:
                timed_out = True
                break

            iteration += 1

            neighbor_solution = self._generate_feasible_neighbor(
                current_solution, batch_assignments, validator, params.C_n, params.A
            )

            if neighbor_solution is None:
                no_improvement_count += 1
                continue

            neighbor_cost = evaluator.evaluate(neighbor_solution)

            if neighbor_cost < current_cost:
                current_solution = neighbor_solution
                current_cost = neighbor_cost
                no_improvement_count = 0
            else:
                no_improvement_count += 1

        elapsed = time.time() - wall_clock_start

        congestion_cost = evaluator.evaluate_congestion(current_solution)

        print(f"\nHill Climbing v3 execution time: {elapsed:.4f}s")
        print(f"Final objective value: {current_cost:.4f}")
        print(f"Final congestion wait: {congestion_cost:.4f}")
        print(f"Iterations: {iteration}" + (" (stopped: time budget exceeded)" if timed_out else ""))

        output = self._build_solution_output(current_solution)

        solution_info = self._build_solution_info(current_solution, current_cost, congestion_cost, params)
        super().notify(solution_info=solution_info)

        solve_result = SolveResult(
            status="optimal",
            output=output,
            elapsed=elapsed,
            params={
                "obj_val": current_cost,
                "obj_val_congestion": congestion_cost,
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
                "Min_dwell": min_dwell,
            },
        )
        solve_registry.register(solve_result)
        return solve_result

    def _register_infeasible(self, params: SolveHC3ModelDTO, elapsed: float) -> None:
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
        Returns None if any batch with required locations cannot be routed.
        Route construction itself is congestion-agnostic (same
        Dijkstra-nearest-neighbor as opp_hc_2): congestion is priced only
        once routes/pickers/sequences are fixed, by RouteEvaluator.
        """
        solution = RouteSolution(self.B, self.location_graph, batch_assignments, self.P)

        for batch in self.B:
            if not batch_assignments[batch]:
                continue

            required_locations = self._find_required_locations(batch, batch_assignments[batch], A)

            if not required_locations:
                continue

            route = self._generate_feasible_route(required_locations)
            if route is None:
                route = self._generate_feasible_route_bff(required_locations)

            if route is None:
                print(f"WARNING: Could not generate feasible route for batch {batch}")
                return None

            solution.set_batch_route(batch, route)

        self._assign_batches_to_pickers(solution, batch_assignments)

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
        list) instead of scanning every vertex + has_edge per candidate --
        see opp_hc_2._dijkstra's docstring for the profiling that found this
        pattern responsible for ~82% of opp_aco_2's runtime on a stress
        instance.
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
        Dijkstra-based nearest-neighbor construction. Polynomial time - the
        fast path used before falling back to `_generate_feasible_route_bff`.
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

    # Same safety valve as opp_hc_2._MAX_BFF_EXPANSIONS -- see its docstring
    # there for the full explanation.
    _MAX_BFF_EXPANSIONS = 200_000

    def _generate_feasible_route_bff(self, required_locations: Set) -> Optional[List]:
        """
        Generate a feasible route visiting all required locations. Two-tier
        search, mirroring opp_hc_2's identical fix (2026-08-28) -- see its
        docstring for the full rationale: tier 1 is the fast, memoized BFS
        (can have false negatives from cross-path state pruning); tier 2,
        tried only if tier 1 fails, is an unmemoized/exhaustive BFS bounded
        by _MAX_BFF_EXPANSIONS (correct but slow -- layering it behind tier
        1 avoids regressing real stress instances the way replacing tier 1
        outright did).
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
        memoize=True is tier 1 (fast, cross-path state pruning), memoize=
        False is tier 2 (exhaustive, expansion-bounded). See
        _generate_feasible_route_bff's docstring."""
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

            # get_neighbors() returns them sorted -- same deterministic
            # exploration order get_vertices() gave here before.
            for vertex in self.location_graph.get_neighbors(node):
                if vertex in visited:
                    continue

                if vertex == final:
                    if not remaining:
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

        None of these moves is congestion-aware by itself (2-opt still picks
        the geometrically shortest reversal) - congestion is only priced
        when the resulting neighbor is evaluated, so a move that shortens a
        route but increases contention with another picker can still be
        rejected by the outer accept-if-better check in solve().
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
        route: evaluate every pair of edges (every reversal segment), keep
        only feasible reversals, and return the single best (steepest-
        descent) improving one by DISTANCE - or None if no feasible
        reversal shortens the current route.
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

        if len(route) != len(set(route)):
            return False

        if not self.location_graph.has_edge(depot, route[0]):
            return False

        for i in range(len(route) - 1):
            if not self.location_graph.has_edge(route[i], route[i+1]):
                return False

        if not self.location_graph.has_edge(route[-1], final):
            return False

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

    def _build_solution_info(
        self,
        solution: RouteSolution,
        objective_value: float,
        congestion_value: float,
        params: SolveModelDTO,
    ) -> dict:
        """
        Build solution information dictionary for OutputHandler. Compatible
        with opp_hc_2's shape, plus congestion_objective_value and
        batch_congestion_wait. Per-batch t_exec_h/completion times are
        recomputed here with the SAME formula RouteEvaluator uses (unlike
        opp_hc_2, whose reporting-only helper diverged from its evaluator's
        formula), plus the congestion wait already priced by the last
        evaluate() call on this exact solution object.
        """
        solution_info = {
            "status": "optimal",
            "objective_value": objective_value,
            "congestion_objective_value": congestion_value,
            "batch_times": {},
            "batch_completions": {},
            "batch_congestion_wait": {},
            "picker_assignments": {},
            "tardiness": {},
            "earliness": {},
            "routes": {},
        }

        batch_assignments = params.extract_batch_assignments()
        base_time = self.T_0 if self.T_0 is not None else 0

        for picker in self.P:
            current_time = base_time
            for batch in solution.get_picker_sequence(picker):
                route = solution.get_batch_route(batch)
                orders = batch_assignments.get(batch, set())

                t_exec_b = self._calculate_batch_execution_time(route, orders, params)
                t_exec_b += solution.get_batch_congestion_wait(batch)
                current_time += t_exec_b

                solution_info["batch_times"][batch] = t_exec_b
                solution_info["batch_completions"][batch] = current_time
                solution_info["batch_congestion_wait"][batch] = solution.get_batch_congestion_wait(batch)
                solution_info["picker_assignments"][batch] = picker
                solution_info["routes"][batch] = route

        for order in self.N:
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

    def _calculate_batch_execution_time(self, route: List, orders: Set[str], params: SolveModelDTO) -> float:
        """
        t_exec = B_setup + B_picking * sum(C_n) + B_time * travel_distance + service_time
        (excludes congestion wait, added separately by the caller - same
        formula as RouteEvaluator._calculate_batch_execution_time).
        """
        picking_capacity = sum(params.C_n.get(o, 0) for o in orders) if isinstance(params.C_n, dict) else 0
        picking_time = params.B_picking * picking_capacity
        travel_time = params.B_time * self._calculate_route_distance(route)
        service_time = sum(params.S.get(loc, 0) for loc in route) if isinstance(params.S, dict) else 0
        return params.B_setup + picking_time + travel_time + service_time
