from models.base.opp_location_graph import OPPLocationGraph

"""
   Scenario for test 3
"""


def two_possible_routes_batches():
    V = {"L1", "L2", "L3", "L4", "L5"}
    B = {"B1", "B2"}

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

    cap_vehicle = 5.0

    return V, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle
