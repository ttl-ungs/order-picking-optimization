"""
Pre-solve input validation shared by the four models.

The ZIMPL models take the batch composition (B_nb) as a parameter, so the
solver cannot reject "an order belongs to exactly one batch" or "the batch
fits in the vehicle" by itself. These checks do it in Python before ZIMPL
runs, so that the exact models and the heuristics give the same answer on an
invalid input.
"""


def overloaded_batches(C_n: dict, B_nb: dict, C_v: float, tolerance: float = 1e-9) -> set:
    """
    Batches whose load (the sum of C_n over their orders) exceeds the vehicle
    capacity C_v. Empty when every batch fits.
    """
    if not C_n or not B_nb or C_v is None:
        return set()

    load_by_batch = {}
    for (n, b), assigned in B_nb.items():
        if not assigned:
            continue
        if n not in C_n:
            # A missing capacity must not count as zero load: that would
            # hide exactly the overloaded batches this check exists to catch.
            raise ValueError(
                f"overloaded_batches: order {n!r} is assigned to batch {b!r} via B_nb "
                f"but has no entry in C_n -- can't validate vehicle capacity without "
                f"a real capacity value for it."
            )
        load_by_batch[b] = load_by_batch.get(b, 0.0) + C_n[n]

    return {b for b, load in load_by_batch.items() if load > C_v + tolerance}


def orders_without_exactly_one_batch(B_nb: dict, N, tolerance: float = 1e-9) -> set:
    """
    Orders of N that are not in exactly one batch (sum_b B_nb[(n, b)] != 1):
    left out, or assigned to two or more batches.
    """
    if not N:
        return set()

    # Every order starts at 0, so with an empty B_nb all of them are reported
    # as unassigned.
    assignment_count = {n: 0.0 for n in N}
    if B_nb:
        for (n, _b), assigned in B_nb.items():
            if n in assignment_count:
                assignment_count[n] += assigned

    return {n for n, count in assignment_count.items() if abs(count - 1.0) > tolerance}
