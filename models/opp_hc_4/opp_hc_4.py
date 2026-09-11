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
  t_exec_pb[p, b] <= T_frio_max.

Cold chain is enforced as a HARD constraint on the reported final answer,
but a SOFT one (a large cost penalty, _search_cost/_route_local_search_
cost) during the search itself -- see models/opp_hc_4/utils/
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
from models.opp_v5.utils.cold_chain_validation import batches_without_eligible_picker, invalid_speeds


class OPPHillClimbing(Model):
    """Hill Climbing solver for OPP v4 - picker speed + cold chain, no congestion."""

    # Multiplier applied to a cold-chain overrun (a time-unit amount)
    # before adding it to a search cost -- see constraints_validator.py's
    # module docstring for why cold chain is a SOFT constraint during
    # search now (2026-09-10 audit fix). Large enough to dominate the
    # search away from violations (typical marginal objective contribution
    # per unit of recollection time is W_full, usually single-to-low-
    # double digits) without using an arbitrarily huge Big-M-style
    # constant -- this is a plain Python cost comparison, not a MIP
    # constraint, so there's no SCIP-presolve-numerics failure mode to
    # worry about the way there was with opp_v5's M_seq.
    _COLD_CHAIN_PENALTY_WEIGHT = 1000.0

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

        # V_p[p] is a divisor in _t_exec_pb (fixed_time(b) + route_time(b)
        # / V_p[p]): a speed of exactly 0 is a ZeroDivisionError waiting
        # to happen the first time any batch/picker pair gets evaluated
        # (the eligibility pre-check below, if nothing else); a negative
        # one silently produces a negative t_exec_pb that would look
        # "eligible" for any T_frio_max. Reject up front instead of
        # crashing or accepting nonsensical input (2026-09-10 audit finding).
        bad_speeds = invalid_speeds(self._picker_speeds(params))
        if bad_speeds:
            print(f"ERROR: V_p must be strictly positive for every picker; got non-positive speed for {sorted(bad_speeds)}")
            self._register_infeasible(params, time.time() - wall_clock_start)
            return "infeasible", None

        # Exact (not estimated) impossibility pre-check: fixed_time(b)
        # alone (setup + picking, independent of route/picker) already
        # tells us the BEST possible t_exec_pb for any picker, since
        # route_time is always >= 0 -- feeding batches_without_eligible_
        # picker a route_time of exactly 0.0 for every batch asks it "is
        # there a picker fast enough even for a zero-distance route?". A
        # batch flagged here is impossible under ANY route or picker, not
        # just one this run happened to construct -- unlike the estimate-
        # based pre-check this replaces (2026-09-09 audit finding). See
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
        current_cost = self._search_cost(current_solution, evaluator, validator)

        best_feasible_solution = None
        best_feasible_cost = float("inf")
        if validator.cold_chain_violation(current_solution) == 0.0:
            best_feasible_solution = current_solution.copy()
            best_feasible_cost = evaluator.evaluate(current_solution)

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

            neighbor_cost = self._search_cost(neighbor_solution, evaluator, validator)

            if neighbor_cost < current_cost:
                current_solution = neighbor_solution
                current_cost = neighbor_cost
                no_improvement_count = 0

                violation = validator.cold_chain_violation(current_solution)
                if violation == 0.0:
                    true_cost = evaluator.evaluate(current_solution)
                    if true_cost < best_feasible_cost:
                        best_feasible_solution = current_solution.copy()
                        best_feasible_cost = true_cost
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

    def _route_time(self, route: List, params: SolveHC4ModelDTO, distance: Optional[float] = None) -> float:
        """
        Travel time (B_time * distance) + service time -- opp_v5's
        R_b_time, the part scaled by V_p. Pass `distance` when the caller
        already computed it (e.g. a 2-opt candidate's distance) to avoid
        recomputing it a second time via _calculate_route_distance
        (2026-09-10 audit finding: this and _t_exec_pb used to each
        recompute the route's distance independently, doubling the work
        of every 2-opt candidate evaluation in _generate_route_neighbor).
        """
        if not route:
            return 0.0

        if distance is None:
            distance = self._calculate_route_distance(route)

        service_time = sum(params.S.get(loc, 0) for loc in route) if isinstance(params.S, dict) else 0

        return params.B_time * distance + service_time

    def _t_exec_pb(
        self, batch: str, route: List, picker: str,
        batch_assignments: Dict[str, Set[str]], params: SolveHC4ModelDTO,
        distance: Optional[float] = None,
    ) -> float:
        """See _route_time's docstring for why `distance` can be passed in precomputed."""
        fixed_time = self._fixed_time(batch, batch_assignments, params)
        speed = self._picker_speed(picker, params)
        return fixed_time + self._route_time(route, params, distance=distance) / speed

    def _eligible_pickers_for_batch(
        self, batch: str, route: List, batch_assignments: Dict[str, Set[str]], params: SolveHC4ModelDTO,
    ) -> List[str]:
        """Pickers p for which t_exec_pb[p, batch] <= T_frio_max, given `route`."""
        # Route distance doesn't depend on picker -- compute it once
        # instead of once per picker (each _t_exec_pb call would otherwise
        # recompute it independently; see _route_time's docstring).
        distance = self._calculate_route_distance(route)
        return [
            p for p in self.P
            if self._t_exec_pb(batch, route, p, batch_assignments, params, distance=distance) <= params.T_frio_max + 1e-9
        ]

    def _generate_initial_feasible_solution(
        self,
        batch_assignments: Dict[str, Set[str]],
        validator: "ConstraintsValidator",
        params: SolveHC4ModelDTO,
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

            route = self._generate_feasible_route(required_locations)
            if route is None:
                route = self._generate_feasible_route_bff(required_locations)

            if route is None:
                print(f"WARNING: Could not generate feasible route for batch {batch}")
                return None

            # Tighten with a standalone (picker/cold-chain-agnostic) 2-opt
            # pass -- gives Hill Climbing a better starting point than the
            # raw nearest-neighbor/BFS construction, regardless of cold
            # chain (cheap: one more O(n^2) pass, done once here).
            route = self._two_opt_tighten_route(route)

            solution.set_batch_route(batch, route)
            route_time[batch] = self._route_time(route, params)

        self._assign_batches_to_pickers(solution, batch_assignments, route_time, params)

        if not validator.validate_solution(solution):
            return None

        return solution

    def _assign_batches_to_pickers(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        route_time: Dict[str, float],
        params: SolveHC4ModelDTO,
    ) -> None:
        """
        Distribute batches with orders across pickers, greedily balancing
        load among each batch's COLD-CHAIN-ELIGIBLE pickers when it has
        any. A batch with NO eligible picker under its current route
        (possible now that construction no longer aborts on this -- see
        _generate_initial_feasible_solution) gets a best-effort pick: the
        picker that minimizes t_exec_pb, i.e. gets it closest to
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
                    key=lambda p: self._t_exec_pb(batch, route, p, batch_assignments, params, distance=distance),
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

    def _route_topology_feasible(self, route: List) -> bool:
        """
        Topology-only feasibility (depot/final edges + every consecutive
        edge exists) for a route that is a PERMUTATION of an already-valid
        route's nodes -- unlike _is_route_feasible, doesn't need to re-check
        "no repeated nodes" or "covers all required locations", both
        automatically preserved by any reordering of the same node set.
        Used by _two_opt_tighten_route, which only ever reorders segments
        of a route it was handed (never adds/removes nodes).
        """
        if not route:
            return True

        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        if not self.location_graph.has_edge(depot, route[0]):
            return False

        for i in range(len(route) - 1):
            if not self.location_graph.has_edge(route[i], route[i + 1]):
                return False

        if not self.location_graph.has_edge(route[-1], final):
            return False

        return True

    def _two_opt_tighten_route(self, route: List) -> List:
        """
        Standalone distance-minimizing 2-opt local search over `route`
        (topology only -- no picker, no cold chain): repeatedly applies the
        best improving reversal until none is left. Used to tighten the
        nearest-neighbor/BFS construction's route BEFORE it's used for the
        cold-chain eligibility pre-check or as the Hill Climbing search's
        starting point (see _generate_initial_feasible_solution's call
        site for why this matters). Bounded to len(route) sweeps as a
        safety valve -- in practice 2-opt converges in far fewer.
        """
        if len(route) <= 1:
            return route

        current = route
        for _ in range(len(route)):
            best_route = None
            best_distance = self._calculate_route_distance(current)

            for i in range(len(current) - 1):
                for j in range(i + 1, len(current)):
                    candidate = current[:i] + current[i:j + 1][::-1] + current[j + 1:]
                    if not self._route_topology_feasible(candidate):
                        continue
                    candidate_distance = self._calculate_route_distance(candidate)
                    if candidate_distance < best_distance - 1e-9:
                        best_distance = candidate_distance
                        best_route = candidate

            if best_route is None:
                break
            current = best_route

        return current

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

    def _search_cost(self, solution: RouteSolution, evaluator: "RouteEvaluator", validator: "ConstraintsValidator") -> float:
        """
        Objective + a large penalty for any cold-chain overrun -- drives
        ALL accept/reject decisions during the search (initial cost,
        neighbor acceptance). NOT the reported obj_val: see solve()'s
        best_feasible_solution/best_feasible_cost, tracked separately with
        the real (unpenalized) objective, only from fully compliant states.
        """
        return evaluator.evaluate(solution) + self._COLD_CHAIN_PENALTY_WEIGHT * validator.cold_chain_violation(solution)

    def _route_local_search_cost(
        self, batch: str, route: List, picker: str,
        batch_assignments: Dict[str, Set[str]], params: SolveHC4ModelDTO,
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
        t_exec = self._t_exec_pb(batch, route, picker, batch_assignments, params, distance=distance)
        violation = max(0.0, t_exec - params.T_frio_max)
        return params.B_time * distance + self._COLD_CHAIN_PENALTY_WEIGHT * violation

    def _generate_feasible_neighbor(
        self,
        solution: RouteSolution,
        batch_assignments: Dict[str, Set[str]],
        params: SolveHC4ModelDTO,
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
        Full 2-opt on a randomly selected batch's route: every
        topologically feasible reversal is scored by
        _route_local_search_cost (distance + this batch's own cold-chain
        overrun penalty), and the single best (steepest-descent)
        improving one is kept -- deliberately NOT required to already be
        fully cold-chain-compliant (see _generate_feasible_neighbor's
        docstring): a move that reduces the overrun without eliminating
        it is still progress, and the outer solve() loop decides whether
        the resulting whole solution is actually better.
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
        best_local_cost = self._route_local_search_cost(batch, route, picker, batch_assignments, params)

        for i in range(len(route) - 1):
            for j in range(i + 1, len(route)):
                new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]

                if not self._is_route_feasible(new_route, batch, batch_assignments, params.A):
                    continue

                local_cost = self._route_local_search_cost(batch, new_route, picker, batch_assignments, params)
                if local_cost < best_local_cost - 1e-9:
                    best_local_cost = local_cost
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
        """
        Move a random batch to a different picker (any picker, route
        untouched) -- NOT restricted to cold-chain-eligible ones anymore
        (see _generate_feasible_neighbor's docstring): the outer solve()
        loop's _search_cost penalizes a resulting overrun and rejects the
        move if it doesn't help, so this can freely explore reassigning a
        currently-ineligible batch towards a picker that gets it closer to
        (or all the way to) compliance.
        """
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
