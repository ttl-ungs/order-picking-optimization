"""Small scenarios adapted from the normal OPP v4 routing cases."""


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
        "d_ij": {
            ("D", "A"): 2.0, ("A", "F"): 2.0,
            ("D", "B"): 6.0, ("B", "F"): 6.0,
            ("D", "F"): 30.0, ("A", "B"): 20.0,
        },
        "S_i": {"D": 0.0, "A": 1.0, "B": 2.0, "F": 0.0},
        "A_ni": {
            ("O1", "D"): 0, ("O1", "A"): 1, ("O1", "B"): 0, ("O1", "F"): 0,
            ("O2", "D"): 0, ("O2", "A"): 0, ("O2", "B"): 1, ("O2", "F"): 0,
        },
        "Bn": {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1},
        "C_n": {"O1": 1.0, "O2": 1.0},
        "Dd": {"O1": 100.0, "O2": 100.0},
        "W_full": 1.0,
        "W_ea_ta": 0.0,
        "W_ea": 1.0,
        "W_ta": 1.0,
        "B_time": 1.0,
        "B_setup": 1.0,
        "B_picking": 1.0,
        "C_v": 10.0,
        "M": 10000.0,
        "V_p": {"P_slow": 1.0, "P_fast": 2.0},
        "T_frio_max": 100.0,
    }


def one_cold_batch(cold_limit=10.0):
    """A batch which only the fast picker can prepare under the cold limit."""
    data = two_batches_two_routes()
    data.update(
        N={"O1"},
        B={"B1"},
        V={"D", "B", "F"},
        E={("D", "B"), ("B", "F"), ("D", "F")},
        d_ij={("D", "B"): 6.0, ("B", "F"): 6.0, ("D", "F"): 30.0},
        S_i={"D": 0.0, "B": 2.0, "F": 0.0},
        A_ni={("O1", "D"): 0, ("O1", "B"): 1, ("O1", "F"): 0},
        Bn={("O1", "B1"): 1},
        C_n={"O1": 1.0},
        Dd={"O1": 100.0},
        T_frio_max=cold_limit,
    )
    return data


# The three scenarios below reuse one_cold_batch's fixed geometry (route B1
# costs R_b_time=14.0 -- distance 6+6=12 at B_time=1.0, plus S_i["B"]=2.0 --
# and tiempo_fijo=B_setup+B_picking*C_n["O1"]=1.0+1.0*1.0=2.0), so
# t_exec_pb(P_fast, B1) = 2.0 + 14.0/2.0 = 9.0 exactly and
# t_exec_pb(P_slow, B1) = 2.0 + 14.0/1.0 = 16.0 exactly -- precise enough to
# assert on, not just "which picker got it".

def cold_chain_exact_boundary():
    """T_frio_max set to EXACTLY P_fast's t_exec_pb (9.0) -- PB_elig uses
    `<=`, so this must still be eligible, not excluded by an off-by-one on
    the boundary."""
    return one_cold_batch(cold_limit=9.0)


def cold_chain_infeasible_for_every_picker():
    """T_frio_max below even the fastest picker's t_exec_pb (9.0) -- no
    (picker, batch) pair is ever eligible, so PB_elig is empty for B1 and
    `assign_exactly_one_picker` (sum over an empty set == 1) can never
    hold: the model must come back genuinely infeasible, not just "no
    picker found" from the Python-side preflight check."""
    return one_cold_batch(cold_limit=5.0)


def heterogeneous_speed_precise():
    """Same two-batch, two-speed setup already used for the assignment-
    direction test, kept here to assert the exact completion-time formula:
    t_exec_pb = tiempo_fijo + R_b_time / V_p -- i.e. that ONLY the route
    portion is scaled by picker speed, never the fixed setup/picking time.
    With V_p={P_slow: 1.0, P_fast: 2.0}, R_b_time={B1: 5.0, B2: 14.0} and
    tiempo_fijo=2.0 for both batches (B_setup=1.0, B_picking=1.0,
    C_n={"O1": 1.0, "O2": 1.0}):
        t_exec_pb(P_slow, B1) = 2.0 + 5.0/1.0  =  7.0
        t_exec_pb(P_fast, B2) = 2.0 + 14.0/2.0 =  9.0
    which is also the cost-minimizing assignment (7.0+9.0=16.0, cheaper
    than the 20.5 the reversed assignment would cost)."""
    return two_batches_two_routes()
