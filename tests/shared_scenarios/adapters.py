"""
Adapts a plain instance dict (see instances.py) into a ready-to-solve
(params, model_dto) pair for a specific model family.

One generic function covers all 6 heuristic models: every HC/ACO params
DTO (SolveHCModelDTO, SolveHC3ModelDTO, SolveHC4ModelDTO, SolveAcoModelDTO,
SolveAco3ModelDTO, SolveAco4ModelDTO) inherits the same common fields
(W_c, W_pen, W_e, W_t, C_n, C_v, A, T_travel, T_setup, T_pick, T_due_n,
M, B_nb) from dtos/opp/solve_model_dto.py::SolveModelDTO -- only a handful
of family-specific extras (Min_dwell, V_p, T_cold, ACO hyperparameters,
...) differ, and those already have sensible defaults in each DTO's own
__init__, so callers only need to override one via `extra_fields` if they
actually want to test something other than the default (e.g. cold chain
active instead of disabled).
"""

from typing import Dict, Type

from dtos.opp.model_dto import ModelDTO


def build_model_dto(instance: Dict) -> ModelDTO:
    """The (N, location_graph, B, P, start_time) tuple every model's __init__ needs, shared across families."""
    dto = ModelDTO()
    dto.N = instance["N"]
    dto.location_graph = instance["location_graph"]
    dto.B = instance["B"]
    dto.P = instance["P"]
    dto.start_time = 0
    return dto


def build_params(instance: Dict, dto_cls: Type, **extra_fields):
    """
    `dto_cls` is whichever SolveXModelDTO the target model family expects
    (e.g. SolveHC4ModelDTO for opp_hc_4). `extra_fields` are set via
    setattr AFTER the common fields, so a caller can override a family-
    specific default (e.g. V_p=..., T_cold=... for hc_4/aco_4) without
    this function needing to know about every family's extras up front.
    """
    params = dto_cls()
    params.W_c = instance["W_c"]
    params.W_pen = instance["W_pen"]
    params.W_e = instance["W_e"]
    params.W_t = instance["W_t"]
    params.C_n = instance["C_n"]
    params.C_v = instance["C_v"]
    params.A = instance["A"]
    params.T_travel = instance["T_travel"]
    params.T_setup = instance["T_setup"]
    params.T_pick = instance["T_pick"]
    params.T_due_n = instance["T_due_n"]
    params.M = instance["M"]
    params.B_nb = instance["B_nb"]

    for key, value in extra_fields.items():
        setattr(params, key, value)

    return params
