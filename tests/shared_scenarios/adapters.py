"""
Adapts a plain instance dict (see instances.py) into a ready-to-solve
(params, model_dto) pair for a specific model family.

One generic function covers all 6 heuristic models: every HC/ACO params
DTO (SolveHCModelDTO, SolveHC3ModelDTO, SolveHC4ModelDTO, SolveAcoModelDTO,
SolveAco3ModelDTO, SolveAco4ModelDTO) inherits the same common fields
(W_full, W_ea_ta, W_ea, W_ta, C_n, C_v, A, B_time, B_setup, B_picking, Dd,
M, Bn) from dtos/opp/solve_model_dto.py::SolveModelDTO -- only a handful
of family-specific extras (Min_dwell, V_p, T_frio_max, ACO hyperparameters,
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
    specific default (e.g. V_p=..., T_frio_max=... for hc_4/aco_4) without
    this function needing to know about every family's extras up front.
    """
    params = dto_cls()
    params.W_full = instance["W_full"]
    params.W_ea_ta = instance["W_ea_ta"]
    params.W_ea = instance["W_ea"]
    params.W_ta = instance["W_ta"]
    params.C_n = instance["C_n"]
    params.C_v = instance["C_v"]
    params.A = instance["A"]
    params.B_time = instance["B_time"]
    params.B_setup = instance["B_setup"]
    params.B_picking = instance["B_picking"]
    params.Dd = instance["Dd"]
    params.M = instance["M"]
    params.Bn = instance["Bn"]

    for key, value in extra_fields.items():
        setattr(params, key, value)

    return params
