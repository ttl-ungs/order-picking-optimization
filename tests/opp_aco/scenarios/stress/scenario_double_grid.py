from models.base.opp_location_graph import OPPLocationGraph


def _add_grid(
    graph,
    prefix,
    rows,
    cols,
    v_weight,
    h_weight,
    depot_id=None,
    final_id=None,
):
    def vid(r, c):
        return f"{prefix}{(c - 1) * rows + r}"

    for col in range(1, cols + 1):
        for row in range(1, rows + 1):
            v = vid(row, col)
            if v == depot_id:
                graph.add_vertex(v, "depot")
            elif v == final_id:
                graph.add_vertex(v, "final")
            else:
                graph.add_vertex(v, "picking")

    for col in range(1, cols + 1):
        for row in range(1, rows):
            a, b = vid(row, col), vid(row + 1, col)
            graph.add_edge(a, b, v_weight)
            graph.add_edge(b, a, v_weight)

    for row in range(1, rows + 1):
        for col in range(1, cols):
            a, b = vid(row, col), vid(row, col + 1)
            graph.add_edge(a, b, h_weight)
            graph.add_edge(b, a, h_weight)


def scenario_two_grids_custom_setup(
    batches,
    orders,
    rows=50,
    cols=50,
    connectors=10,
    v_weight=4,
    h_weight=4,
    connector_weight=4,
):
    total = rows * cols
    B = {f"B{b}" for b in range(1, batches + 1)}
    N = {f"O{o}" for o in range(1, orders + 1)}

    graph = OPPLocationGraph("A1", f"B{total}")

    _add_grid(
        graph,
        prefix="A",
        rows=rows,
        cols=cols,
        v_weight=v_weight,
        h_weight=h_weight,
        depot_id="A1",
        final_id=None,
    )
    _add_grid(
        graph,
        prefix="B",
        rows=rows,
        cols=cols,
        v_weight=v_weight,
        h_weight=h_weight,
        depot_id=None,
        final_id=f"B{total}",
    )

    step = max(1, total // connectors)
    for k in range(connectors):
        idx = 1 + (k * step)
        if idx > total:
            idx = total - (connectors - 1 - k)
        left = f"A{idx}"
        right = f"B{idx}"
        graph.add_edge(left, right, connector_weight)
        graph.add_edge(right, left, connector_weight)

    V = graph.get_vertices()

    y = {(o, b): 0 for o in N for b in B}
    sorted_batches = sorted(B)
    for i, o in enumerate(sorted(N)):
        y[(o, sorted_batches[i % len(sorted_batches)])] = 1

    depot = graph.get_depot()
    final = graph.get_final()
    candidate_locations = [v for v in sorted(V) if v not in {depot, final}]
    if not candidate_locations:
        candidate_locations = sorted(V)

    a = {(n, v): 0 for n in N for v in V}
    for i, o in enumerate(sorted(N)):
        a[(o, candidate_locations[i % len(candidate_locations)])] = 1

    return graph, V, B, N, y, a
