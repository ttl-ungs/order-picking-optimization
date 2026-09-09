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
counterpart of opp_v5's stage2_scheduling.zpl additions over opp_v4:

- Picker speed (V_p): a batch's execution time is no longer a single
  t_exec_b fixed for every picker. Instead t_exec_pb[p, b] = fixed_time(b)
  + route_time(b) / V_p[p], where fixed_time (setup + picking) doesn't
  depend on speed and route_time (travel + service) does. Faster pickers
  finish the same route sooner.
- Cold chain (T_frio_max): a (picker, batch) pair is only eligible if
  t_exec_pb[p, b] <= T_frio_max. This restricts WHICH picker a batch can be
  assigned to (X_pb's domain), exactly like stage2_scheduling.zpl restricts
  X_pb to PB_elig, rather than adding it as a separate penalized cost. A
  batch left with zero eligible pickers makes the instance infeasible,
  short-circuited up front the same way opp_v5's solve pipeline does (see
  models/opp_v5/utils/cold_chain_validation.py::batches_without_eligible_picker,
  reused here directly instead of re-implementing the same check).

Deliberately WITHOUT congestion between concurrent pickers (unlike
opp_hc_3): congestion and picker-speed/cold-chain are orthogonal additions
over opp_hc_2, and this model only needs the latter. Adding congestion on
top would require re-pricing t_exec_pb's route/service time against other
pickers' reservations (models/utils/congestion.py::CongestionTracker) every
time a batch's route OR its assigned picker's speed changes - left out here
to keep the search space (and what's being measured) focused on the
speed/cold-chain trade-off, matching opp_v5 itself, which also has no
congestion (see analysis/config.py).
"""

import time
import random
import heapq
from collections import deque
from typing import Dict, List, Set, Optional, Tuple

from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO
from dtos.opp.solve_result import SolveResult
import models.utils.solve_registry as solve_registry
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO
from models.opp_hc_2.utils.route_solution import RouteSolution
from models.opp_hc_4.utils.route_evaluator import RouteEvaluator
from models.opp_hc_4.utils.constraints_validator import ConstraintsValidator
from models.opp_v5.utils.cold_chain_validation import batches_without_eligible_picker


class OPPHillClimbing(Model):
    """Hill Climbing solver for OPP v4 - picker speed + cold chain, no congestion."""

    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time
        self.P = sorted(dto.P) if getattr(dto, "P", None) else ["P1"]

    def solve(self, params: SolveHC4ModelDTO):
        """
        Solve OPP v4 using Hill Climbing on routes with full constraint
        validation, picker speed and cold chain eligibility.
        """
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

        max_iterations = params.Max_it
        max_no_improvement = params.Max_imp

        current_solution, stuck_batches = self._generate_initial_feasible_solution(
            batch_assignments, validator, params
        )

        if stuck_batches:
            print(
                "ERROR: No picker satisfies the cold-chain deadline for "
                f"batches {sorted(stuck_batches)}"
            )
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

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
                current_solution, batch_assignments, validator, params
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

        print(f"\nHill Climbing execution time: {elapsed:.4f}s")
        print(f"Final objective value: {current_cost:.4f}")
        print(f"Iterations: {iteration}" + (" (stopped: time budget exceeded)" if timed_out else ""))

        output = self._build_solution_output(current_solution)

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
                "V_p": dict(params.V_p),
                "T_frio_max": params.T_frio_max,
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

    def _register_infeasible(self, params: SolveHC4ModelDTO, elapsed: float) -> None:
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
                "V": len(self.location_graph.get_vertices()),
                "Max_it": getattr(params, "Max_it", None),
                "Max_imp": getattr(params, "Max_imp", None),
            },
        ))

    def _picker_speed(self, picker: str, params: SolveHC4ModelDTO) -> float:
        return (params.V_p or {}).get(picker, 1.0)

    def _picker_speeds(self, params: SolveHC4ModelDTO) -> Dict[str, float]:
        return {p: self._picker_speed(p, params) for p in self.P}

    def _fixed_time(self, batch: str, batch_assignments: Dict[str, Set[str]], params: SolveHC4ModelDTO) -> float:
        """Setup + picking time -- the part of t_exec_pb that does NOT depend on picker speed."""
        orders = batch_assignments.get(batch, set())
        picking_capacity = sum(params.C_n.get(o, 0) for o in orders) if isinstance(params.C_n, dict) else 0
        return params.B_setup + params.B_picking * picking_capacity

    def _route_time(self, route: List, params: SolveHC4ModelDTO) -> float:
        """Travel time (B_time * distance) + service time -- opp_v5's R_b_time, the part scaled by V_p."""
        if not route:
            return 0.0

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        distance = self.location_graph.get_distance(depot, route[0])
        for i in range(len(route) - 1):
            distance += self.location_graph.get_distance(route[i], route[i + 1])
        distance += self.location_graph.get_distance(route[-1], final)

        service_time = sum(params.S.get(loc, 0) for loc in route) if isinstance(params.S, dict) else 0

        return params.B_time * distance + service_time

    def _t_exec_pb(
        self, batch: str, route: List, picker: str,
        batch_assignments: Dict[str, Set[str]], params: SolveHC4ModelDTO,
    ) -> float:
        fixed_time = self._fixed_time(batch, batch_assignments, params)
        speed = self._picker_speed(picker, params)
        return fixed_time + self._route_time(route, params) / speed

    def _eligible_pickers_for_batch(
        self, batch: str, route: List, batch_assignments: Dict[str, Set[str]], params: SolveHC4ModelDTO,
    ) -> List[str]:
        """Pickers p for which t_exec_pb[p, batch] <= T_frio_max, given `route`."""
        return [
            p for p in self.P
            if self._t_exec_pb(batch, route, p, batch_assignments, params) <= params.T_frio_max + 1e-9
        ]

    def _generate_initial_feasible_solution(
        self,
        batch_assignments: Dict[str, Set[str]],
        validator: "ConstraintsValidator",
        params: SolveHC4ModelDTO,
    ) -> Tuple[Optional[RouteSolution], Optional[Set[str]]]:
        """
        Generate initial FEASIBLE solution respecting ALL constraints,
        picker speed and cold chain.
        Returns (None, None) if any batch with required locations cannot be
        routed at all, or (None, stuck_batches) if every batch got a route
        but at least one has zero picker eligible under the cold-chain
        deadline (mirrors opp_v5's PB_elig/B_sin_picker_elegible short-circuit).
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

            route = self._generate_feasible_route(required_locations)
            if route is None:
                route = self._generate_feasible_route_bff(required_locations)

            if route is None:
                print(f"WARNING: Could not generate feasible route for batch {batch}")
                return None, None

            solution.set_batch_route(batch, route)
            route_time[batch] = self._route_time(route, params)

        # Cold-chain pre-check: a batch with zero eligible picker can never
        # be assigned, so bail out before running Hill Climbing on it (same
        # short-circuit opp_v5's solve pipeline applies before invoking ZIMPL).
        stuck_batches = batches_without_eligible_picker(
            self.P, self.B, self.N, params.C_n, params.Bn,
            params.B_setup, params.B_picking, route_time,
            self._picker_speeds(params), params.T_frio_max,
        )
        if stuck_batches:
            return None, stuck_batches

        self._assign_batches_to_pickers(solution, batch_assignments, route_time, params)

        if not validator.validate_solution(solution):
            return None, None

        return solution, None

    def _assign_batches_to_pickers(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        route_time: Dict[str, float],
        params: SolveHC4ModelDTO,
    ) -> None:
        """
        Distribute batches with orders across their COLD-CHAIN-ELIGIBLE
        pickers, greedily balancing load (assign each batch to whichever of
        its eligible pickers currently has the fewest batches).
        """
        load = {p: 0 for p in self.P}
        batches_to_assign = [b for b in self.B if batch_assignments[b]]
        for batch in batches_to_assign:
            eligible = self._eligible_pickers_for_batch(
                batch, solution.get_batch_route(batch), batch_assignments, params
            )
            # Guaranteed non-empty: batches_without_eligible_picker already
            # ruled out any batch with an empty eligible set before this runs.
            picker = min(eligible, key=lambda p: (load[p], self.P.index(p)))
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
        """Shortest-path distances/predecessors from `source` (see opp_hc_2's twin method)."""
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
        """Dijkstra-based nearest-neighbor route construction (see opp_hc_2's twin method)."""
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

    _MAX_BFF_EXPANSIONS = 200_000

    def _generate_feasible_route_bff(self, required_locations: Set) -> Optional[List]:
        """Last-resort exhaustive route search (see opp_hc_2's twin method's docstring)."""
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
        """BFS over states (current_node, remaining_required, path_so_far)."""
        queue: deque = deque([(depot, initial_remaining, [depot])])
        seen: Set = {(depot, initial_remaining)} if memoize else None
        expansions = 0

        while queue:
            if not memoize:
                expansions += 1
                if expansions > self._MAX_BFF_EXPANSIONS:
                    return None

            node, remaining, path = queue.popleft()
            visited = set(path)

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

        return None

    def _generate_feasible_neighbor(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        validator: "ConstraintsValidator",
        params: SolveHC4ModelDTO,
    ) -> Optional[RouteSolution]:
        """
        Generate a neighbor via one of three feasibility-preserving moves:
        - 2-opt on a batch's route (must keep the assigned picker cold-chain-eligible)
        - Reassign a batch to a different (cold-chain-eligible) picker
        - Swap the processing order of two batches on the same picker
        """
        batches_with_orders = [b for b in self.B if batch_assignments[b]]

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
        params: SolveHC4ModelDTO,
    ) -> Optional[RouteSolution]:
        """
        Full 2-opt on a randomly selected batch's route: only reversals that
        stay topologically feasible AND keep the batch's current picker
        cold-chain-eligible are considered; keeps the single best
        (steepest-descent) improving one.
        """
        batches_with_routes = [b for b in self.B if solution.get_batch_route(b)]
        if not batches_with_routes:
            return None

        batch = random.choice(batches_with_routes)
        route = solution.get_batch_route(batch)
        picker = solution.get_batch_picker(batch)

        if len(route) <= 1:
            return None

        best_route = None
        best_distance = self._calculate_route_distance(route)

        for i in range(len(route) - 1):
            for j in range(i + 1, len(route)):
                new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]

                if not self._is_route_feasible(new_route, batch, batch_assignments, params.A):
                    continue

                if picker is not None and self._t_exec_pb(
                    batch, new_route, picker, batch_assignments, params
                ) > params.T_frio_max + 1e-9:
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
        params: SolveHC4ModelDTO,
    ) -> Optional[RouteSolution]:
        """Move a random batch to a different COLD-CHAIN-ELIGIBLE picker, route untouched."""
        batches_with_orders = [b for b in self.B if batch_assignments[b]]
        if not batches_with_orders:
            return None

        batch = random.choice(batches_with_orders)
        current_picker = solution.get_batch_picker(batch)
        route = solution.get_batch_route(batch)
        eligible = self._eligible_pickers_for_batch(batch, route, batch_assignments, params)
        other_pickers = [p for p in eligible if p != current_picker]
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
        params: SolveHC4ModelDTO,
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

    def _is_route_feasible(
        self, route: List, batch: str, batch_assignments: Dict[str, Set[str]], A: Dict
    ) -> bool:
        """Topology-only feasibility check (cold chain is checked separately by callers)."""
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

    def _build_solution_info(self, solution: RouteSolution, objective_value: float, params: SolveHC4ModelDTO) -> dict:
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
            "T_frio_max": params.T_frio_max,
        }

        base_time = self.T_0 if self.T_0 is not None else 0

        for picker in self.P:
            current_time = base_time
            for batch in solution.get_picker_sequence(picker):
                route = solution.get_batch_route(batch)

                t_exec_pb = self._calculate_batch_execution_time(batch, route, picker, params)
                current_time += t_exec_pb

                solution_info["batch_times"][batch] = t_exec_pb
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
                due_date = params.Dd.get(order, float('inf'))

                if completion_time > due_date:
                    solution_info["tardiness"][order] = completion_time - due_date
                    solution_info["earliness"][order] = 0
                else:
                    solution_info["tardiness"][order] = 0
                    solution_info["earliness"][order] = due_date - completion_time

        return solution_info

    def _calculate_batch_execution_time(
        self, batch: str, route: List, picker: str, params: SolveHC4ModelDTO
    ) -> float:
        """
        t_exec_pb = B_setup + B_picking * sum(C_n)          [fixed, no speed]
                  + (B_time * travel_distance + service_time) / V_p[picker]
        (same formula as RouteEvaluator._calculate_batch_execution_time --
        kept here too since this copy also drives the reported
        batch_times/batch_completions/tardiness/earliness, same split
        opp_hc_2/opp_hc_3 use between the search's evaluator and this
        reporting-only helper).
        """
        return self._t_exec_pb(batch, route, picker, params.extract_batch_assignments(), params)
