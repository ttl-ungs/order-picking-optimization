from models.base.opp_location_graph import OPPLocationGraph


def _add_grid(
    graph, prefix, rows, cols, v_weight, h_weight, depot_id=None, final_id=None
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


def multigrid_5x5_3x3_five_pickers_twelve_batches(
    connect=True,
    v_weight=2,
    h_weight=3,
    connector_weight=2,
):
    P = {f"P{i}" for i in range(1, 6)}
    B = {f"B{i}" for i in range(1, 13)}

    x = {(p, b): 0 for p in P for b in B}
    sorted_pickers = sorted(P)
    for i, b in enumerate(sorted(B)):
        x[(sorted_pickers[i % len(sorted_pickers)], b)] = 1

    graph = OPPLocationGraph("A1", "B9")

    _add_grid(
        graph,
        prefix="A",
        rows=5,
        cols=5,
        v_weight=v_weight,
        h_weight=h_weight,
        depot_id="A1",
        final_id=None,
    )
    _add_grid(
        graph,
        prefix="B",
        rows=3,
        cols=3,
        v_weight=v_weight,
        h_weight=h_weight,
        depot_id=None,
        final_id="B9",
    )

    if connect:
        connectors = [("A13", "B1"), ("A23", "B7")]
        for left, right in connectors:
            graph.add_edge(left, right, connector_weight)
            graph.add_edge(right, left, connector_weight)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    cap_vehicle = 10.0

    return graph.get_vertices(), P, B, w1, w2, gamma, delta, graph, cap_vehicle, x
