"""
Pre-solve input validation for opp_v5_2_split's Etapa 2 (opp_model_v5_2_split_stage2_scheduling.zpl).
Bug: opp_model_v5_2_split_stage2_scheduling.zpl restricts x_pb's domain to PB_elig = {(p,b) : t_exec_pb[p,b] <= T_frio_max},
so that`assign_exactly_one_picker` becomes a sum over an EMPTY set for that batch, and ZIMPL rejects that at
COMPILE time.
This mirrors models/utils/input_validation.py's role for opp_v4.

Shared by opp_v5_2_split's own pre-solve pipeline, opp_hc_4 and opp_aco_4 (all
three compute t_exec_pb = fixed_time(b) + route_time(b) / V_p[p]).
"""

# Same tolerance opp_hc_4/opp_aco_4's own eligibility checks use
# (t_exec_pb <= T_frio_max + 1e-9) -- kept in sync here so this shared
# check can't be stricter than what those models actually enforce, which
# would make it possible for a picker they'd accept to be reported as
# ineligible by batches_without_eligible_picker (2026-09-10 audit finding:
# opp_model_v5_2_split_stage2_scheduling.zpl's PB_elig used a bare <=, with no epsilon at all).
COLD_CHAIN_TOLERANCE = 1e-9


def invalid_speeds(V_p: dict) -> set:
    """
    Picker ids whose speed is not strictly positive. V_p[p] is a divisor
    in t_exec_pb = fixed_time(b) + route_time(b) / V_p[p]: a speed of
    exactly 0 means a division by zero (undefined -- ZeroDivisionError in
    Python, and ZIMPL has no graceful "infeasible" for it either, since
    t_exec_pb is a plain parameter expression evaluated at model-read
    time, not a constraint SCIP could reason about); a negative speed
    silently produces a NEGATIVE t_exec_pb, which would then look
    "eligible" for any T_frio_max, including ones that make no physical
    sense (2026-09-10 audit finding -- nothing anywhere validated this).
    Callers should treat a non-empty result the same way they'd treat
    malformed input in general (report infeasible / reject cleanly,
    mirroring how a missing `Bn` is already handled), not let the
    division happen at all.
    """
    return {p for p, speed in V_p.items() if speed is None or speed <= 0}


def batches_without_eligible_picker(
    P, B, N, C_n: dict, Bn: dict, B_setup: float, B_picking: float,
    R_b: dict, V_p: dict, T_frio_max: float,
) -> set:
    """
    Returns the set of batch ids in B that have zero (picker, batch) pair satisfying t_exec_pb <= T_frio_max
    Replicates opp_model_v5_2_split_stage2_scheduling.zpl's PB_elig/B_sin_picker_elegible computation exactly
    (same tiempo_fijo/t_exec_pb formula, including its +1e-9 tolerance -- see COLD_CHAIN_TOLERANCE), so
    solve_v5_stage2 can short-circuit to a clean "infeasible" before invoking ZIMPL for these.
    Empty result means every batch has at least one eligible picker.

    Callers are expected to have already rejected any picker with
    invalid_speeds(V_p) non-empty -- a picker with V_p[p] <= 0 is treated
    here as simply never eligible (skipped, not divided by), so this
    function itself never raises, but that is a fallback, not a
    substitute for checking invalid_speeds() up front.
    """
    if not B or not P:
        return set(B) if B else set()

    fixed_time = {}
    for b in B:
        orders_in_b = {n for n in N if Bn.get((n, b), 0)}
        fixed_time[b] = B_setup + B_picking * sum(C_n.get(n, 0.0) for n in orders_in_b)

    without_picker = set()
    for b in B:
        if b not in R_b:
            # Stage 1 never exported a route time for this batch.
            without_picker.add(b)
            continue
        has_eligible = any(
            fixed_time[b] + R_b[b] / V_p[p] <= T_frio_max + COLD_CHAIN_TOLERANCE
            for p in P
            if V_p.get(p, 0.0) > 0
        )
        if not has_eligible:
            without_picker.add(b)

    return without_picker
