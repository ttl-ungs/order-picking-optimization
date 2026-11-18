from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.opp_aco import OPPAntColonyOptimization
from tests.infra.cases.heuristic_model_case import HeuristicModelTestCase


class OPPTestCaseACO(HeuristicModelTestCase):
    """Adapter of OPP-ACO: solves the shared cases with Ant Colony Optimization."""

    model_cls = OPPAntColonyOptimization
    dto_cls = SolveAcoModelDTO
