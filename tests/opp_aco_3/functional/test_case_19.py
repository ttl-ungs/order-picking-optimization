from tests.infra.factories.family_case import family_case
from models.opp_aco_3 import OPPAntColonyOptimization
from dtos.aco.solve_aco_3_model_dto import SolveAco3ModelDTO
from models.opp_aco_3.utils.output_handler import OutputHandler


TestDueDatesExtreme = family_case(
    'tests.opp_aco_2.functional.test_case_19',
    {
        'OPPAntColonyOptimization': OPPAntColonyOptimization,
        'SolveAcoModelDTO': SolveAco3ModelDTO,
        'OutputHandler': OutputHandler,
    },
)
