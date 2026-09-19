from models.base.opp_location_graph import OPPLocationGraph


def detour_single_mission_route():
    V = {"L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"}
    B = {"B1"}

    opp_location_graph = OPPLocationGraph("L1", "L8")

    for i in range(2, 8):
        opp_location_graph.add_vertex(f"L{i}", "picking")

    opp_location_graph.add_edge("L1", "L2", 1)
    opp_location_graph.add_edge("L2", "L1", 1)

    opp_location_graph.add_edge("L2", "L3", 1)
    opp_location_graph.add_edge("L3", "L2", 1)

    opp_location_graph.add_edge("L3", "L5", 1)
    opp_location_graph.add_edge("L5", "L3", 1)

    opp_location_graph.add_edge("L5", "L6", 1)
    opp_location_graph.add_edge("L6", "L5", 1)

    opp_location_graph.add_edge("L6", "L4", 1)
    opp_location_graph.add_edge("L4", "L6", 1)

    opp_location_graph.add_edge("L4", "L8", 1)
    opp_location_graph.add_edge("L8", "L4", 1)

    opp_location_graph.add_edge("L2", "L5", 5)
    opp_location_graph.add_edge("L5", "L2", 5)

    opp_location_graph.add_edge("L3", "L4", 2)
    opp_location_graph.add_edge("L4", "L3", 2)

    opp_location_graph.add_edge("L5", "L7", 5)
    opp_location_graph.add_edge("L7", "L5", 5)

    opp_location_graph.add_edge("L7", "L8", 3)
    opp_location_graph.add_edge("L8", "L7", 3)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0
    cap_vehicle = 10.0

    return V, B, w1, w2, gamma, delta, opp_location_graph, cap_vehicle
