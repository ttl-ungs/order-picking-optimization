from tests.support.graphs_factory import GraphsFactory


def scenario_three_missions_two_pickers_two_periods_grid_graph(
    rows=4, cols=4, v_weight=4, h_weight=4
):
    H = {"M1", "M2", "M3"}
    K = {1, 2}
    P = {"P1", "P2"}

    # Mission assignment by picker and period:
    # P1 handles M1 then M2, P2 handles M3 in period 1.
    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[("P1", 1, "M1")] = 1
    x[("P1", 2, "M2")] = 1
    x[("P2", 1, "M3")] = 1

    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(rows, cols, v_weight, h_weight)
    opp_location_graph.add_edge("V1", "V6", v_weight)
    opp_location_graph.add_edge("V6", "V11", v_weight)
    opp_location_graph.add_edge("V11", "V16", v_weight)
    B = set()

    return H, K, P, x, opp_location_graph, V, B
