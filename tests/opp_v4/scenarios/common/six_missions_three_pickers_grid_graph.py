from graphs.graphs_factory import GraphsFactory

def scenario_six_missions_three_pickers_two_periods_grid_graph(rows=4, cols=4, v_weight=4, h_weight=4):
    P = {"P1", "P2", "P3"}
    B= {"B1", "B2", "B3", "B4", "B5", "B6"}
    x = {(p, b): 0 for p in P for b in B}
    x[("P1", "B1")] = 1
    x[("P1", "B2")] = 1
    x[("P2", "B3")] = 1
    x[("P2", "B4")] = 1
    x[("P3", "B5")] = 1
    x[("P3", "B6")] = 1

    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(rows, cols, v_weight, h_weight)

    return P, x, opp_location_graph, V, B

def scenario_six_missions_three_pickers_one_period_grid_graph(rows=4, cols=4, v_weight=4, h_weight=4):
    P = {"P1", "P2", "P3"}
    B= {"B1", "B2", "B3", "B4", "B5", "B6"}

    x = {(p, b): 0 for p in P for b in B}
    x[("P1", "G1")] = 1
    x[("P1", "G2")] = 1
    x[("P2", "G3")] = 1
    x[("P2", "G4")] = 1
    x[("P3", "G5")] = 1
    x[("P3", "G6")] = 1

    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(rows, cols, v_weight, h_weight)

    return P, x, opp_location_graph, V, B