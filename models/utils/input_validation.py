"""
Pre-solve input validation shared by the four models.

The ZIMPL models (opp_mono, opp_split) take the batch assignment (B_nb) and
batch composition as fixed *parameters*, not decision variables, so the solver
cannot reject "order n belongs to exactly one batch" or "the batch fits the
vehicle" by itself.
These checks reject, in Python before ZIMPL/SCIP ever runs, the two
input-validity conditions that opp_hc and opp_aco also reject as infeasible
for the same instance, so every model gives the same answer on an invalid
input.
"""


def overloaded_batches(C_n: dict, B_nb: dict, C_v: float, tolerance: float = 1e-9) -> set:
    """
    Returns the set of batch ids whose total required capacity (sum of
    C_n[n] over every order n assigned to that batch via B_nb[(n, b)] == 1)
    exceeds the vehicle capacity C_v. Empty set means every batch fits.
    """
    if not C_n or not B_nb or C_v is None:
        return set()

    load_by_batch = {}
    for (n, b), assigned in B_nb.items():
        if not assigned:
            continue
        if n not in C_n:
            # Fix (2026-08-28, code audit): used to silently fall back to
            # C_n.get(n, 0.0), so an order missing from C_n contributed
            # ZERO load -- exactly backwards for a validator whose whole
            # job is to catch batches that are too heavy. Missing capacity
            # data for an order that IS assigned via B_nb is itself a data
            # problem the caller needs to know about, not something this
            # check should paper over.
            raise ValueError(
                f"overloaded_batches: order {n!r} is assigned to batch {b!r} via B_nb "
                f"but has no entry in C_n -- can't validate vehicle capacity without "
                f"a real capacity value for it."
            )
        load_by_batch[b] = load_by_batch.get(b, 0.0) + C_n[n]

    return {b for b, load in load_by_batch.items() if load > C_v + tolerance}


def orders_without_exactly_one_batch(B_nb: dict, N, tolerance: float = 1e-9) -> set:
    """
    Returns the set of orders n in N whose assignment across batches
    (sum_b B_nb[(n, b)]) is not exactly 1 -- i.e. left unassigned, or assigned
    to two or more batches at once. Mirrors the "sum_b y[n,b] == 1"
    constraint the heuristics enforce on the batch
    assignment.
    """
    if not N:
        return set()

    # Fix (2026-08-28, code audit): used to be `if not B_nb or not N: return
    # set()` -- an EMPTY B_nb with a non-empty N means every order in N is
    # unassigned, exactly the condition this function exists to catch, but
    # the old short-circuit silently reported "nothing wrong" instead.
    # Every order starts at count 0 regardless of whether B_nb has any
    # entries at all; only bump the count for entries that are actually
    # there.
    assignment_count = {n: 0.0 for n in N}
    if B_nb:
        for (n, _b), assigned in B_nb.items():
            if n in assignment_count:
                assignment_count[n] += assigned

    return {n for n, count in assignment_count.items() if abs(count - 1.0) > tolerance}
