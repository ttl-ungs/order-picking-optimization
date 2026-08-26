"""OPP v5 data builders preserving the sizes of the OPP v4 stress suite."""

from tests.opp_v4.scenarios.stress.scenario_custom_setup import scenario_custom_setup


def migrated_stress_scenario(batches, pickers, orders, rows, cols):
    graph, vertices, batch_set, picker_set, order_set, _x, bn, a_ni = scenario_custom_setup(
        batches, pickers, orders, rows, cols
    )
    edges = set()
    distances = {}
    for origin in graph.get_vertices():
        for destination in graph.get_vertices():
            if graph.has_edge(origin, destination):
                edges.add((origin, destination))
                distances[(origin, destination)] = graph.get_distance(origin, destination)

    return {
        "N": order_set,
        "P": picker_set,
        "B": batch_set,
        "V": set(vertices),
        "E": edges,
        "depot": graph.get_depot(),
        "final": graph.get_final(),
        "d_ij": distances,
        "S_i": {vertex: 0.0 for vertex in vertices},
        "A_ni": a_ni,
        "Bn": bn,
        "C_n": {order: 10.0 for order in order_set},
        "Dd": {order: 30.0 for order in order_set},
        "W_full": 9.0,
        "W_ea_ta": 1.0,
        "W_ea": 1.0,
        "W_ta": 1.0,
        "B_time": 0.5,
        "B_setup": 1.0,
        "B_picking": 1.0,
        "C_v": 250.0,
        "M": 10000.0,
        # Baseline migration settings: same picker behavior as OPP v4.
        "V_p": {picker: 1.0 for picker in picker_set},
        "T_frio_max": 1_000_000_000.0,
    }
