from tests.support.graphs_factory import GraphsFactory

def scenario_custom_setup(
    batches,
    orders,
    rows=4,
    cols=4,
    v_weight=4,
    h_weight=4,
):
    B = {f"B{b}" for b in range(1, batches + 1)}
    N = {f"O{o}" for o in range(1, orders + 1)}

    y = {(o, b): 0 for o in N for b in B}
    sorted_batches = sorted(B)
    for i, o in enumerate(sorted(N)):
        y[(o, sorted_batches[i % len(sorted_batches)])] = 1

    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(rows, cols, v_weight, h_weight)

    depot = opp_location_graph.get_depot()
    final = opp_location_graph.get_final()
    candidate_locations = [v for v in sorted(V) if v not in {depot, final}]
    if not candidate_locations:
        candidate_locations = sorted(V)

    a = {(n, v): 0 for n in N for v in V}
    for i, o in enumerate(sorted(N)):
        a[(o, candidate_locations[i % len(candidate_locations)])] = 1

    return opp_location_graph, V, B, N, y, a
