"""
Ant Colony Optimization (ACO) heuristic for OPP v4 with picker speed and
cold chain.

Same problem as opp_aco_2 (multi-picker, all constraints validated):
- Receives: same SolveModelDTO parameters, plus a set of pickers (P)
- Validates: ALL constraints from opp_aco_2, plus cold-chain eligibility
- Optimizes: routes within batches (probabilistic pick-to-pick ACO
  construction after Chen et al. 2013, see _build_batch_route) AND
  the assignment/sequencing of batches to pickers (X_pb), so that batches
  on different pickers run in parallel and batches on the same picker are
  sequenced without overlap
- Output: compatible with build_output

Added on top of opp_aco_2 - picker speed and cold chain, the ACO
counterpart of opp_hc_4 (itself the Hill Climbing counterpart of opp_v5_2_split's
opp_model_v5_2_split_stage2_scheduling.zpl additions over opp_v4):

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
matching opp_v5_2_split itself, which also has no congestion (see analysis/config.py).
"""

import time
import random
import heapq
from typing import Dict, List, Set, Optional, Tuple

from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO
from dtos.opp.solve_result import SolveResult
from dtos.opp.solution_record_dto import SolutionRecordDTO
from dtos.opp.model_dto import ModelDTO
from models.base.model import Model
from models.base.opp_location_graph import OPPLocationGraph
import models.utils.solve_registry as solve_registry
import models.utils.route_construction as route_construction
from models.opp_aco_2.utils.route_solution import RouteSolution
from models.opp_aco_4.utils.route_evaluator import RouteEvaluator
from models.opp_aco_4.utils.constraints_validator import ConstraintsValidator
from models.opp_aco_4.utils import exec_time
from models.opp_v5_2_split.utils.cold_chain_validation import batches_without_eligible_picker, invalid_speeds
from models.utils.input_validation import orders_without_exactly_one_batch
from models.utils.sla import sla_on_time_pct


class OPPAntColonyOptimization(Model):
    """ACO solver for OPP v4 - picker speed + cold chain, no congestion."""

    # Construction attempts per batch per ant before falling back to the
    # exhaustive best-first route (see _build_batch_route/_fallback_route).
    # With pick-to-pick construction one attempt costs ~2-15 ms and
    # succeeds 50-97% of the time on most of v5's realistic_crew batches
    # (1-13% on a few hard ones), measured 2026-09-26 -- so a handful of
    # retries is cheap and keeps ants diverse, while the cached fallback
    # bounds the cost of the hard ones. The old edge-by-edge walk needed
    # 100-1000 retries here and still failed (1822s for one solve).
    _MAX_ROUTE_ATTEMPTS_PER_BATCH = 10

    # Cap for the best-first fallback route search, same value and
    # rationale as opp_hc_4's _MAX_BFF_EXPANSIONS (shared search, see
    # models/utils/route_construction.best_first_route).
    _MAX_BFF_EXPANSIONS = 2_000_000

    # Local search (2-opt + segment re-routing, see
    # route_construction.improve_route) on every ant's route -- see
    # _build_batch_route's docstring.
    _IMPROVE_ANT_ROUTES = True

    # The other hybrid (ACO + local search) components, each switchable on
    # its own so their contribution can be measured separately
    # (analysis/run_aco_ablation_study.py). All on by default:
    # - elite-route polishing of each batch's record route
    #   (route_construction.polish_route, in solve() and _fallback_route);
    _POLISH_ELITE_ROUTES = True
    # - swapping each batch's shortest-known route into the best solution
    #   (_recombine_shortest_routes);
    _RECOMBINE_SHORTEST_ROUTES = True
    # - schedule local search on the best solution (_schedule_local_search).
    _SCHEDULE_LOCAL_SEARCH = True

    # Route pheromone bounds, MAX-MIN Ant System style (Stuetzle & Hoos
    # 2000; the variant described in Alaya & Solnon, "Ant Colony
    # Optimization for Multi-objective Optimization Problems", pp.3-4):
    # pheromone starts at tau_max, only the best routes deposit, delta
    # tau = 1, and tau is kept within [tau_min, tau_max]. Each batch
    # reinforces at most 2 routes per iteration (iteration-best and
    # best-so-far, see _update_route_pheromones), so the steady state of
    # tau <- (1 - rho) tau + 2 is 2 / rho: tau_max = 2 / rho. tau_min =
    # tau_max / 50 keeps every pick pair choosable (the ratio is our
    # choice; Stuetzle & Hoos derive it from n and a target
    # probability, of the same order for n ~ 20-26 picks). MAX-MIN bounds
    # are also what Lesch et al. (2023), "Optimizing storage assignment,
    # order picking, and their interaction in mezzanine warehouses",
    # Applied Intelligence 53:18605-18629, use for ACO picker routing
    # (tau in [1, 25], alpha = 1, beta = 2, rho = 0.02, p.18620), with
    # the same 1/d visibility core (their Eq. 6, p.18617).
    #
    # Why not the previous scheme (every ant deposits Q / cost on the
    # route, floor 0.01, init 1.0): with Q = 100 and costs ~1.5e5 a
    # deposit is ~7e-4, below the floor, so route pheromone decayed to
    # the floor everywhere and carried no information (measured
    # 2026-09-26 on realistic_crew_scenario(7)). Chen et al. (2013), Eqs.
    # 3-5, deposit 1 / L_k with L_k the TOUR LENGTH -- i.e. the route --
    # not the full objective; we follow that: route pheromone learns from
    # route length only, per batch, and the full objective still drives
    # picker pheromone and the best-so-far solution.
    _MMAS_TAU_MIN_RATIO = 1.0 / 50.0

    # Share of params.Max_time that ant construction may use before
    # stopping (once a compliant solution exists); the rest is reserved for
    # the end-of-iteration elite-route polishing and schedule local search.
    # Only matters on instances that hit the budget at all. Measured
    # 2026-09-27 on the 100x100 migrated grid with Max_time = 600 s: letting
    # ants use the whole budget left polishing 11 s and the schedule search
    # none, objective 1,403,120 -- vs 917,328 when post-processing ran in
    # full (1878 s, before the budget covered it).
    _ANT_BUDGET_SHARE = 0.5

    # Multiplier applied to ConstraintsValidator.cold_chain_violation() (a
    # time-unit overrun) before adding it to an ant solution's cost -- see
    # constraints_validator.py's module docstring for why cold chain is a
    # SOFT constraint during search now (2026-09-09 audit fix). Large
    # enough to dominate the search away from violations (typical marginal
    # objective contribution per unit of recollection time is W_full,
    # usually single-to-low-double digits) without using an arbitrarily
    # huge Big-M-style constant -- this is a continuous heuristic penalty,
    # not a MIP constraint, so there's no SCIP-presolve-numerics failure
    # mode to worry about the way there was with opp_v5_2_split's M_seq.
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
        # Underlying UNDIRECTED adjacency, for the completability check in
        # route_construction.stitch_route (see keeps_route_completable).
        self._undirected_adjacency = route_construction.undirected_adjacency(self.location_graph)
        # Same warehouse with edges reversed, for backwards construction
        # (see route_construction.stitch_route_either_way).
        self._reversed_graph = route_construction.reversed_graph(self.location_graph)

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

        # is_batch_assignment_valid only rejects an order in TWO+ batches.
        unassigned_or_duplicated = orders_without_exactly_one_batch(params.Bn, self.N)
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
        # Absolute deadline for the expensive post-processing too (elite
        # route polishing, schedule local search), not just ant building:
        # on the 100x100 migrated grid those took ~1090 s of a run whose
        # Max_time was 1 s (2026-09-27 phase timing). None = no budget.
        self._deadline = start_time + max_time if max_time != float("inf") else None
        alpha = getattr(params, "_Alpha", 1.0)
        beta = getattr(params, "_Beta", 2.5)
        evaporation_rate = getattr(params, "_E", 0.15)
        q_factor = getattr(params, "_Q", 100.0)

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
            self._register_infeasible(params, time.time() - start_time)
            return "infeasible", None

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

        picker_pheromones = self._initialize_picker_pheromones()

        # Batch->required-locations is fixed for the whole solve() (batch
        # assignments don't change), yet _find_required_locations used to
        # be recomputed once per ant per batch. Profiling a 100-order/20-
        # batch stress instance showed this (and the validator's identical
        # _get_required_locations) at ~18% of total runtime combined.
        # Precomputing it once here turns 900 ants x 20 batches worth of
        # recomputation into 20 calls.
        required_locations_by_batch = {
            batch: self._find_required_locations(batch, batch_assignments[batch], params.A)
            for batch in self.B
            if batch_assignments.get(batch)
        }
        self._required_by_batch = required_locations_by_batch
        self._tau_max = 2.0 / evaporation_rate
        self._tau_min = self._tau_max * self._MMAS_TAU_MIN_RATIO
        pheromones = self._initialize_pheromones(required_locations_by_batch)

        # Exact (not estimated) reachability pre-check: if a required
        # location can't be reached from the depot, or can't reach `final`,
        # NO route -- built by any ant, in any iteration -- could ever
        # visit it. This is a static graph-topology fact -- two linear-time
        # searches (_reachable_from: forwards from the depot, and over the
        # reversed graph from `final`) -- so it costs almost nothing to
        # check upfront instead of letting every ant of
        # every iteration exhaust _MAX_ROUTE_ATTEMPTS_PER_BATCH on a batch
        # that was never solvable in the first place (same "honest
        # infeasibility, no shortcut before trying" philosophy as the
        # cold-chain pre-check above -- this is just the topology half of
        # it, not a substitute for the search on batches that pass it).
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
        # "Iteration of convergence": which iteration last improved
        # best_global_solution (always cold-chain-compliant, see below) --
        # distinct from `iteration`/`max_it` (iterations actually run vs.
        # the configured LIMIT).
        best_found_at_iteration = 0
        # Shortest route found so far for each batch, by any ant (see
        # _recombine_shortest_routes).
        shortest_route_by_batch: Dict[str, Tuple[float, List[str]]] = {}

        timed_out = False
        while iteration < max_it and not timed_out:
            iteration += 1
            ant_solutions = []
            feasible_ant_solutions = []
            iteration_best_route_by_batch: Dict[str, Tuple[float, List[str]]] = {}

            for ant in range(num_ants):
                # Wall-clock budget (params.Max_time): checked per ant, so a
                # very large instance can stop mid-iteration -- but only
                # once a cold-chain-compliant solution exists (this
                # iteration's or an earlier one's), so the budget can never
                # produce a false "infeasible" (same honesty rule as the
                # pre-checks above). Ants stop at _ANT_BUDGET_SHARE of the
                # budget, leaving the rest for polishing the best routes and
                # schedule (which honor the full deadline, see _deadline).
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

                # validate_solution() now checks ONLY opp_aco_2's original
                # hard constraints (topology/capacity/one-picker-per-batch)
                # -- cold chain is a soft penalty below, not a hard reject
                # here, so a single cold-chain-tight batch can no longer
                # starve pheromone updates for every OTHER batch in the
                # same ant (see constraints_validator.py's module docstring).
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
                # Per-batch compliance set: which batches' route/picker
                # pheromone this ant is allowed to reinforce (see
                # _deposit_solution's docstring for why this must be
                # per-batch, not all-or-nothing for the whole solution).
                compliant_batches = validator.compliant_batches(ant_solution)
                ant_solutions.append((ant_solution, cost, compliant_batches))

                if violation == 0.0:
                    feasible_ant_solutions.append((ant_solution, base_cost))

            # When a batch's iteration-best route beats that batch's record,
            # polish it with the expensive elite-route local search
            # (route_construction.polish_route: pick-level 2-opt + or-opt
            # relocation + improve_route) before storing it as the batch's
            # best-so-far route -- used by _recombine_shortest_routes and as
            # MMAS's best-so-far deposit. Only on a new record, not every
            # iteration: at 14x14 one polish costs ~120-260 ms (measured
            # 2026-09-26), too much for 6 batches x 60 iterations, while
            # records are comparatively rare.
            records = [
                (batch, route)
                for batch, (length, route) in iteration_best_route_by_batch.items()
                if length < shortest_route_by_batch.get(batch, (float("inf"), None))[0] - 1e-9
            ]
            for index, (batch, route) in enumerate(records):
                # Under a budget, each record gets an equal share of what's
                # left, keeping one more share for the schedule local search
                # below -- otherwise the first few polishes on a huge grid
                # eat all of it (2026-09-27, 100x100: 284 s of polishing,
                # schedule search 0 s).
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

            # best_global_solution is tracked ONLY among cold-chain-COMPLIANT
            # ants (base_cost, unpenalized -- violation is 0 for these
            # anyway) so the reported final answer always satisfies
            # T_frio_max exactly, even though the search itself tolerates
            # temporary violations to keep learning.
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
                "iterations_run": iteration,
                "Max_time": max_time,
                "timed_out": timed_out,
                "best_found_at_iteration": best_found_at_iteration,
            },
        )
        solve_result.solution_record = SolutionRecordDTO(
            model_name="opp_aco_4",
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
        return exec_time.fixed_time(orders, params.C_n, params.B_setup, params.B_picking)

    def _route_time(
        self, route: List[str], params: SolveAco4ModelDTO, distance: Optional[float] = None
    ) -> float:
        """
        Travel time (B_time * distance) + service time -- opp_v5_2_split's
        R_b_time, the part scaled by V_p. Pass `distance` when the caller
        already computed it, to avoid recomputing it again here (2026-09-10
        audit finding: _eligible_pickers_for_batch used to call this once
        per picker, recomputing the SAME route's distance every time, even
        though distance doesn't depend on picker at all).
        """
        return exec_time.route_time(self.location_graph, route, params.B_time, params.S, distance)

    def _t_exec_pb(
        self, batch: str, route: List[str], picker: str,
        batch_assignments: Dict[str, Set[str]], params: SolveAco4ModelDTO,
        distance: Optional[float] = None,
    ) -> float:
        """See _route_time's docstring for why `distance` can be passed in precomputed."""
        orders = batch_assignments.get(batch, set())
        return exec_time.t_exec_pb(
            self.location_graph, route, orders, picker,
            params.C_n, params.B_setup, params.B_picking, params.B_time, params.S, params.V_p,
            distance=distance,
        )

    def _eligible_pickers_for_batch(
        self, batch: str, route: List[str], batch_assignments: Dict[str, Set[str]], params: SolveAco4ModelDTO,
    ) -> List[str]:
        """Pickers p for which t_exec_pb[p, batch] <= T_frio_max, given `route`."""
        # Route distance doesn't depend on picker -- compute it once
        # instead of once per picker (see _route_time's docstring).
        distance = self._calculate_route_distance(route)
        return [
            p for p in self.P
            if self._t_exec_pb(batch, route, p, batch_assignments, params, distance=distance) <= params.T_frio_max + 1e-9
        ]

    # NOTE: this model used to have a route-time ESTIMATE (greedy nearest-
    # neighbor over shortest-path distances, 2-opt-tightened) here, feeding a pre-check
    # that could declare a genuinely feasible instance "infeasible" before
    # a single ant ever ran (2026-09-09/10 audit findings -- see header).
    # Removed: the only pre-check left is the exact, estimate-free one in
    # solve() (route_time = 0.0 for every batch), and every batch that
    # survives it gets a real, full run of the ACO loop instead.

    @staticmethod
    def _reachable_from(location_graph, source: str) -> Set[str]:
        """
        Every vertex reachable from `source` along `location_graph`'s edges
        (BFS). Replaces an all-pairs Dijkstra precomputation (_sp_dist)
        whose only remaining use was solve()'s reachability pre-check: it
        scanned every vertex per settled node, O(V^3) overall, which never
        finished on the 100x100 migrated stress grid (V = 10,000 -- ACO
        timed out at 40 min there, 2026-09-27) while this is O(V + E).
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
        Pheromone on (pick, pick) pairs, following Chen et al. (2013),
        A-TOP, p.81: tau_ij lives on every pair of picks (plus the depot)
        an ant can travel between, not on aisle edges. Here that is, per
        batch, every ordered pair among {depot} + its required locations +
        {final} (depot only as origin, final only as destination -- they
        open/close the route). Pairs are shared across batches: two
        batches needing the same two locations learn from each other,
        since the geometry between them is the same.
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
        required_locations_by_batch: Dict[str, Set[str]],
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

            required_locations = required_locations_by_batch[batch]

            if required_locations:
                route = None
                # Alternate construction direction between attempts, from a
                # random side (see route_construction.stitch_route_either_way
                # for why both are needed).
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
        backwards: bool = False,
    ) -> Optional[List[str]]:
        """
        Probabilistically constructs a batch route (depot ... final, a
        simple path) visiting every required location.

        Pick-to-pick construction, following Chen et al. (2013), "An ant
        colony optimization routing algorithm for two order pickers with
        congestion consideration" (A-TOP), Computers & Industrial
        Engineering 66:77-85: the ant "travels from one pick to another"
        (p.79), i.e. picker routing is treated as a Steiner-TSP over the
        pick locations, not as a walk over individual aisle edges. At each
        step the ant chooses the NEXT REQUIRED LOCATION r among those still
        unvisited with the Ant System random-proportional rule (their Eq. 2,
        p.81):

            p(r) = tau[last, r]^alpha * eta[r]^beta / sum(...),
            eta[r] = 1 / dist(current, r)

        and walks the shortest path to it. Coruzzolo et al. (2023),
        Logistics 7:61 (pp.6-9), use the same Steiner-TSP view with
        precomputed shortest-path distances for their routing step.

        Deviation from Chen et al. (our own, forced by the problem
        definition): Chen et al. take pick-to-pick distances from a static
        precomputed table and allow re-walking aisles already traversed.
        v5 (the exact model these heuristics are compared against) forbids
        revisiting any vertex (see test_case_forced_revisit_is_infeasible),
        so the distance used for eta and the path walked are recomputed
        each step with Dijkstra AVOIDING every vertex already on the route
        (and `final`, which may only close the route).

        Why this replaced the previous edge-by-edge walk (2026-09-26 audit
        finding): on v5's realistic_crew_scenario batches (23-26 required
        locations on a grid) a random self-avoiding walk over single edges
        boxes itself in long before finishing -- 193/200 constructions on
        realistic_crew_scenario(14)'s B1 ended with every neighbor a dead
        end, and even 1000 retries per batch took 1822s for one solve.
        Choosing among required locations instead, and connecting them by
        shortest non-revisiting paths, removes those dead ends by
        construction almost always.

        Returns None if the stitching still paints itself into a corner
        (no candidate pick passes route_construction.keeps_route_completable, or `final` is
        unreachable without revisiting); _build_ant_solution then retries
        and, after _MAX_ROUTE_ATTEMPTS_PER_BATCH failures, uses
        _fallback_route (our own addition, not from the papers): the same
        exhaustive best-first search opp_hc_4 uses.

        Finally the route is tightened by local search when
        _IMPROVE_ANT_ROUTES is set: 2-opt (shared with opp_hc_4) alternated
        with segment re-routing (shortest corridor between consecutive
        picks), see models/utils/route_construction.improve_route. Chen et
        al. apply no local search; Coruzzolo et al. do (on batches), and
        hybridizing ant tours with local search is standard ACO practice
        (Dorigo & Stuetzle 2004, "Ant Colony Optimization", ch. 3.7) -- our
        choice. Measured 2026-09-26 on realistic_crew_scenario(7): without
        it ACO's routes summed 451 route-time units vs 425 for v5's exact
        Stage 1.
        """
        # Chen et al. (2013), Eq. 2: tau^alpha * eta^beta, eta = 1/d, with
        # pheromone indexed by (previous pick, next pick) in the route's
        # depot -> final direction -- so when building backwards (from the
        # final node, see stitch_route_either_way) the construction's
        # current -> r step is the route's r -> current pair.
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
        Try the best-so-far solution with every batch's route swapped for
        the shortest route any ant has built for that batch so far
        (keeping its picker assignment and sequence). Returns the new
        (solution, cost) if it is valid, cold-chain compliant and strictly
        cheaper, else None.

        Our own addition, not from the papers. Why it's needed (measured
        2026-09-26 on realistic_crew_scenario(7) with W_full=27): the
        construction does reach v5's optimal Stage 1 route for most
        batches, but rarely, and in a different ant each time -- an ant's
        cost couples all batches, so one short route inside an otherwise
        worse ant gets no credit. Remembering the best route per batch
        and recombining is an elitist memory (in the spirit of the
        best-so-far deposit of elitist Ant System / MMAS, Dorigo &
        Stuetzle 2004, ch. 3.3-3.4), applied per batch because batches'
        routes are independent of each other. A shorter route is not
        always cheaper under this objective (finishing earlier can add
        earliness when W_full is small), hence the evaluator decides.
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
        First-improvement local search over the SCHEDULE of `solution`
        (routes fixed): (1) move one batch to another picker, at any
        position of that picker's sequence; (2) swap two batches' positions
        within a picker's sequence; (3) exchange two batches between
        different pickers. A move is accepted only if the result is valid,
        cold-chain compliant and strictly cheaper; repeats until no move
        improves. Returns the (possibly unchanged) solution and its cost.

        Our own addition, not from the papers (Chen et al.'s ACO only
        routes; batch-to-picker assignment/sequencing is outside their
        problem). Why it's needed (measured 2026-09-26 on
        realistic_crew_scenario(7), W_full=27): with every route already
        equal to v5's optimal Stage 1 routes, ACO still lost to v5 by ~8
        objective units, from the schedule alone -- ants pick pickers by
        roulette and sequence each picker by earliest due date
        (_sort_picker_queues_by_due_date), which is a good rule of thumb
        but not optimal against this objective, while v5's Stage 2 solves
        the schedule exactly. These are the same neighborhoods opp_hc_4
        searches (_generate_picker_reassignment_neighbor /
        _generate_sequence_swap_neighbor), applied exhaustively to the
        best-so-far solution only, and only when it changes (a sweep is
        O(B^2 * P) evaluations -- cheap next to a full ant colony
        iteration at these sizes).
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
                break  # Max_time (see solve()): keep the best schedule so far

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
        the farthest-insertion order (route_construction.insertion_route,
        Rosenkrantz, Stearns & Lewis 1977) realized forwards, else on the
        reversed graph, else the exhaustive best-first search
        (best_first_route, within _MAX_BFF_EXPANSIONS) -- polished with
        route_construction.polish_route. A full depot ... final list, or
        None if none of them finds a simple route.

        Insertion first because it's cheap and, when it realizes, gives a
        short route (measured 2026-09-27: e.g. realistic_crew_scenario(14)
        B2 = 154.5 route-time units, v5's exact Stage 1 optimum), while
        best_first_route's first feasible route can be much longer -- too
        long to be cold-chain-eligible in realistic_crew_cold_chain, where
        that made every ant non-compliant. Cached per required-location
        set: all of this is deterministic, and without the cache a batch
        that needs it would pay for it once per ant.
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
        """Finds all locations that MUST be visited for a given batch's orders."""
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
        MAX-MIN update of the (pick, pick) route pheromone (see the
        _MMAS_TAU_MIN_RATIO comment for sources and why): evaporate every
        pair, tau <- (1 - rho) tau, then deposit delta tau = 1 on the
        consecutive-pick pairs of each (batch, route) in `batch_routes` -- per batch, its
        iteration-best and best-so-far (shortest) routes -- and clamp to
        [tau_min, tau_max].

        Pairs are taken over the route's PICKS (Chen et al. 2013, p.81:
        delta tau_ij for the pick-to-pick moves), in the order the route
        first reaches them, depot first and final last -- matching what
        _build_batch_route chooses. No cold-chain filter is needed here
        (unlike picker pheromone): these are the SHORTEST routes found,
        and a shorter route can only lower t_exec_pb, never cause a
        T_frio_max violation.
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
        Evaporation + deposit on the (batch, picker) pheromone table (route
        pheromone has its own update, _update_route_pheromones). Each entry
        in `ant_solutions` is a (solution, cost, compliant_batches) triple
        -- see _deposit_solution's docstring for why deposit is filtered to
        `compliant_batches` instead of depositing for the whole solution.
        Ant System style (every ant deposits Q / cost) plus an elitist x2
        deposit for the best-so-far solution -- unchanged from the
        previous version of this model.
        """
        for key in picker_pheromones:
            picker_pheromones[key] *= (1.0 - evaporation_rate)
            picker_pheromones[key] = max(picker_pheromones[key], 0.01)

        for solution, cost, compliant_batches in ant_solutions:
            if cost <= 0:
                continue
            self._deposit_solution(solution, picker_pheromones, q_factor / cost, batches=compliant_batches)

        if best_global_solution and best_global_cost < float('inf') and best_global_cost > 0:
            # best_global_solution is only ever set from a cold-chain-
            # compliant ant (see solve()'s feasible_ant_solutions), so every
            # one of its batches is compliant -- deposit for all of them.
            self._deposit_solution(best_global_solution, picker_pheromones, (q_factor / best_global_cost) * 2.0)

    def _deposit_solution(
        self,
        solution: RouteSolution,
        picker_pheromones: Dict[Tuple[str, str], float],
        amount: float,
        batches: Optional[Set[str]] = None,
    ) -> None:
        """
        Deposit pheromone on the (batch, picker) pairs used by a solution,
        restricted to `batches` (None means every batch in self.B -- used
        for the elitist best_global_solution deposit, always fully
        cold-chain-compliant by construction).

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
            picker = solution.get_batch_picker(batch)
            if picker is not None and (batch, picker) in picker_pheromones:
                picker_pheromones[(batch, picker)] += amount

    def _calculate_route_distance(self, route: List[str]) -> float:
        """Total travel distance of depot -> route... -> final."""
        return exec_time.calculate_route_distance(self.location_graph, route)

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
        return exec_time.t_exec_pb(
            self.location_graph, route, orders, picker,
            params.C_n, params.B_setup, params.B_picking, params.B_time, params.S, params.V_p,
        )

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
