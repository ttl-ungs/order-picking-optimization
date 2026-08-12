# opp_aco_3 — Pseudocode

Companion to `README.md` (algorithm description + literature references).
Line up each block below against the corresponding method in `opp_aco_3.py`
(named in parentheses) to read the real implementation.

```text
ALGORITHM OPPAntColonyOptimization.solve(params)                       (solve)
    tau1, tau2   <- init every valid edge to Tau_max        # m-ACO4(1,m): one
    tau_picker   <- init every (batch, picker) to 1.0       # matrix per objective
    best_solution <- None ; best_cost <- +inf ; best_congestion <- 0
    stagnation   <- 0 ; cataclysms_used <- 0

    for iteration in 1 .. Max_it:
        ant_solutions <- []                                 # (solution, time_cost, congestion_cost)

        for ant in 1 .. A_ants:
            S <- BUILD_ANT_SOLUTION(tau1, tau2, tau_picker)
            if S is not None and VALIDATE(S):
                ant_solutions.append( (S, EVALUATE_TIME(S), EVALUATE_CONGESTION(S)) )

        if ant_solutions is empty:
            continue                                        # no ant found a feasible route this round

        iter_best <- the (S, time_cost, *) in ant_solutions with minimum time_cost
        if iter_best.time_cost < best_cost:
            best_solution, best_cost, best_congestion <- copy(iter_best)
            stagnation <- 0
        else:
            stagnation <- stagnation + 1

        UPDATE_PHEROMONES(tau1, tau2, tau_picker, ant_solutions, best_solution, best_cost)

        if stagnation >= Max_iter_wo_improvement:            # "cataclysm" (Chen et al. Sec.4.3;
            if cataclysms_used < Max_cataclysms:              #  Lesch et al. Algorithm 2)
                reset tau1, tau2 to Tau_max ; reset tau_picker to 1.0
                cataclysms_used <- cataclysms_used + 1 ; stagnation <- 0
            else:
                break                                        # stagnation budget exhausted -> stop early

    return best_solution, best_cost, best_congestion


SUBROUTINE BUILD_ANT_SOLUTION(tau1, tau2, tau_picker)                   (_build_ant_solution)
    S <- empty solution

    # Pass 1: fix each picker's processing queue (order of batches unchanged
    # from opp_aco_2 - X_pb assignment only, no congestion involved yet)
    for batch in B with orders (in fixed batch order):
        picker <- ROULETTE_PICK_PICKER(batch, tau_picker, picker_load)   (_select_picker)
        S.assign_batch_to_picker(batch, picker)
        picker_load[picker] += 1

    # Pass 2: build routes round-robin by picker-queue SLOT, so a batch
    # always sees what earlier-slot batches on OTHER pickers already reserved
    tracker <- new CongestionTracker(Min_dwell)
    picker_time[p] <- 0  for every picker p

    for slot in 0 .. max(queue length over all pickers) - 1:
        for picker in P (sorted, deterministic):
            if slot has no batch queued for picker: continue
            batch <- S.sequence[picker][slot]

            route, wait <- BUILD_ROUTE(required_locations(batch), tau1, tau2,
                                        tracker, owner=picker, start=picker_time[picker])
            if route is None:
                return None                          # ant got stuck -> whole solution discarded

            S.set_batch_route(batch, route)
            S.set_batch_congestion_wait(batch, wait)

            exec_time <- BASE_EXEC_TIME(route, batch.orders) + wait   # B_setup + B_picking*cap
            picker_time[picker] <- picker_time[picker] + exec_time    # + B_time*dist + service + wait

    return S


SUBROUTINE BUILD_ROUTE(required, tau1, tau2, tracker, owner, start_time)  (_build_batch_route_congestion_aware)
    route <- [depot] ; current <- depot ; t <- start_time ; wait_total <- 0
    unvisited <- copy(required)

    while unvisited is not empty:
        use_tau1 <- ( random() < P_objective_switch )        # m-ACO4: pick ONE objective for
                                                               # THIS step, shared by every candidate
        for each neighbor n of current not yet visited:
            predicted_wait <- tracker.peek_wait(edge(current,n) and, unless n is
                                                 depot/final, node(n), at time t)   (_peek_logical_wait)
            if use_tau1:
                weight(n) <- tau1(current,n)^Alpha * heuristic_distance(n, unvisited)^Beta
            else:
                weight(n) <- tau2(current,n)^Alpha * ( 1 / (1 + predicted_wait) )^Beta2

        next <- ROULETTE_WHEEL_PICK(candidates, weights)

        # Commit the move for real: reserve edge + node resources, cascading
        # through any pre-existing occupancy (Chen et al.'s dynamic recalculation)
        t, wait_here <- tracker.reserve(edge(current,next), node(next), at t, owner)  (_advance_and_reserve)
        wait_total <- wait_total + wait_here

        route.append(next) ; mark next as visited ; current <- next

    route.append( shortest_path(current -> final) )   # deterministic BFS tail, also reserved
    return route, wait_total


SUBROUTINE UPDATE_PHEROMONES(tau1, tau2, tau_picker, ant_solutions,       (_update_pheromones)
                              best_solution, best_cost)
    evaporate every edge of tau1, tau2, tau_picker by factor (1 - E)

    iter_best_time       <- min(time_cost over ant_solutions)
    iter_best_congestion <- min(congestion_cost over ant_solutions)

    for (S, time_cost, congestion_cost) in ant_solutions:               # m-ACO4 deposit rule
        delta1 <- 1 / (1 + max(0, time_cost       - iter_best_time))        (Alaya et al. Sec.3.2;
        delta2 <- 1 / (1 + max(0, congestion_cost - iter_best_congestion))   Lesch et al. Eqs.11-13)
        deposit delta1 on tau1, delta2 on tau2, for every edge S used
        deposit Q / (1 + time_cost) on tau_picker[(batch, picker)] for every batch S assigned

    if best_solution exists:                                           # elitist boost
        deposit 2.0 on tau1 and tau2 for every edge best_solution used

    clip every entry of tau1, tau2 to the range [Tau_min, Tau_max]      # MAX-MIN Ant System
```

## Complexity note

The outer loop is `O(Max_it × A_ants × |B| × |V|²)` in the worst case (route
construction re-scans neighbors/heuristics per step); the congestion tracker
adds an `O(k)` cost per `reserve`/`peek_wait` call, `k` = number of existing
reservations on that specific resource (small in practice - bounded by how
many batches can plausibly contend for the same node/edge).
