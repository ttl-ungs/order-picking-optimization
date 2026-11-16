"""Small scenarios of the routing cases of the functional tests."""


def two_batches_two_routes():
    """Two independent batches with a unique shortest route each."""
    return {
        "N": {"O1", "O2"},
        "P": {"P_slow", "P_fast"},
        "B": {"B1", "B2"},
        "V": {"D", "A", "B", "F"},
        "E": {
            ("D", "A"), ("A", "F"),
            ("D", "B"), ("B", "F"),
            # More expensive alternatives ensure routing is actually decided.
            ("D", "F"), ("A", "B"),
        },
        "depot": "D",
        "final": "F",
        "D_ij": {
            ("D", "A"): 2.0, ("A", "F"): 2.0,
            ("D", "B"): 6.0, ("B", "F"): 6.0,
            ("D", "F"): 30.0, ("A", "B"): 20.0,
        },
        "S_i": {"D": 0.0, "A": 1.0, "B": 2.0, "F": 0.0},
        "A_ni": {
            ("O1", "D"): 0, ("O1", "A"): 1, ("O1", "B"): 0, ("O1", "F"): 0,
            ("O2", "D"): 0, ("O2", "A"): 0, ("O2", "B"): 1, ("O2", "F"): 0,
        },
        "B_nb": {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1},
        "C_n": {"O1": 1.0, "O2": 1.0},
        "T_due_n": {"O1": 100.0, "O2": 100.0},
        "W_c": 1.0,
        "W_pen": 0.0,
        "W_e": 1.0,
        "W_t": 1.0,
        "T_travel": 1.0,
        "T_setup": 1.0,
        "T_pick": 1.0,
        "C_v": 10.0,
        "M": 10000.0,
        "V_p": {"P_slow": 1.0, "P_fast": 2.0},
        "T_cold": 100.0,
    }


def one_cold_batch(cold_limit=10.0):
    """A batch which only the fast picker can prepare under the cold limit."""
    data = two_batches_two_routes()
    data.update(
        N={"O1"},
        B={"B1"},
        V={"D", "B", "F"},
        E={("D", "B"), ("B", "F"), ("D", "F")},
        D_ij={("D", "B"): 6.0, ("B", "F"): 6.0, ("D", "F"): 30.0},
        S_i={"D": 0.0, "B": 2.0, "F": 0.0},
        A_ni={("O1", "D"): 0, ("O1", "B"): 1, ("O1", "F"): 0},
        B_nb={("O1", "B1"): 1},
        C_n={"O1": 1.0},
        T_due_n={"O1": 100.0},
        T_cold=cold_limit,
    )
    return data


# The three scenarios below reuse one_cold_batch's fixed geometry (route B1
# costs R_b=14.0 -- distance 6+6=12 at T_travel=1.0, plus S_i["B"]=2.0 --
# and F_b=T_setup+T_pick*C_n["O1"]=1.0+1.0*1.0=2.0), so
# T_exec_pb(P_fast, B1) = 2.0 + 14.0/2.0 = 9.0 exactly and
# T_exec_pb(P_slow, B1) = 2.0 + 14.0/1.0 = 16.0 exactly -- precise enough to
# assert on, not just "which picker got it".

def cold_chain_exact_boundary():
    """T_cold set to EXACTLY P_fast's T_exec_pb (9.0) -- PB_elig uses
    `<=`, so this must still be eligible, not excluded by an off-by-one on
    the boundary."""
    return one_cold_batch(cold_limit=9.0)


def cold_chain_infeasible_for_every_picker():
    """T_cold below even the fastest picker's T_exec_pb (9.0) -- no
    (picker, batch) pair is ever eligible, so PB_elig is empty for B1 and
    `assign_exactly_one_picker` (sum over an empty set == 1) can never
    hold: the model must come back genuinely infeasible, not just "no
    picker found" from the Python-side preflight check."""
    return one_cold_batch(cold_limit=5.0)


def heterogeneous_speed_precise():
    """Same two-batch, two-speed setup already used for the assignment-
    direction test, kept here to assert the exact completion-time formula:
    T_exec_pb = F_b + R_b / V_p -- i.e. that ONLY the route
    portion is scaled by picker speed, never the fixed setup/picking time.
    With V_p={P_slow: 1.0, P_fast: 2.0}, R_b={B1: 5.0, B2: 14.0} and
    F_b=2.0 for both batches (T_setup=1.0, T_pick=1.0,
    C_n={"O1": 1.0, "O2": 1.0}):
        T_exec_pb(P_slow, B1) = 2.0 + 5.0/1.0  =  7.0
        T_exec_pb(P_fast, B2) = 2.0 + 14.0/2.0 =  9.0
    which is also the cost-minimizing assignment (7.0+9.0=16.0, cheaper
    than the 20.5 the reversed assignment would cost)."""
    return two_batches_two_routes()


# The builders below reuse the same graph (route via A costs R_b=5.0,
# route via B costs 14.0) and F_b = T_setup + T_pick * sum(C_n)
# = 1.0 + 1.0 * (orders in the batch). Every expected value in the tests is
# derived by hand from those numbers.


def cold_limit_between_route_and_total():
    """T_cold = 8.0 sits between P_fast's route share (14.0/2.0 = 7.0)
    and its whole execution time (2.0 + 7.0 = 9.0). An implementation that
    compared only the route against the limit would accept the batch; the
    documented one compares the whole T_exec_pb and must reject it."""
    return one_cold_batch(cold_limit=8.0)


def cold_limit_within_tolerance():
    """T_cold = 9.0 - 5e-10: P_fast's T_exec_pb (9.0) exceeds it by less
    than the documented 1e-9 tolerance, so the pair must stay eligible --
    otherwise rounding noise in a derived time could drop a valid picker."""
    return one_cold_batch(cold_limit=9.0 - 5e-10)


def two_batches_same_route(fast_speed=2.0, cold_limit=100.0):
    """Two one-order batches that both need location B (R_b = 14.0).

    T_exec_pb = 2.0 + 14.0 / V_p: 16.0 for P_slow (V_p = 1.0) and
    2.0 + 14.0 / fast_speed for P_fast. Due dates are far and earliness /
    tardiness are off (W_pen = 0), so the objective is the sum of the two
    completion times: the model picks between queueing both batches on the
    fast picker and giving one to the slow picker.
    """
    data = two_batches_two_routes()
    data.update(
        A_ni={
            ("O1", "D"): 0, ("O1", "A"): 0, ("O1", "B"): 1, ("O1", "F"): 0,
            ("O2", "D"): 0, ("O2", "A"): 0, ("O2", "B"): 1, ("O2", "F"): 0,
        },
        V_p={"P_slow": 1.0, "P_fast": fast_speed},
        T_cold=cold_limit,
    )
    return data


def two_cold_batches():
    """Both batches of two_batches_same_route under T_cold = 10.0: only
    P_fast is eligible for either (9.0 <= 10.0 < 16.0), so it has to run both
    back to back. The second one completes at 18.0, past the limit -- which
    is correct, because the limit bounds each batch's execution time, not
    the waiting before it or the picker's cumulative time."""
    return two_batches_same_route(fast_speed=2.0, cold_limit=10.0)


def slow_picker_late_order(speed=0.5, due_date=20.0):
    """One order at B, a single picker slower than 1.0, and a due date the
    picker cannot meet: t_exec = 2.0 + 14.0 / 0.5 = 30.0, so the order is
    10.0 late. W_c = 10 outweighs the single order's earliness, so there
    is no reason to delay: completion 30.0, objective 10*30 + 10 = 310."""
    data = one_cold_batch(cold_limit=100.0)
    data.update(
        P={"P_only"},
        V_p={"P_only": speed},
        T_due_n={"O1": due_date},
        W_c=10.0,
        W_pen=1.0,
        W_e=1.0,
        W_t=1.0,
    )
    return data


def three_orders_one_batch(w_full):
    """Three orders at location A in one batch, one picker at speed 1.0.

    Earliest completion: F_b (1.0 + 1.0 * 3) + R_b (5.0) = 9.0.
    Every due date is 20.0 and W_e = W_t = W_pen = 1. Delaying the batch
    one unit costs W_c and saves one unit of earliness per order still
    early, so with three orders the model delays while W_c < 3:
      - w_full = 1: completes at 20.0, no earliness, objective 20.0.
      - w_full = 5: completes at 9.0, earliness 11.0 per order,
        objective 5 * 9 + 3 * 11 = 78.0.
    """
    data = two_batches_two_routes()
    data.update(
        N={"O1", "O2", "O3"},
        P={"P_only"},
        B={"B1"},
        A_ni={
            (order, location): int(location == "A")
            for order in ("O1", "O2", "O3") for location in ("D", "A", "B", "F")
        },
        B_nb={("O1", "B1"): 1, ("O2", "B1"): 1, ("O3", "B1"): 1},
        C_n={"O1": 1.0, "O2": 1.0, "O3": 1.0},
        T_due_n={"O1": 20.0, "O2": 20.0, "O3": 20.0},
        W_c=w_full,
        W_pen=1.0,
        W_e=1.0,
        W_t=1.0,
        V_p={"P_only": 1.0},
    )
    return data


def two_possible_routes(due_date):
    """The two_possible_routes instance (scenario_03): two
    orders at L4, one batch each, two pickers at speed 1.0, and three ways
    from L1 to L5 through L4 -- the short one L1 -> L4 -> L5 (distance 8)
    and two long ones through L2 or L3 (distance 15).

    F_b = T_setup + T_pick * 3 = 4.0, so a batch takes
    4.0 + 0.5 * 8 = 8.0 on the short route and 4.0 + 0.5 * 15 = 11.5 on a
    long one. Earliness weighs W_pen * W_e = 10 > W_c = 1, so a batch
    that can finish before its due date waits until it (voluntary wait):
      - due_date = 10: only the short route arrives in time; completion
        10.0 per batch, objective 1 * (10 + 10) = 20.0. A long route would
        be 1.5 late (10 * 5 * 1.5 = 75 of tardiness per batch).
      - due_date = 15: every route arrives in time, so every
        route is optimal; completion 15.0 per batch, objective 30.0.
    """
    return {
        "N": {"O1", "O2"},
        "P": {"P1", "P2"},
        "B": {"B1", "B2"},
        "V": {"L1", "L2", "L3", "L4", "L5"},
        "E": {("L1", "L2"), ("L1", "L3"), ("L1", "L4"), ("L2", "L4"), ("L3", "L4"), ("L4", "L5")},
        "depot": "L1",
        "final": "L5",
        "D_ij": {
            ("L1", "L2"): 5.0, ("L1", "L3"): 5.0, ("L1", "L4"): 3.0,
            ("L2", "L4"): 5.0, ("L3", "L4"): 5.0, ("L4", "L5"): 5.0,
        },
        "S_i": {v: 0.0 for v in ("L1", "L2", "L3", "L4", "L5")},
        "A_ni": {
            (order, location): int(location == "L4")
            for order in ("O1", "O2") for location in ("L1", "L2", "L3", "L4", "L5")
        },
        "B_nb": {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1},
        "C_n": {"O1": 3.0, "O2": 3.0},
        "T_due_n": {"O1": due_date, "O2": due_date},
        "W_c": 1.0,
        "W_pen": 10.0,
        "W_e": 1.0,
        "W_t": 5.0,
        "T_travel": 0.5,
        "T_setup": 1.0,
        "T_pick": 1.0,
        "C_v": 5.0,
        "M": 10000.0,
        "V_p": {"P1": 1.0, "P2": 1.0},
        "T_cold": 1_000_000_000.0,
    }


def two_dead_end_aisles():
    """A central hub H with two dead-end aisles, L1 and L2, one order in each.

    Any walk that picks both has to pass through H three times
    (D -> H -> L1 -> H -> L2 -> H -> F). The routing constraints allow at
    most one arc into and one out of each vertex, so the model has no
    feasible route, even though a picker could walk it.
    """
    return {
        "N": {"O1", "O2"},
        "P": {"P1"},
        "B": {"B1"},
        "V": {"D", "H", "L1", "L2", "F"},
        "E": {("D", "H"), ("H", "L1"), ("L1", "H"), ("H", "L2"), ("L2", "H"), ("H", "F")},
        "depot": "D",
        "final": "F",
        "D_ij": {("D", "H"): 1.0, ("H", "L1"): 1.0, ("L1", "H"): 1.0,
                 ("H", "L2"): 1.0, ("L2", "H"): 1.0, ("H", "F"): 1.0},
        "S_i": {"D": 0.0, "H": 0.0, "L1": 0.0, "L2": 0.0, "F": 0.0},
        "A_ni": {
            (order, location): int((order, location) in {("O1", "L1"), ("O2", "L2")})
            for order in ("O1", "O2") for location in ("D", "H", "L1", "L2", "F")
        },
        "B_nb": {("O1", "B1"): 1, ("O2", "B1"): 1},
        "C_n": {"O1": 1.0, "O2": 1.0},
        "T_due_n": {"O1": 100.0, "O2": 100.0},
        "W_c": 1.0,
        "W_pen": 0.0,
        "W_e": 1.0,
        "W_t": 1.0,
        "T_travel": 1.0,
        "T_setup": 1.0,
        "T_pick": 1.0,
        "C_v": 10.0,
        "M": 10000.0,
        "V_p": {"P1": 1.0},
        "T_cold": 100.0,
    }
