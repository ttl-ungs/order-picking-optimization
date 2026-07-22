from models.base.opp_location_graph import OPPLocationGraph


def branched_single_mission_route():
    V = {"L1", "L2", "L3", "L4", "L5", "L6", "L7"}
    B = {"B1"}

    opp_location_graph = OPPLocationGraph("L1", "L7")

    for i in range(2, 7):
        opp_location_graph.add_vertex(f"L{i}", "picking")

    opp_location_graph.add_edge("L1", "L2", 2)
    opp_location_graph.add_edge("L2", "L1", 2)

    opp_location_graph.add_edge("L2", "L3", 1)
    opp_location_graph.add_edge("L3", "L2", 1)

    opp_location_graph.add_edge("L3", "L5", 1)
    opp_location_graph.add_edge("L5", "L3", 1)

    opp_location_graph.add_edge("L5", "L6", 1)
    opp_location_graph.add_edge("L6", "L5", 1)

    opp_location_graph.add_edge("L6", "L7", 2)
    opp_location_graph.add_edge("L7", "L6", 2)

    opp_location_graph.add_edge("L2", "L4", 4)
    opp_location_graph.add_edge("L4", "L2", 4)

    opp_location_graph.add_edge("L3", "L4", 4)
    opp_location_graph.add_edge("L4", "L3", 4)

    opp_location_graph.add_edge("L4", "L5", 4)
    opp_location_graph.add_edge("L5", "L4", 4)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0
    cap_vehicle = 8.0

    return V, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle
