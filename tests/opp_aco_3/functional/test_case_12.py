from tests.infra.factories.family_case import family_case
from models.opp_aco_3 import OPPAntColonyOptimization
from dtos.aco.solve_aco_3_model_dto import SolveAco3ModelDTO


TestOPPAntColonyOptimization2 = family_case(
    'tests.opp_aco_2.functional.test_case_12',
    {
        'OPPAntColonyOptimization': OPPAntColonyOptimization,
        'SolveAcoModelDTO': SolveAco3ModelDTO,
    },
)
