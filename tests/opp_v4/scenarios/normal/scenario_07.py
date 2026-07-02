from models.base.opp_location_graph import OPPLocationGraph

"""
   Scenario for test 7
"""


def test_two_orders_two_locations_two_missions():
    V = {"L1", "L2", "L3", "L4"}
    P = {"P1", "P2"}
    B = {"B1", "B2"}

    opp_location_graph = OPPLocationGraph("L1", "L4")

    for i in range(1, len(V) + 1):
        opp_location_graph.add_vertex(f"L{i}", "picking")

    opp_location_graph.add_edge("L1", "L2", 50)
    opp_location_graph.add_edge("L2", "L1", 50)

    opp_location_graph.add_edge("L1", "L4", 1)
    opp_location_graph.add_edge("L4", "L4", 1)

    opp_location_graph.add_edge("L1", "L3", 50)
    opp_location_graph.add_edge("L3", "L1", 50)

    opp_location_graph.add_edge("L2", "L4", 1)
    opp_location_graph.add_edge("L4", "L2", 1)

    opp_location_graph.add_edge("L3", "L4", 1)
    opp_location_graph.add_edge("L4", "L3", 1)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    x = {(p, b): 0 for p in P for b in B}
    x[("P1", "B1")] = 1
    x[("P2", "B2")] = 1

    cap_vehicle = 5.0

    return V, P, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle, x
