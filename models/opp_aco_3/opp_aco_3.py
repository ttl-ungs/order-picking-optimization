"""
Ant Colony Optimization (ACO) heuristic for OPP v4 with congestion between
pickers and a multi-pheromone (m-ACO4) architecture.

Same problem as opp_model_v4.zpl / opp_aco_2, PLUS two additions grounded in
the literature review for this thesis (papers under /zpaper), cited inline
at each mechanism below:

1. Congestion between concurrent pickers (opp_aco_2 parallelizes pickers but
   never models that they can physically collide/queue for the same space).
   Adapted from:
       Chen, F., Wang, H., Qi, C., & Xie, Y. (2013). An ant colony
       optimization routing algorithm for two order pickers with congestion
       consideration. Computers & Industrial Engineering, 66(1), 77-85.
   Our OPPLocationGraph has no aisle/sub-aisle/block coordinates (unlike the
   paper's narrow-aisle layout), so instead of the paper's per-sub-aisle
   spatio-temporal tabu list we treat every NODE and every undirected EDGE as
   a capacity-1 resource (see models/utils/congestion.py::CongestionTracker).
   Routes are still built one full batch at a time (not a true step-by-step
   joint simulation of all pickers), so resource reservations are registered
   in "round-robin by picker-queue slot" order - an approximation of the
   paper's continuous-time dynamic recalculation, not an exact replication.

2. Multi-pheromone architecture m-ACO4(1,m), m=2 objectives (time/completion
   vs. congestion wait), instead of opp_aco_2's single edge-pheromone table:
       Alaya, I., Solnon, C., & Ghedira, K. Ant Colony Optimization for
       Multi-objective Optimization Problems. Sec. 3.2 "m-ACO4(1,m)": one
       colony, one pheromone matrix per objective; at each construction step
       an ant randomly picks which matrix (and its own heuristic/visibility)
       guides that step. Reported as the best-performing MOACO variant.
   Deposit rule, MAX-MIN pheromone bounds, and the "cataclysm" anti-
   stagnation reset (also present in Chen et al., Sec.4.3) follow the
   calibrated parametrization reported for a real warehouse instance in:
       Lesch, V., Muller, P.B.M., Kramer, M., Hadry, M., Kounev, S., &
       Krupitzer, C. (2023). Optimizing storage assignment, order picking,
       and their interaction in mezzanine warehouses. Applied Intelligence,
       53, 18605-18629 (ACO3/ACO4, Sec.6, Table p.18620, Algorithm 2 p.18618).

The reported/selected "best" solution is still chosen by the time objective
(tau1) alone, to keep solution_info/output/tests shaped exactly like
opp_aco_2's; the congestion objective (tau2) is reported alongside it for
diagnostics, matching the two components explicitly separated in Chen et al.
"""

import time
import random
import heapq
from collections import deque
from typing import Dict, List, Set, Optional, Tuple

from dtos.aco.solve_aco_3_model_dto import SolveAco3ModelDTO
from dtos.opp.solve_result import SolveResult
from dtos.opp.model_dto import ModelDTO
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
from models.utils.congestion import CongestionTracker
import models.utils.solve_registry as solve_registry
from models.opp_aco_3.utils.route_solution import RouteSolution
from models.opp_aco_3.utils.route_evaluator import RouteEvaluator
from models.opp_aco_3.utils.constraints_validator import ConstraintsValidator


class OPPAntColonyOptimization(Model):
    """ACO solver for OPP v4 - congestion-aware, multi-pheromone (m-ACO4)."""

    # See opp_aco_2.OPPAntColonyOptimization._MAX_ROUTE_ATTEMPTS_PER_BATCH for
    # why this exists: one ant needing every batch's random construction to
    # come out loop-free simultaneously is effectively impossible past a
    # handful of batches. Retrying just the batch that failed is what fixes
    # it; the congestion tracker's reservations from a discarded attempt are
    # rolled back via CongestionTracker.snapshot()/restore() so a retry never
    # sees phantom reservations from its own previous, abandoned try.
    _MAX_ROUTE_ATTEMPTS_PER_BATCH = 100

    def __init__(self, dto: ModelDTO):
        super().__init__()
        self.N = sorted(dto.N)
        self.location_graph = dto.location_graph
        self.B = sorted(dto.B)
        self.T_0 = dto.start_time
        self.P = sorted(dto.P) if getattr(dto, "P", None) else ["P1"]
        self._sp_dist = self._precompute_shortest_paths()

    def solve(self, params: SolveAco3ModelDTO):
        """
        Solves the OPP v4 using a congestion-aware, multi-pheromone ACO.

        Args:
            params (SolveAco3ModelDTO): DTO with exact model + ACO + congestion params.
        """
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
        beta = getattr(params, "_Beta", 2.0)
        beta2 = getattr(params, "_Beta2", 2.0)
        evaporation_rate = getattr(params, "_E", 0.02)
        q_factor = getattr(params, "_Q", 100.0)
        min_dwell = getattr(params, "_Min_dwell", 0.0)
        p_objective_switch = getattr(params, "_P_objective_switch", 0.5)
        tau_min = getattr(params, "_Tau_min", 1.0)
        tau_max = getattr(params, "_Tau_max", 25.0)
        max_iter_wo_improvement = getattr(params, "_Max_iter_wo_improvement", 20)
        max_cataclysms = getattr(params, "_Max_cataclysms", 3)

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

        # 1. Pheromone initialization: two matrices (time, congestion) per
        # m-ACO4(1,m) [Alaya et al.], plus the unchanged X_pb assignment
        # pheromone. Initialized to tau_max (MAX-MIN Ant System convention:
        # start high to encourage early exploration, then evaporate down).
        pheromones_time = self._initialize_pheromones(tau_max)
        pheromones_congestion = self._initialize_pheromones(tau_max)
        picker_pheromones = self._initialize_picker_pheromones()

        best_global_solution = None
        best_global_cost = float("inf")
        best_global_congestion_cost = 0.0
        iterations_since_improvement = 0
        cataclysms_used = 0
        iteration = 0

        while iteration < max_it:
            iteration += 1
            ant_solutions = []  # list of (solution, time_cost, congestion_cost)

            for _ in range(num_ants):
                ant_solution = self._build_ant_solution(
                    batch_assignments,
                    pheromones_time,
                    pheromones_congestion,
                    picker_pheromones,
                    params,
                    alpha,
                    beta,
                    beta2,
                    min_dwell,
                    p_objective_switch,
                )

                if ant_solution is not None and validator.validate_solution(ant_solution):
                    time_cost = evaluator.evaluate(ant_solution)
                    congestion_cost = evaluator.evaluate_congestion(ant_solution)
                    ant_solutions.append((ant_solution, time_cost, congestion_cost))

            if not ant_solutions:
                continue

            iter_best_solution, iter_best_cost, iter_best_congestion_of_best = min(
                ant_solutions, key=lambda x: x[1]
            )
            iter_best_time = iter_best_cost
            iter_best_congestion = min(c for _, _, c in ant_solutions)

            improved = iter_best_cost < best_global_cost
            if improved:
                best_global_solution = iter_best_solution.copy()
                best_global_cost = iter_best_cost
                best_global_congestion_cost = iter_best_congestion_of_best
                iterations_since_improvement = 0
            else:
                iterations_since_improvement += 1

            # 4. Pheromone update: evaporation + m-ACO4 deposit on both
            # matrices, elitist boost for the global best, MAX-MIN clipping.
            self._update_pheromones(
                pheromones_time,
                pheromones_congestion,
                picker_pheromones,
                ant_solutions,
                iter_best_time,
                iter_best_congestion,
                evaporation_rate,
                q_factor,
                tau_min,
                tau_max,
                best_global_solution=best_global_solution,
                best_global_cost=best_global_cost,
            )

            # 5. Cataclysm: reset pheromones after prolonged stagnation
            # [Chen et al., Sec.4.3; Lesch et al., Algorithm 2].
            if iterations_since_improvement >= max_iter_wo_improvement:
                if cataclysms_used < max_cataclysms:
                    self._reset_pheromones(pheromones_time, tau_max)
                    self._reset_pheromones(pheromones_congestion, tau_max)
                    picker_pheromones = self._initialize_picker_pheromones()
                    cataclysms_used += 1
                    iterations_since_improvement = 0
                else:
                    # Cataclysm budget exhausted and still stagnant: stop early.
                    break

        elapsed = time.time() - start_time

        print(f"\nACO v3 execution time: {elapsed:.4f}s")
        print(f"Final objective value (time): {best_global_cost:.4f}")
        print(f"Final congestion wait (best solution): {best_global_congestion_cost:.4f}")
        print(f"Iterations completed: {iteration} (cataclysms used: {cataclysms_used})")

        if best_global_solution is None:
            self._register_infeasible(params, elapsed)
            return "infeasible", None

        solution_info = self._build_solution_info(
            best_global_solution, best_global_cost, best_global_congestion_cost, params
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
                "obj_val_congestion": best_global_congestion_cost,
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
                "Beta2": beta2,
                "Min_dwell": min_dwell,
                "Cataclysms_used": cataclysms_used,
                "Max_route_attempts_per_batch": self._MAX_ROUTE_ATTEMPTS_PER_BATCH,
            },
        )
        solve_registry.register(solve_result)
        return solve_result

    def _register_infeasible(self, params: SolveAco3ModelDTO, elapsed: float) -> None:
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
                "Beta": getattr(params, "_Beta", 2.0),
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

    def _initialize_pheromones(self, initial_value: float) -> Dict[Tuple[str, str], float]:
        """Initializes an edge pheromone matrix with `initial_value` for valid edges."""
        pheromones = {}
        vertices = self.location_graph.get_vertices()
        for i in vertices:
            for j in vertices:
                if self.location_graph.has_edge(i, j):
                    pheromones[(i, j)] = initial_value
        return pheromones

    def _reset_pheromones(self, pheromones: Dict[Tuple[str, str], float], initial_value: float) -> None:
        """In-place cataclysm reset of a pheromone matrix to its initial value."""
        for edge in pheromones:
            pheromones[edge] = initial_value

    def _initialize_picker_pheromones(self) -> Dict[Tuple[str, str], float]:
        """Initializes the batch/picker assignment pheromone table (X_pb) with a base value of 1.0."""
        return {(b, p): 1.0 for b in self.B for p in self.P}

    # ------------------------------------------------------------------
    # Ant solution construction
    # ------------------------------------------------------------------

    def _build_ant_solution(
        self,
        batch_assignments: Dict[str, Set[str]],
        pheromones_time: Dict[Tuple[str, str], float],
        pheromones_congestion: Dict[Tuple[str, str], float],
        picker_pheromones: Dict[Tuple[str, str], float],
        params: SolveAco3ModelDTO,
        alpha: float,
        beta: float,
        beta2: float,
        min_dwell: float,
        p_objective_switch: float,
    ) -> Optional[RouteSolution]:
        """
        Each ant first assigns every batch with orders to a picker (X_pb),
        exactly like opp_aco_2, which fixes each picker's processing queue.
        Routes are then built round-by-round across pickers' queue slots
        (slot 0 of every picker, then slot 1, ...), so that a batch always
        "sees" the node/edge occupancy already reserved by batches that,
        given the queues, run at or before its own start time - the causal
        approximation of Chen et al.'s dynamic congestion recalculation
        described in this module's docstring.
        """
        solution = RouteSolution(self.B, self.location_graph, batch_assignments, self.P)
        picker_load = {p: 0 for p in self.P}

        for batch in self.B:
            if not batch_assignments.get(batch):
                continue
            picker = self._select_picker(batch, picker_pheromones, picker_load, alpha, beta)
            solution.assign_batch_to_picker(batch, picker)
            picker_load[picker] += 1

        tracker = CongestionTracker(min_dwell=min_dwell)
        picker_current_time: Dict[str, float] = {p: 0.0 for p in self.P}
        max_slots = max((len(solution.get_picker_sequence(p)) for p in self.P), default=0)

        for slot in range(max_slots):
            for picker in self.P:
                sequence = solution.get_picker_sequence(picker)
                if slot >= len(sequence):
                    continue

                batch = sequence[slot]
                required_locations = self._find_required_locations(
                    batch, batch_assignments[batch], params.A
                )

                if not required_locations:
                    continue

                route = None
                for _ in range(self._MAX_ROUTE_ATTEMPTS_PER_BATCH):
                    tracker_snapshot = tracker.snapshot()
                    candidate, candidate_wait, candidate_exec_extra = self._build_batch_route_congestion_aware(
                        required_locations,
                        pheromones_time,
                        pheromones_congestion,
                        alpha,
                        beta,
                        beta2,
                        p_objective_switch,
                        tracker,
                        owner=picker,
                        start_time=picker_current_time[picker],
                        b_time=params.B_time,
                        S=params.S if isinstance(params.S, dict) else {},
                    )
                    if candidate is not None and len(candidate) == len(set(candidate)):
                        route, congestion_wait, exec_extra = candidate, candidate_wait, candidate_exec_extra
                        break
                    # Discard this attempt's reservations before retrying --
                    # otherwise the next try would see phantom occupancy from
                    # a route that never actually happened.
                    tracker.restore(tracker_snapshot)
                if route is None:
                    return None  # Batch never came out loop-free even after retrying

                solution.set_batch_route(batch, route[1:-1])
                solution.set_batch_congestion_wait(batch, congestion_wait)

                exec_time = self._calculate_batch_execution_time(
                    route[1:-1], batch_assignments[batch], params
                ) + congestion_wait
                picker_current_time[picker] += exec_time

        return solution

    def _select_picker(
        self,
        batch: str,
        picker_pheromones: Dict[Tuple[str, str], float],
        picker_load: Dict[str, int],
        alpha: float,
        beta: float,
    ) -> str:
        """Roulette-wheel selection of a picker for a batch (unchanged from opp_aco_2)."""
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

    def _build_batch_route_congestion_aware(
        self,
        required_locations: Set[str],
        pheromones_time: Dict[Tuple[str, str], float],
        pheromones_congestion: Dict[Tuple[str, str], float],
        alpha: float,
        beta: float,
        beta2: float,
        p_objective_switch: float,
        tracker: CongestionTracker,
        owner: str,
        start_time: float,
        b_time: float,
        S: Dict[str, float],
    ) -> Tuple[Optional[List[str]], float, float]:
        """
        Probabilistically constructs a batch route visiting all required
        locations, m-ACO4-style: at every construction step, one of the two
        pheromone matrices is picked at random to guide that step (m=2
        objectives: time/tau1 vs. congestion/tau2), each with its own
        visibility term. Congestion is a real, physical delay simulated as
        the route is built (CongestionTracker.reserve), not merely a
        heuristic bias - the returned route already reflects the wait each
        node/edge actually incurred.

        Returns:
            (route_with_depot_and_final, total_congestion_wait, current_time)
            or (None, 0.0, start_time) if the ant gets stuck.
        """
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        route = [depot]
        visited = {depot}
        unvisited_req = set(required_locations)
        current = depot
        current_time = start_time
        total_wait = 0.0

        # Safety valve for the backtracking fallback below: bounds how long a
        # single ant can wander before giving up, so allowing revisits can't
        # turn into an unbounded walk on an unlucky draw.
        max_steps = 4 * max(len(self.location_graph.get_vertices()), 1)
        steps = 0

        while unvisited_req:
            steps += 1
            if steps > max_steps:
                return None, 0.0, start_time  # Genuinely stuck wandering, not just one dead end

            neighbors = [
                n
                for n in self.location_graph.get_vertices()
                if self.location_graph.has_edge(current, n)
                and n not in visited
                and n != final
            ]

            if not neighbors:
                # See opp_aco_2._build_batch_route's comment: forbidding every
                # node ever stepped on (not just the required locations)
                # turns this into a self-avoiding walk that dead-ends
                # constantly on anything but a tiny grid. Fall back to
                # allowing a step onto an already-visited, non-required node
                # so the ant can retrace its way out instead of the whole
                # route (and every batch sharing this ant's solution) being
                # discarded.
                neighbors = [
                    n
                    for n in self.location_graph.get_vertices()
                    if self.location_graph.has_edge(current, n) and n != final
                ]
                if not neighbors:
                    return None, 0.0, start_time  # Truly isolated node -- no escape at all

            use_time_matrix = random.random() < p_objective_switch

            probabilities = []
            total_prob = 0.0

            for n in neighbors:
                dist = self.location_graph.get_distance(current, n)
                dist = dist if dist > 0 else 0.01
                travel_time = b_time * dist

                logical_wait = self._peek_logical_wait(
                    tracker, current, n, current_time, travel_time, owner, S
                )

                if use_time_matrix:
                    tau = pheromones_time.get((current, n), 1.0) ** alpha
                    if n in unvisited_req:
                        eta = (1.5 / dist) ** beta
                    else:
                        min_dist_to_req = min(
                            self._sp_dist.get((n, req), float("inf")) for req in unvisited_req
                        )
                        min_dist_to_req = min_dist_to_req if min_dist_to_req > 0 else 0.01
                        eta = (1.0 / (dist + min_dist_to_req)) ** beta
                else:
                    tau = pheromones_congestion.get((current, n), 1.0) ** alpha
                    eta = (1.0 / (1.0 + logical_wait)) ** beta2

                prob = tau * eta
                probabilities.append((n, prob))
                total_prob += prob

            if total_prob == 0:
                return None, 0.0, start_time

            next_node = self._roulette_pick(probabilities, total_prob, neighbors[-1])

            current_time, wait_here = self._advance_and_reserve(
                tracker, current, next_node, current_time, owner, b_time, S
            )
            total_wait += wait_here

            route.append(next_node)
            visited.add(next_node)
            if next_node in unvisited_req:
                unvisited_req.remove(next_node)
            current = next_node

        # See opp_aco_2._build_batch_route's comment: try the clean path first
        # (avoiding every node already stepped on), and only fall back to a
        # revisit-permitting search if that fails -- trying the unrestricted
        # search first could pick a revisiting path over an equally-short clean
        # one that was actually available.
        tail_route = self._find_shortest_path_bfs(current, final, visited)
        if tail_route is None:
            tail_route = self._find_shortest_path_bfs(current, final, set())
        if tail_route is None:
            return None, 0.0, start_time

        for i in range(len(tail_route) - 1):
            n1, n2 = tail_route[i], tail_route[i + 1]
            current_time, wait_here = self._advance_and_reserve(
                tracker, n1, n2, current_time, owner, b_time, S
            )
            total_wait += wait_here

        route.extend(tail_route[1:])
        return route, total_wait, current_time

    def _peek_logical_wait(
        self,
        tracker: CongestionTracker,
        current: str,
        n: str,
        current_time: float,
        travel_time: float,
        owner: str,
        S: Dict[str, float],
    ) -> float:
        """Read-only estimate of the "logic travel distance" wait component [Chen et al., Eq. congestion]."""
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        edge_wait = tracker.peek_wait(
            CongestionTracker.edge_key(current, n), current_time, travel_time, owner
        )
        if n in (depot, final):
            return edge_wait

        arrival_est = current_time + travel_time + edge_wait
        node_wait = tracker.peek_wait(
            CongestionTracker.node_key(n), arrival_est, tracker.dwell(S.get(n, 0.0)), owner
        )
        return edge_wait + node_wait

    def _advance_and_reserve(
        self,
        tracker: CongestionTracker,
        current: str,
        next_node: str,
        current_time: float,
        owner: str,
        b_time: float,
        S: Dict[str, float],
    ) -> Tuple[float, float]:
        """
        Commits the move current -> next_node: reserves the edge (transit)
        and, unless next_node is depot/final, the node (dwell) resources,
        cascading through any pre-existing occupancy. Returns
        (new_current_time, total_wait_incurred_on_this_step).
        """
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        dist = self.location_graph.get_distance(current, next_node)
        dist = dist if dist > 0 and dist != float("inf") else 0.0
        travel_time = b_time * dist

        departure, edge_wait = tracker.reserve(
            CongestionTracker.edge_key(current, next_node), current_time, travel_time, owner
        )
        arrival = departure + travel_time

        if next_node in (depot, final):
            return arrival, edge_wait

        dwell = tracker.dwell(S.get(next_node, 0.0))
        node_start, node_wait = tracker.reserve(
            CongestionTracker.node_key(next_node), arrival, dwell, owner
        )
        return node_start + dwell, edge_wait + node_wait

    def _roulette_pick(
        self, probabilities: List[Tuple[str, float]], total_prob: float, fallback: str
    ) -> str:
        rand_val = random.uniform(0, total_prob)
        cumulative = 0.0
        for n, p in probabilities:
            cumulative += p
            if rand_val <= cumulative:
                return n
        return fallback

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

    # ------------------------------------------------------------------
    # Pheromone update (m-ACO4 deposit rule + MAX-MIN bounds + elitism)
    # ------------------------------------------------------------------

    def _update_pheromones(
        self,
        pheromones_time: Dict[Tuple[str, str], float],
        pheromones_congestion: Dict[Tuple[str, str], float],
        picker_pheromones: Dict[Tuple[str, str], float],
        ant_solutions: List[Tuple[RouteSolution, float, float]],
        iter_best_time: float,
        iter_best_congestion: float,
        evaporation_rate: float,
        q_factor: float,
        tau_min: float,
        tau_max: float,
        best_global_solution: Optional[RouteSolution] = None,
        best_global_cost: float = float("inf"),
    ) -> None:
        """
        Evaporation, then an m-ACO4(1,m) deposit per ant on each matrix:
        Delta_tau^i(c) = 1 / (1 + f_i(S) - f_i(iteration_best_i)) for every
        edge c used by that ant's solution S [Alaya et al., Sec.3.2; Lesch
        et al., Eqs.11-13], plus an elitist boost for the all-time-best
        solution on both matrices, then MAX-MIN clipping [tau_min, tau_max].
        """
        depot = self.location_graph.get_depot()
        final = self.location_graph.get_final()

        for edge in pheromones_time:
            pheromones_time[edge] *= (1.0 - evaporation_rate)
        for edge in pheromones_congestion:
            pheromones_congestion[edge] *= (1.0 - evaporation_rate)
        for key in picker_pheromones:
            picker_pheromones[key] *= (1.0 - evaporation_rate)
            picker_pheromones[key] = max(picker_pheromones[key], 0.01)

        for solution, time_cost, congestion_cost in ant_solutions:
            delta_time = 1.0 / (1.0 + max(0.0, time_cost - iter_best_time))
            delta_congestion = 1.0 / (1.0 + max(0.0, congestion_cost - iter_best_congestion))
            self._deposit_solution(solution, pheromones_time, delta_time, depot, final)
            self._deposit_solution(solution, pheromones_congestion, delta_congestion, depot, final)

            picker = None
            for batch in self.B:
                picker = solution.get_batch_picker(batch)
                if picker is not None and (batch, picker) in picker_pheromones:
                    picker_pheromones[(batch, picker)] += q_factor / (1.0 + time_cost)

        if best_global_solution and best_global_cost < float("inf"):
            elitist_delta = 2.0  # Delta_tau=1 is the max per-ant reward; double it for the elite.
            self._deposit_solution(best_global_solution, pheromones_time, elitist_delta, depot, final)
            self._deposit_solution(best_global_solution, pheromones_congestion, elitist_delta, depot, final)

        for edge in pheromones_time:
            pheromones_time[edge] = min(max(pheromones_time[edge], tau_min), tau_max)
        for edge in pheromones_congestion:
            pheromones_congestion[edge] = min(max(pheromones_congestion[edge], tau_min), tau_max)

    def _deposit_solution(
        self,
        solution: RouteSolution,
        pheromones: Dict[Tuple[str, str], float],
        amount: float,
        depot: str,
        final: str,
    ) -> None:
        """Deposit pheromone on every edge used by the solution's batch routes."""
        for batch in self.B:
            route = solution.get_batch_route(batch)
            if route:
                full_route = [depot] + route + [final]
                for i in range(len(full_route) - 1):
                    edge = (full_route[i], full_route[i + 1])
                    if edge in pheromones:
                        pheromones[edge] += amount

    # ------------------------------------------------------------------
    # Cost / output helpers
    # ------------------------------------------------------------------

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
        self, route: List[str], orders: Set[str], params: SolveAco3ModelDTO
    ) -> float:
        """t_exec formula (Constraint 18 replication), excluding congestion wait
        (added separately by the caller, since it is simulated during construction)."""
        picking_capacity = sum(params.C_n.get(o, 0) for o in orders) if isinstance(params.C_n, dict) else 0
        picking_time = params.B_picking * picking_capacity
        travel_time = params.B_time * self._calculate_route_distance(route)
        service_time = sum(params.S.get(loc, 0) for loc in route) if isinstance(params.S, dict) else 0
        return params.B_setup + picking_time + travel_time + service_time

    def _build_solution_info(
        self,
        solution: RouteSolution,
        cost: float,
        congestion_cost: float,
        params: SolveAco3ModelDTO,
    ) -> dict:
        """Structures the data expected by the output_handler (Picker assignments, Tardiness, Earliness, congestion)."""
        solution_info = {
            "status": "optimal",
            "objective_value": cost,
            "congestion_objective_value": congestion_cost,
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
