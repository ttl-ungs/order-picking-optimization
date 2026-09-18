from tests.family_case import family_case
from models.opp_aco_4 import OPPAntColonyOptimization
from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO


TestOPPAntColonyOptimization2 = family_case(
    'tests.opp_aco_2.tests.normal.test_opp_aco_2_model_09',
    {
        'OPPAntColonyOptimization': OPPAntColonyOptimization,
        'SolveAcoModelDTO': SolveAco4ModelDTO,
    },
)
