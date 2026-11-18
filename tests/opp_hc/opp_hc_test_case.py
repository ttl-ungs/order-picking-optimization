from dtos.hc.solve_hc_model_dto import SolveHCModelDTO
from models.opp_hc import OPPHillClimbing
from tests.infra.cases.heuristic_model_case import HeuristicModelTestCase


class OPPTestCaseHC(HeuristicModelTestCase):
    """Adapter of OPP-HC: solves the shared cases with Hill Climbing."""

    model_cls = OPPHillClimbing
    dto_cls = SolveHCModelDTO
