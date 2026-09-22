from dtos import ModelDTO
from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO
from graphs.graphs_factory import GraphsFactory


def single_order_params(due_date_value, start_time, cap_vehicle=100.0):
    """
    Same fixture as tests.shared_scenarios.functional.single_order_params_aco,
    ported to return a SolveAco4ModelDTO (V_p unset / T_frio_max default +inf,
    so it behaves identically to the aco_2 version) since opp_aco_4's solve()
    reads params.V_p / params.T_frio_max, which a plain SolveAcoModelDTO
    doesn't have.
    """
    B = {"B1"}
    factory = GraphsFactory()
    opp_location_graph, V = factory.get_graph(4, 4, 4, 4)
    N = {"O1"}

    a = {(n, v): 0 for n in N for v in V}
    a[("O1", "V2")] = 1

    y = {("O1", "B1"): 1}

    params = SolveAco4ModelDTO()
    # w1 > w2*gamma forces the optimizer to minimize v (completion time)
    # rather than trading it off against earliness
    params.W_full = 10.0
    params.W_ea_ta = 1.0
    params.W_ea = 1.0
    params.W_ta = 1.0
    params.C_n = {"O1": 1.0}
    params.C_v = cap_vehicle
    params.A = a
    params.B_time = 0.5
    params.B_setup = 1.0
    params.B_picking = 1.0
    params.Dd = {"O1": due_date_value}
    params.M = 1000.0
    params.Bn = y

    model_dto = ModelDTO()
    model_dto.N = N
    model_dto.location_graph = opp_location_graph
    model_dto.B = B
    model_dto.start_time = start_time

    return params, model_dto
