from models.base.opp_location_graph import OPPLocationGraph

"""
   Scenario for tests 2.1 and 2.2
"""


def two_orders_two_aisles():
    V = {"L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"}
    P = {"P1", "P2"}
    B = {"B1", "B2"}

    opp_location_graph = OPPLocationGraph("L1", "L8")

    for i in range(2, 8):
        opp_location_graph.add_vertex(f"L{i}", "picking")

    opp_location_graph.add_edge("L1", "L2", 10)
    opp_location_graph.add_edge("L2", "L3", 20)
    opp_location_graph.add_edge("L3", "L4", 5)
    opp_location_graph.add_edge("L4", "L8", 3)

    opp_location_graph.add_edge("L1", "L5", 15)
    opp_location_graph.add_edge("L5", "L6", 10)
    opp_location_graph.add_edge("L6", "L7", 9)
    opp_location_graph.add_edge("L7", "L8", 2)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    x = {(p, b): 0 for p in P for b in B}
    x[("P1", "B1")] = 1
    x[("P2", "B2")] = 1

    cap_vehicle = 5.0

    return V, P, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle, x
