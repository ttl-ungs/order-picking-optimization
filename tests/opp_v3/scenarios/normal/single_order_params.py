from dtos import SolveModelDTO, ModelDTO
from graphs.graphs_factory import GraphsFactory


def single_order_params(due_date_value, start_time, cap_vehicle=100.0):
    B = {"B1"}
    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(4, 4, 4, 4)
    N = {"O1"}

    a = {(n, v): 0 for n in N for v in V}
    a[("O1", "V2")] = 1

    y = {("O1", "B1"): 1}

    params = SolveModelDTO()
    # w1 > w2*gamma forces the optimizer to minimize v (completion time)
    # rather than trading it off against earliness
    params.w1 = 10.0
    params.w2 = 1.0
    params.gamma = 1.0
    params.delta = 1.0
    params.cap_n = {"O1": 1.0}
    params.cap_vehicle = cap_vehicle
    params.a = a
    params.beta_time = 0.5
    params.beta_setup = 1.0
    params.beta_picking = 1.0
    params.due_date = {"O1": due_date_value}
    params.M = 1000.0
    params.y = y

    model_dto = ModelDTO()
    model_dto.N = N
    model_dto.location_graph = opp_location_graph
    model_dto.B = B
    model_dto.start_time = start_time

    return params, model_dto