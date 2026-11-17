"""
Pre-solve validation of the picker speeds and the cold chain, shared by every
model (all of them use T_exec_pb = fixed_time(b) + route_time(b) / V_p[p]).

OPP-Split's Stage 2 restricts x_pb to PB_elig = {(p, b) : T_exec_pb[p, b] <=
T_cold}. For a batch with no eligible picker, assign_exactly_one_picker is a
sum over an empty set, which ZIMPL rejects when it compiles the model; these
checks report such an instance as infeasible before solving.
"""

# Tolerance of every cold-chain comparison (T_exec_pb <= T_cold + 1e-9), here,
# in the heuristics and in the ZIMPL models (EPS), so a batch with T_exec_pb
# equal to T_cold up to rounding is eligible in all of them.
COLD_CHAIN_TOLERANCE = 1e-9


def invalid_speeds(V_p: dict) -> set:
    """
    Pickers whose speed is not strictly positive. V_p[p] divides in T_exec_pb:
    a speed of 0 is a division by zero, and a negative one gives a negative
    T_exec_pb that would look eligible for any T_cold. Callers reject the
    instance when the result is not empty.
    """
    return {p for p, speed in V_p.items() if speed is None or speed <= 0}


def batches_without_eligible_picker(
    P, B, N, C_n: dict, B_nb: dict, T_setup: float, T_pick: float,
    R_b: dict, V_p: dict, T_cold: float,
) -> set:
    """
    Batches of B with no picker p such that T_exec_pb[p, b] <= T_cold: the
    set B_no_eligible_picker of opp_split_stage2_scheduling.zpl, with the same
    formula and tolerance. Empty when every batch has an eligible picker.

    A picker with V_p[p] <= 0 is never eligible here; callers are expected to
    have checked invalid_speeds() first.
    """
    if not B or not P:
        return set(B) if B else set()

    fixed_time = {}
    for b in B:
        orders_in_b = {n for n in N if B_nb.get((n, b), 0)}
        fixed_time[b] = T_setup + T_pick * sum(C_n.get(n, 0.0) for n in orders_in_b)

    without_picker = set()
    for b in B:
        if b not in R_b:
            # No route time for this batch (Stage 1 did not produce one).
            without_picker.add(b)
            continue
        has_eligible = any(
            fixed_time[b] + R_b[b] / V_p[p] <= T_cold + COLD_CHAIN_TOLERANCE
            for p in P
            if V_p.get(p, 0.0) > 0
        )
        if not has_eligible:
            without_picker.add(b)

    return without_picker
