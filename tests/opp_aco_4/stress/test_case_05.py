from tests.support.family_case import family_case
from models.opp_aco_4 import OPPAntColonyOptimization
from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO
from models.opp_aco_4.utils.output_handler import OutputHandler


TestOPPModel = family_case(
    'tests.opp_aco_2.stress.test_case_05',
    {
        'OPPAntColonyOptimization': OPPAntColonyOptimization,
        'SolveAcoModelDTO': SolveAco4ModelDTO,
        'OutputHandler': OutputHandler,
    },
)
