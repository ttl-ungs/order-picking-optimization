from dtos import SolveModelDTO, ModelDTO
from tests.infra.factories.graphs_factory import GraphsFactory


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
    params.W_c = 10.0
    params.W_pen = 1.0
    params.W_e = 1.0
    params.W_t = 1.0
    params.C_n = {"O1": 1.0}
    params.C_v = cap_vehicle
    params.A = a
    params.T_travel = 0.5
    params.T_setup = 1.0
    params.T_pick = 1.0
    params.T_due_n = {"O1": due_date_value}
    params.M = 1000.0
    params.B_nb = y

    model_dto = ModelDTO()
    model_dto.N = N
    model_dto.location_graph = opp_location_graph
    model_dto.B = B
    model_dto.start_time = start_time

    return params, model_dto