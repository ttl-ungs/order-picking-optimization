from graphs.graphs_factory import GraphsFactory


def scenario_one_mission_one_picker_grid_graph(rows=4, cols=4, v_weight=4, h_weight=4):
    H = {"M1"}
    K = {1}
    P = {"P1"}

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[("P1", 1, "M1")] = 1

    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(rows, cols, v_weight, h_weight)
    B = set()

    return H, K, P, x, opp_location_graph, V, B
