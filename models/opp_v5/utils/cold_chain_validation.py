"""
Pre-solve input validation for opp_v5's Etapa 2 (stage2_scheduling.zpl).
Bug: stage2_scheduling.zpl restricts X_pb's domain to PB_elig = {(p,b) : t_exec_pb[p,b] <= T_frio_max},
so that`assign_exactly_one_picker` becomes a sum over an EMPTY set for that batch, and ZIMPL rejects that at
COMPILE time.
This mirrors models/utils/input_validation.py's role for opp_v4.
"""


def batches_without_eligible_picker(
    P, B, N, C_n: dict, Bn: dict, B_setup: float, B_picking: float,
    R_b_time: dict, V_p: dict, T_frio_max: float,
) -> set:
    """
    Returns the set of batch ids in B that have zero (picker, batch) pair satisfying t_exec_pb <= T_frio_max
    Replicates stage2_scheduling.zpl's PB_elig/B_sin_picker_elegible computation exactly
    (same tiempo_fijo/t_exec_pb formula), so solve_v5_stage2 can short-circuit to a clean "infeasible" before
    invoking ZIMPL for these.
    Empty result means every batch has at least one eligible picker.
    """
    if not B or not P:
        return set(B) if B else set()

    fixed_time = {}
    for b in B:
        orders_in_b = {n for n in N if Bn.get((n, b), 0)}
        fixed_time[b] = B_setup + B_picking * sum(C_n.get(n, 0.0) for n in orders_in_b)

    without_picker = set()
    for b in B:
        if b not in R_b_time:
            # Stage 1 never exported a route time for this batch.
            without_picker.add(b)
            continue
        has_eligible = any(
            fixed_time[b] + R_b_time[b] / V_p[p] <= T_frio_max
            for p in P
        )
        if not has_eligible:
            without_picker.add(b)

    return without_picker
