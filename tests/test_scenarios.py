import itertools

from models.opp_location_graph import OPPLocation, OPPLocationGraph

"""
   Scenario for test 1
"""
def basic_two_orders_capacity_limit():
    V = {"L1", "L2", "L3", "L4"}
    H = {"M1", "M2"}
    K = {1}
    P = {"P1", "P2"}
    B = set()

    location_graph = OPPLocationGraph(depot_node="L1", final_node="L4")

    for i in range(2, 4):
        location_graph.add_vertex(f"L{i}", "picking")

    location_graph.add_edge("L1", "L2", 10)
    location_graph.add_edge("L1", "L3", 12.0)
    location_graph.add_edge("L2", "L3", 5.0)
    location_graph.add_edge("L2", "L4", 10.0)
    location_graph.add_edge("L3", "L2", 5.0)
    location_graph.add_edge("L3", "L4", 10.0)

    w1 = 1.0 
    w2 = 10.0 
    gamma = 1.0 
    delta = 5.0 

    cap_vehicle = 5.0

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[("P1", 1, "M1")] = 1
    x[("P2", 1, "M2")] = 1
    
    return V, H, K, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x

"""
   Scenario for tests 2.1 and 2.2
"""
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

"""
   Scenario for test 3
"""
def test_two_possible_routes():
    V = {"L1", "L2", "L3", "L4", "L5"}
    H = {"M1", "M2"}
    K = {1}
    P = {"P1", "P2"}
    B = set()

    opp_location_graph = OPPLocationGraph("L1", "L5")

    for i in range(2, 5):
        opp_location_graph.add_vertex(f"L{i}", "picking")

    opp_location_graph.add_edge("L1", "L2", 5)
    opp_location_graph.add_edge("L1", "L3", 5)
    opp_location_graph.add_edge("L1", "L4", 3)

    opp_location_graph.add_edge("L2", "L4", 5)
    opp_location_graph.add_edge("L3", "L4", 5)

    opp_location_graph.add_edge("L4", "L5", 5)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[("P1", 1, "M1")] = 1
    x[("P2", 1, "M2")] = 1

    cap_vehicle = 5.0

    return V, H, K, P, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle, x
