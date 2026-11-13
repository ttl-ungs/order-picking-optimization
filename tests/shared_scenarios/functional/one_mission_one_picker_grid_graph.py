from tests.infra.factories.graphs_factory import GraphsFactory


def scenario_one_mission_one_picker_grid_graph(rows=4, cols=4, v_weight=4, h_weight=4):
    B = {"B1"}
    P = {"P1"}

    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(rows, cols, v_weight, h_weight)

    return P, opp_location_graph, V, B
