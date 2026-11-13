from tests.infra.factories.graphs_factory import GraphsFactory


def grid_5x3_two_pickers_four_batches():
    B = {"B1", "B2", "B3", "B4"}
    P = {"P1", "P2"}

    x = {(p, b): 0 for p in P for b in B}
    x[("P1", "B1")] = 1
    x[("P1", "B2")] = 1
    x[("P2", "B3")] = 1
    x[("P2", "B4")] = 1

    factory = GraphsFactory()
    location_graph, V = factory.get_graph(5, 3, v_weight=2, h_weight=3)

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    cap_vehicle = 6.0

    return V, P, B, w1, w2, gamma, delta, location_graph, cap_vehicle, x
