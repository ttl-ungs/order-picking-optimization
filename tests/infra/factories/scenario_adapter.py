"""Adapts a scenario dict (what the scenario builders produce and
tests/infra/zimpl/dat_files_builder.py writes for ZIMPL) into the
OPPLocationGraph and the DTOs the heuristics take, so that the same scenario
runs on the four models.
"""

from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO


def build_model_dto_and_params(scenario, dto_cls, seed=1):
    """Build (model_dto, params) for a heuristic from a scenario dict (keys as
    in designed_stress_scenario). `dto_cls` is SolveAcoModelDTO or
    SolveHCModelDTO.
    """
    location_graph = OPPLocationGraph(depot_node=scenario["depot"], final_node=scenario["final"])
    for vertex in scenario["V"]:
        if vertex not in (scenario["depot"], scenario["final"]):
            location_graph.add_vertex(vertex, "picking")
    for (i, j) in scenario["E"]:
        location_graph.add_edge(i, j, scenario["D_ij"][(i, j)])

    params = dto_cls()
    params.W_c = scenario["W_c"]
    params.W_pen = scenario["W_pen"]
    params.W_e = scenario["W_e"]
    params.W_t = scenario["W_t"]
    params.C_n = scenario["C_n"]
    params.C_v = scenario["C_v"]
    params.A = scenario["A_ni"]
    params.T_travel = scenario["T_travel"]
    params.T_setup = scenario["T_setup"]
    params.T_pick = scenario["T_pick"]
    params.S = scenario["S_i"]
    params.T_due_n = scenario["T_due_n"]
    params.M = scenario["M"]
    params.B_nb = scenario["B_nb"]
    params.V_p = scenario["V_p"]
    params.T_cold = scenario["T_cold"]
    params.Seed = seed

    model_dto = ModelDTO()
    model_dto.N = scenario["N"]
    model_dto.location_graph = location_graph
    model_dto.B = scenario["B"]
    model_dto.P = scenario["P"]
    model_dto.start_time = 0

    return model_dto, params
