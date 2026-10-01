"""Adapts a v5-style scenario dict (the format tests/shared_scenarios/stress/
stress_scenarios_v5*.py and two_stage_scenarios_v5.py build, and
tests/infra/zimpl/dat_files_builder.py consumes for ZIMPL) into the
OPPLocationGraph + DTO shape opp_aco_4/opp_hc_4 expect.

Needed because v5's stress scenarios (realistic_crew_scenario,
migrated_stress_scenario) were built only for v5 and are never used by
opp_aco_2/opp_hc_2 -- unlike the functional scenarios, there is no existing
aco_4/hc_4 test that already exercises this content via family_case, so
there is nothing to adapt FROM on that side. This module is the one-time
translation needed to run the same scenario through opp_aco_4/opp_hc_4.
"""

from models.base.opp_location_graph import OPPLocationGraph
from dtos.opp.model_dto import ModelDTO


def build_model_dto_and_params(scenario, dto_cls, seed=1):
    """scenario: a v5-style dict (see stress_scenarios_v5_designed.py's
    designed_stress_scenario for the exact keys). dto_cls: SolveAco4ModelDTO
    or SolveHC4ModelDTO (field names are identical between the two, see
    their docstrings). Returns (model_dto, params), ready for
    OPPAntColonyOptimization(model_dto).solve(params) or
    OPPHillClimbing(model_dto).solve(params).
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
