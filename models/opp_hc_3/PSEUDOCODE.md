# opp_hc_3 — Pseudocode

Companion to `README.md` (algorithm description + rationale). Line up each
block below against the corresponding method in `opp_hc_3.py` /
`utils/route_evaluator.py` (named in parentheses) to read the real
implementation.

```text
ALGORITHM OPPHillClimbing.solve(params)                                   (solve)
    S <- GENERATE_INITIAL_FEASIBLE_SOLUTION()          (_generate_initial_feasible_solution)
    if S is None:
        return infeasible

    cost <- EVALUATE(S)                                 # prices congestion as a side effect
    iteration <- 0 ; stagnation <- 0

    while iteration < Max_it and stagnation < Max_imp and elapsed_time < Max_time:
        iteration <- iteration + 1

        S' <- GENERATE_NEIGHBOR(S)                      (_generate_feasible_neighbor)
        if S' is None:
            stagnation <- stagnation + 1 ; continue

        cost' <- EVALUATE(S')

        if cost' < cost:                                # accept-if-better (steepest, no annealing)
            S <- S' ; cost <- cost' ; stagnation <- 0
        else:
            stagnation <- stagnation + 1

    return S, cost, EVALUATE_CONGESTION(S)


SUBROUTINE GENERATE_INITIAL_FEASIBLE_SOLUTION()             (_generate_initial_feasible_solution)
    S <- empty solution
    for batch in B with orders:
        route <- DIJKSTRA_NEAREST_NEIGHBOR(required_locations(batch))     (_generate_feasible_route)
        if route is None:
            route <- EXHAUSTIVE_BFS_SEARCH(required_locations(batch))     (_generate_feasible_route_bff)
        if route is None:
            return None                                   # graph disconnected / unreachable stop
        S.set_batch_route(batch, route)

    assign every batch with orders to a picker, round-robin (X_pb)         (_assign_batches_to_pickers)
    return S if VALIDATE(S) else None                       # congestion NOT considered at this stage


SUBROUTINE GENERATE_NEIGHBOR(S)                              (_generate_feasible_neighbor)
    pick uniformly at random among the applicable moves:

    2-OPT_ROUTE(S)                                           (_generate_route_neighbor)
        batch <- random batch with a non-empty route
        best  <- None ; best_distance <- distance(S.route(batch))
        for every reversal segment [i, j] of the route:
            candidate <- route with [i, j] reversed
            if candidate is feasible (all required locations, valid edges, no repeats):
                if distance(candidate) < best_distance:
                    best, best_distance <- candidate, distance(candidate)
        return S with route(batch) <- best   (or None if no improving reversal found)
        # NOTE: picks the geometrically shortest reversal - NOT congestion-aware by
        # itself. A shorter-but-more-congested reversal can still be rejected later
        # by the outer accept-if-better check in solve(), once EVALUATE() prices it.

    REASSIGN_PICKER(S)                                        (_generate_picker_reassignment_neighbor)
        batch  <- random batch with orders
        picker <- random picker other than batch's current one
        return S with batch reassigned to picker (routes untouched)

    SWAP_SEQUENCE(S)                                           (_generate_sequence_swap_neighbor)
        picker <- random picker with >= 2 queued batches
        swap the processing order of two random batches in picker's queue
        return S with that queue reordered


SUBROUTINE EVALUATE(S)                              (RouteEvaluator.evaluate / compute_batch_completions)
    tracker <- new CongestionTracker(Min_dwell)
    picker_time[p] <- 0   for every picker p

    # Round-robin by picker-queue SLOT (same causal approximation as
    # opp_aco_3): a batch prices its congestion against everything already
    # reserved by batches that, given the fixed queues, run at or before it.
    for slot in 0 .. max(queue length over all pickers) - 1:
        for picker in P (sorted, deterministic):
            if slot has no batch queued for picker: continue
            batch <- S.sequence[picker][slot]
            route <- S.get_batch_route(batch)

            base <- B_setup + B_picking*capacity(batch) + B_time*distance(route) + service_time(route)

            if route is not empty:
                _, wait <- SIMULATE_ROUTE_CONGESTION([depot]+route+[final],   (simulate_route_congestion,
                                                       owner=picker,           models/utils/congestion.py)
                                                       start=picker_time[picker],
                                                       tracker)
            else:
                wait <- 0

            S.set_batch_congestion_wait(batch, wait)
            picker_time[picker] <- picker_time[picker] + base + wait
            completion[batch] <- picker_time[picker]

    earliness, tardiness <- compare completion[batch] vs Dd(order) for every order
    objective <- W_full * sum(completion) + W_ea_ta * (W_ea*earliness + W_ta*tardiness)
    return objective


SUBROUTINE SIMULATE_ROUTE_CONGESTION(full_route, owner, start_time, tracker)  (simulate_route_congestion)
    current <- full_route[0] ; t <- start_time ; wait_total <- 0
    for next_node in full_route[1:]:
        travel_time <- B_time * distance(current, next_node)
        t, edge_wait <- tracker.reserve( edge(current, next_node), at t, duration=travel_time, owner )
        wait_total <- wait_total + edge_wait
        if next_node is depot or final:
            current <- next_node ; continue            # depot/final excluded from node contention
        dwell <- max(Min_dwell, service_time(next_node))
        t, node_wait <- tracker.reserve( node(next_node), at t, duration=dwell, owner )
        wait_total <- wait_total + node_wait
        current <- next_node
    return t, wait_total
```

## Why this is a smaller diff than opp_aco_3's pseudocode

Route construction (`GENERATE_INITIAL_FEASIBLE_SOLUTION`) and all three
neighbor moves are **untouched from opp_hc_2** - congestion only enters
through `EVALUATE`, which is where opp_hc_3 actually differs. Compare this
to opp_aco_3, where congestion is woven into the route-construction
subroutine itself (`BUILD_ROUTE`, with its own dedicated pheromone matrix).
