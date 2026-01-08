from models.opp_location_graph import OPPLocationGraph

"""
   Scenario for test 8
"""

def test_four_orders_two_locations_two_missions():
    V = {"L1", "L2", "L3", "L4", "L5"}
    H = {"M1", "M2"}
    K = {1}
    P = {"P1", "P2"}
    B = set()

    opp_location_graph = OPPLocationGraph("L1", "L5")

    for i in range(1, len(V)+1):
        opp_location_graph.add_vertex(f"L{i}", "picking")

    opp_location_graph.add_edge("L1", "L2", 50)
    opp_location_graph.add_edge("L2", "L1", 50)

    opp_location_graph.add_edge("L1", "L5", 1)
    opp_location_graph.add_edge("L5", "L1", 1)

    opp_location_graph.add_edge("L1", "L3", 1)
    opp_location_graph.add_edge("L3", "L1", 1)

    opp_location_graph.add_edge("L1", "L4", 50)
    opp_location_graph.add_edge("L4", "L1", 50)

    opp_location_graph.add_edge("L2", "L5", 1)
    opp_location_graph.add_edge("L5", "L2", 1)

    opp_location_graph.add_edge("L3", "L2", 50)
    opp_location_graph.add_edge("L2", "L3", 50)

    opp_location_graph.add_edge("L3", "L5", 1)
    opp_location_graph.add_edge("L5", "L3", 1)

    opp_location_graph.add_edge("L4", "L3", 50)
    opp_location_graph.add_edge("L3", "L4", 50)

    opp_location_graph.add_edge("L4", "L5", 1)
    opp_location_graph.add_edge("L5", "L4", 1)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[("P1", 1, "M1")] = 1
    x[("P2", 1, "M2")] = 1

    cap_vehicle = 7.0

    return V, H, K, P, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle, x
