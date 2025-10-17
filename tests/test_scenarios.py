import itertools

from models.opp_location_graph import OPPLocation, OPPLocationGraph

def basic_two_orders_capacity_limit():
    N = {1, 2}
    V = {1, 2, 3, 4}
    H = {1, 2}
    K = {1}
    P = {1, 2}
    B = set()

    location_graph = OPPLocationGraph(depot_node=1, final_node=4)

    for v in V:
        if v in {2, 3}:
            location_graph.add_vertex(v, "picking")

    location_graph.add_edge(1, 2, 10.0)
    location_graph.add_edge(1, 3, 12.0)
    location_graph.add_edge(2, 3, 5.0)
    location_graph.add_edge(2, 4, 10.0)
    location_graph.add_edge(3, 2, 5.0)
    location_graph.add_edge(3, 4, 10.0)

    w1 = 1.0 
    w2 = 10.0 
    gamma = 1.0 
    delta = 5.0 

    cap_vehicle = 5.0
    cap_n = {1: 3.0, 2: 3.0}

    a = {
        (1, 1): 0,
        (1, 2): 1,
        (1, 3): 0,
        (1, 4): 0,
        (2, 1): 0,
        (2, 2): 0,
        (2, 3): 1,
        (2, 4): 0,
    }

    beta_time = 0.5
    beta_setup = 1.0
    beta_picking = 1.0
    M = 1000.0

    due_date = {1: 15.0, 2: 15.0}

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[1, 1, 1] = 1
    x[2, 1, 2] = 1

    y = {(n, h): 0 for n in N for h in H}
    y[1, 1] = 1
    y[2, 2] = 1
    return N, H, K, P, B, w1, w2, gamma, delta, cap_n, location_graph, cap_vehicle, a, beta_time, beta_setup, beta_picking, due_date, M, x, y

def two_orders_two_aisles():
    V = {"L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"}
    H = {"M1", "M2"}
    K = {1}
    P = {"P1", "P2"}
    B = set()

    opp_location_graph = OPPLocationGraph("L1", "L8")

    for i in range(2, 8):
        opp_location_graph.add_vertex(f"L{i}", "picking")

    opp_location_graph.add_edge("L1", "L2", 10)
    opp_location_graph.add_edge("L2", "L3", 10)
    opp_location_graph.add_edge("L3", "L4", 10)
    opp_location_graph.add_edge("L4", "L8", 10)

    opp_location_graph.add_edge("L1", "L5", 10)
    opp_location_graph.add_edge("L5", "L6", 10)
    opp_location_graph.add_edge("L6", "L7", 10)
    opp_location_graph.add_edge("L7", "L8", 10)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[("P1", 1, "M1")] = 1
    x[("P2", 1, "M2")] = 1

    cap_vehicle = 5.0

    return V, H, K, P, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle, x
