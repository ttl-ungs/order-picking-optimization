from tests.family_case import family_case
from models.opp_aco_3 import OPPAntColonyOptimization
from dtos.aco.solve_aco_3_model_dto import SolveAco3ModelDTO
from models.opp_aco_3.utils.output_handler import OutputHandler


TestOPPModel = family_case(
    'tests.opp_aco_2.tests.stress.test_opp_aco_2_model_11',
    {
        'OPPAntColonyOptimization': OPPAntColonyOptimization,
        'SolveAcoModelDTO': SolveAco3ModelDTO,
        'OutputHandler': OutputHandler,
    },
)
