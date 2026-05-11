from graphs.graphs_factory import GraphsFactory

def scenario_six_missions_two_periods_grid_graph(rows=4, cols=4, v_weight=4, h_weight=4):
    B= {"B1", "B2", "B3", "B4", "B5", "B6"}
    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(rows, cols, v_weight, h_weight)

    return opp_location_graph, V, B