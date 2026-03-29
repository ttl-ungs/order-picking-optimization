from tests.opp.graphs.graphs_factory import GraphsFactory

def scenario_six_missions_three_pickers_two_periods_grid_graph():

    H = {"M1", "M2", "M3", "M4", "M5", "M6"}
    K = {1, 2}
    P = {"P1", "P2", "P3"}

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[("P1", 1, "M1")] = 1
    x[("P1", 2, "M2")] = 1
    x[("P2", 1, "M3")] = 1
    x[("P2", 2, "M4")] = 1
    x[("P3", 1, "M5")] = 1
    x[("P3", 2, "M6")] = 1

    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(4, 4, 4, 5)
    B = set()
   
    return H, K, P, x, opp_location_graph, V, B

def scenario_six_missions_three_pickers_one_period_grid_graph():

    H = {"M1", "M2", "M3", "M4", "M5", "M6"}
    K = {1}
    P = {"P1", "P2", "P3"}

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[("P1", 1, "M1")] = 1
    x[("P1", 1, "M2")] = 1
    x[("P2", 1, "M3")] = 1
    x[("P2", 1, "M4")] = 1
    x[("P3", 1, "M5")] = 1
    x[("P3", 1, "M6")] = 1

    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(4, 4, 4, 5)
    B = set()

    return H, K, P, x, opp_location_graph, V, B