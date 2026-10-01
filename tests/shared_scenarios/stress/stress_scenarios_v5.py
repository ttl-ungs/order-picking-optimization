"""OPP v5 data builders preserving the sizes of the OPP v4 stress suite."""

from tests.shared_scenarios.stress.scenario_custom_setup_v4 import scenario_custom_setup


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
        "D_ij": distances,
        "S_i": {vertex: 0.0 for vertex in vertices},
        "A_ni": a_ni,
        "B_nb": bn,
        "C_n": {order: 10.0 for order in order_set},
        "T_due_n": {order: 30.0 for order in order_set},
        "W_c": 9.0,
        "W_pen": 1.0,
        "W_e": 1.0,
        "W_t": 1.0,
        "T_travel": 0.5,
        "T_setup": 1.0,
        "T_pick": 1.0,
        "C_v": 250.0,
        "M": 10000.0,
        # Baseline migration settings: same picker behavior as OPP v4.
        "V_p": {picker: 1.0 for picker in picker_set},
        "T_cold": 1_000_000_000.0,
    }
