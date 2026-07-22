from models.base.opp_location_graph import OPPLocationGraph

"""
   Scenario for test 4
"""


def bidirectional_edges():
    V = {"L1", "L2", "L3", "L4", "L5"}
    B = {"B1"}

    opp_location_graph = OPPLocationGraph("L1", "L5")

    for i in range(2, 5):
        opp_location_graph.add_vertex(f"L{i}", "picking")

    opp_location_graph.add_edge("L1", "L2", 5)
    opp_location_graph.add_edge("L2", "L1", 50)

    opp_location_graph.add_edge("L1", "L3", 2)
    opp_location_graph.add_edge("L3", "L1", 2)

    opp_location_graph.add_edge("L1", "L4", 8)
    opp_location_graph.add_edge("L4", "L1", 8)

    opp_location_graph.add_edge("L2", "L4", 5)
    opp_location_graph.add_edge("L4", "L2", 5)

    opp_location_graph.add_edge("L3", "L4", 1)
    opp_location_graph.add_edge("L4", "L3", 1)

    opp_location_graph.add_edge("L4", "L5", 9)
    opp_location_graph.add_edge("L5", "L4", 9)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    cap_vehicle = 5.0

    return V, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle
