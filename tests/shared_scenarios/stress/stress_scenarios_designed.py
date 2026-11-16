"""Stress scenarios designed to exercise what the models decide, instead of plain grids.

`grid_stress_scenario` builds plain grids of a given size, but it carries five properties that inflate difficulty
without modelling anything a warehouse does:

1. `|P| >= |B|` in six of the eight scenarios. Every batch goes to exactly one
   picker, so at most `|B|` pickers are ever used; when `|P| == |B|` each batch
   takes its own and NO non-overlap constraint binds, leaving Stage 2 as a plain
   assignment problem. Sequencing -- the reason Stage 2 exists -- is exercised by
   two of the eight.
2. Due dates fixed at 30 while a batch's fixed time alone is 101 plus 64-72 of
   routing, so every order is late (`sla_on_time_pct = 0.0`) and the earliness
   half of the objective never activates.
3. Every `V_p = 1.0`, so no stress scenario exercises the picker speeds.
4. Order weights of 10.0 make `F_b` (101) outweigh the route (64-72),
   so improving the routing barely moves the objective.
5. Orders map to locations by `sorted_locations[i % len(V)]` and to batches by
   the same index, so a batch's locations come out striped across the grid at a
   spacing set by the batch COUNT -- changing `|B|` changes each batch's
   geometry, not just the instance size.

These builders avoid all five. They also stress the two stages on separate axes,
which is what makes them useful for comparing the split against the monolithic
model: orders and grid size drive Stage 1's routing, while the batches-per-picker
ratio drives Stage 2's sequencing. Loading the routing axis heavily while keeping
batches inside the solvable band is precisely where a decomposed Stage 1 should
pull ahead of a formulation that has to solve routing and scheduling at once.
"""

import random

from tests.infra.factories.graphs_factory import GraphsFactory

_SEED = 20260922


def _picker_speeds(picker_ids, spread, tiers):
    """Assign V_p across pickers, either in tiers or all distinct.

    A real crew is not a continuum of speeds: people are hired from a similar
    pool and all push the same carts, so there are a few bands rather than one
    value per person. That distinction matters to the solver, not just to
    realism -- pickers sharing a speed stay interchangeable, so the symmetry
    that makes assignments permutable is only partly broken. `tiers=None`
    reproduces the all-distinct case, which is the hardest a crew could be.
    """
    if not spread or len(picker_ids) < 2:
        return {picker: 1.0 for picker in picker_ids}

    if tiers is None:
        return {
            picker: 1.0 - spread + 2 * spread * i / (len(picker_ids) - 1)
            for i, picker in enumerate(picker_ids)
        }

    tiers = max(1, min(tiers, len(picker_ids)))
    if tiers == 1:
        return {picker: 1.0 for picker in picker_ids}
    bands = [1.0 - spread + 2 * spread * t / (tiers - 1) for t in range(tiers)]
    return {picker: bands[i % tiers] for i, picker in enumerate(picker_ids)}


ORDERS_PER_BATCH = 26


def realistic_crew_scenario(rows, cols=None, batches=6, pickers=3, t_cold=None):
    """The calibrated stress profile: a realistic crew on a warehouse grid.

    26 orders per batch (on-time share ~67%, so earliness and tardiness both
    act), aisles slightly longer than cross-aisles (4/5) and two speed bands
    (0.8, 1.2). The default crew is 6 batches over 3 pickers -- two batches per
    picker, so sequencing binds; with realistic speeds, more than two per
    picker did not solve. `cols` defaults to a square grid. `t_cold`
    enables the cold-chain limit, which every other stress scenario leaves off.

    Split timings with the default crew (sequential, machine alone): 7x7 2.0 min,
    13x13 5.9 min, 15x15 28.5 min.
    """
    scenario = designed_stress_scenario(
        batches, pickers, batches * ORDERS_PER_BATCH, rows, cols or rows,
        speed_spread=0.2, speed_tiers=2,
        vertical_weight=4, horizontal_weight=5,
    )
    if t_cold is not None:
        scenario["T_cold"] = t_cold
    return scenario


def designed_stress_scenario(
    batches,
    pickers,
    orders,
    rows,
    cols,
    order_weight=5.0,
    speed_spread=0.0,
    speed_tiers=None,
    vertical_weight=4,
    horizontal_weight=4,
):
    """Build a stress scenario free of the degeneracies listed in the module docstring.

    Args:
        batches: number of batches. Keep it above `pickers` so sequencing binds.
        pickers: number of pickers.
        orders: number of orders; must be >= batches so no batch comes out empty.
        rows, cols: grid dimensions.
        order_weight: each order's `C_n`. Drives `F_b` against the route
            time -- raise it to make picking dominate, lower it to make routing
            dominate. Worth calibrating per size, since the route's share depends
            on the grid.
        speed_spread: 0.0 gives every picker `V_p = 1.0`; otherwise speeds span
            `[1 - spread, 1 + spread]`.
        speed_tiers: how many distinct speeds to spread over the crew. None
            gives every picker its own, which is the hardest case for the
            solver but not what a warehouse looks like -- a real crew falls
            into two or three bands. Pickers sharing a band stay
            interchangeable, so the assignment symmetry is only partly broken.
        vertical_weight, horizontal_weight: grid edge costs. Equal values leave
            many routes tied in cost; different ones break those ties.

    Returns:
        The scenario dict the .dat builders expect.
    """
    if orders < batches:
        raise ValueError(f"orders ({orders}) < batches ({batches}) would leave empty batches")

    graph, vertices = GraphsFactory().get_graph(rows, cols, vertical_weight, horizontal_weight)
    vertices = sorted(vertices)
    depot, final = graph.get_depot(), graph.get_final()

    edges, distances = set(), {}
    for origin in vertices:
        for neighbor in graph.get_neighbors(origin):
            edges.add((origin, neighbor))
            distances[(origin, neighbor)] = graph.get_distance(origin, neighbor)

    batch_ids = [f"B{i}" for i in range(1, batches + 1)]
    picker_ids = [f"P{i}" for i in range(1, pickers + 1)]
    order_ids = [f"O{i}" for i in range(1, orders + 1)]

    # Round-robin keeps every batch non-empty and the sizes within one order of
    # each other; locations are drawn at random (seeded) rather than from the
    # order's index, so a batch's geometry does not shift when `batches` changes.
    rng = random.Random(_SEED)
    pickable = [v for v in vertices if v not in (depot, final)]

    bn = {(order, batch): 0 for order in order_ids for batch in batch_ids}
    a_ni = {(order, vertex): 0 for order in order_ids for vertex in vertices}
    for index, order in enumerate(order_ids):
        bn[(order, batch_ids[index % batches])] = 1
        a_ni[(order, rng.choice(pickable))] = 1

    speeds = _picker_speeds(picker_ids, speed_spread, speed_tiers)

    beta_setup, beta_picking, beta_time = 1.0, 1.0, 0.5
    orders_per_batch = orders / batches
    fixed_time = beta_setup + beta_picking * orders_per_batch * order_weight
    # Rough stand-in for a batch's route: its locations, each about an average
    # grid hop apart. Only used to place due dates on the right scale.
    mean_hop = (vertical_weight * rows + horizontal_weight * cols) / 3.0
    route_estimate = beta_time * mean_hop * orders_per_batch
    per_batch = fixed_time + route_estimate / min(speeds.values())
    makespan = per_batch * max(1.0, batches / pickers)

    # Fan due dates across the makespan so some orders finish early and others
    # late; a single value for all of them leaves one half of the objective dead.
    due_dates = {
        order: round(makespan * (0.6 + 0.8 * i / max(1, orders - 1)), 2)
        for i, order in enumerate(order_ids)
    }

    # W_c must exceed the largest batch's order count (times W_pen * W_e,
    # both 1 here), or the Split gains by voluntary waiting: c_pb >= T_exec_pb lets it
    # report a batch LATER than it physically finishes, and a delay of d costs
    # W_c * d while cutting earliness by up to (orders in the batch) * d.
    # With W_c = 9 and 26 orders per batch a delay paid ~17 per unit, so the
    # Split's optimum waited and no heuristic -- which reports real completion
    # times -- could match it. Above the bound a delay never pays and earliness
    # still counts in the objective.
    w_ea_ta, w_ea = 1.0, 1.0
    max_orders_per_batch = -(-orders // batches)  # round-robin: ceil(orders / batches)
    w_full = max_orders_per_batch * w_ea_ta * w_ea + 1.0

    return {
        "N": set(order_ids),
        "P": set(picker_ids),
        "B": set(batch_ids),
        "V": set(vertices),
        "E": edges,
        "depot": depot,
        "final": final,
        "D_ij": distances,
        "S_i": {vertex: 0.0 for vertex in vertices},
        "A_ni": a_ni,
        "B_nb": bn,
        "C_n": {order: order_weight for order in order_ids},
        "T_due_n": due_dates,
        "W_c": w_full,
        "W_pen": w_ea_ta,
        "W_e": w_ea,
        "W_t": 1.0,
        "T_travel": beta_time,
        "T_setup": beta_setup,
        "T_pick": beta_picking,
        # Room for a full batch plus margin, so capacity never becomes the
        # binding constraint -- these scenarios are about routing and sequencing.
        "C_v": order_weight * orders_per_batch * 1.5,
        "M": 1_000_000.0,
        "V_p": speeds,
        "T_cold": 1_000_000_000.0,
    }
