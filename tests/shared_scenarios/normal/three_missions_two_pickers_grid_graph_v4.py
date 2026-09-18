from graphs.graphs_factory import GraphsFactory


def scenario_three_missions_two_pickers_two_periods_grid_graph(
    rows=4, cols=4, v_weight=4, h_weight=4
):
    B = {"B1", "B2", "B3"}
    P = {"P1", "P2"}

    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(rows, cols, v_weight, h_weight)
    opp_location_graph.add_edge("V1", "V6", v_weight)
    opp_location_graph.add_edge("V6", "V11", v_weight)
    opp_location_graph.add_edge("V11", "V16", v_weight)

    return P, opp_location_graph, V, B
