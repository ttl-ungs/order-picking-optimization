from graphs.graphs_factory import GraphsFactory


def scenario_custom_setup(
        batches, pickers, orders, rows=4, cols=4, v_weight=4, h_weight=4
):
    B = {f"B{b}" for b in range(1, batches + 1)}
    P = {f"P{p}" for p in range(1, pickers + 1)}
    N = {f"O{o}" for o in range(1, orders + 1)}

    # Example:  B1 --> P1, B2 --> P2, B3 --> P1, B4 --> P2, etc
    x = {(p, b): 0 for p in P for b in B}
    sorted_pickers = sorted(P.keys())
    for i, b in enumerate(sorted(B.keys())):
        x[(sorted_pickers[i % len(sorted_pickers)], b)] = 1

    # Example: O1 --> B1, O2 --> B2, O3 --> B1, O4 --> B2, etc
    y = {(o, b): 0 for o in N for b in B}
    sorted_orders = sorted(N.keys())
    for i, b in enumerate(sorted(B.keys())):
        y[(sorted_orders[i % len(sorted_orders)], b)] = 1

    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(rows, cols, v_weight, h_weight)

    a = {(n, v): 0 for n in N for v in V}

    return opp_location_graph, V, B, P, N, x, y, a