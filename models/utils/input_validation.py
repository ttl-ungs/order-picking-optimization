"""
Pre-solve input validation for opp_v4.

opp_model_v4.zpl takes the batch assignment (Bn) and batch composition as
fixed *parameters*, not decision variables -- unlike opp_v2/opp_v3 (where
"order n belongs to exactly one batch" and "the batch fits the vehicle" were
constraints on decision variables and infeasible input was rejected by the
solver).
These checks re-add, in Python before ZIMPL/SCIP ever runs, the two
input-validity conditions opp_hc_2/opp_aco_2/opp_hc_3/opp_aco_3 still reject
as infeasible for the same instance, so the "same constraints" equivalence
claimed by every model's README actually holds for opp_v4 too.
"""


def overloaded_batches(C_n: dict, Bn: dict, C_v: float, tolerance: float = 1e-9) -> set:
    """
    Returns the set of batch ids whose total required capacity (sum of
    C_n[n] over every order n assigned to that batch via Bn[(n, b)] == 1)
    exceeds the vehicle capacity C_v. Empty set means every batch fits.
    """
    if not C_n or not Bn or C_v is None:
        return set()

    load_by_batch = {}
    for (n, b), assigned in Bn.items():
        if not assigned:
            continue
        load_by_batch[b] = load_by_batch.get(b, 0.0) + C_n.get(n, 0.0)

    return {b for b, load in load_by_batch.items() if load > C_v + tolerance}


def orders_without_exactly_one_batch(Bn: dict, N, tolerance: float = 1e-9) -> set:
    """
    Returns the set of orders n in N whose assignment across batches
    (sum_b Bn[(n, b)]) is not exactly 1 -- i.e. left unassigned, or assigned
    to two or more batches at once. Mirrors the "sum_b y[n,b] == 1"
    constraint opp_v2/opp_v3/opp_hc_2/opp_aco_2 enforce on the batch
    assignment decision variable.
    """
    if not Bn or not N:
        return set()

    assignment_count = {n: 0.0 for n in N}
    for (n, _b), assigned in Bn.items():
        if n in assignment_count:
            assignment_count[n] += assigned

    return {n for n, count in assignment_count.items() if abs(count - 1.0) > tolerance}
