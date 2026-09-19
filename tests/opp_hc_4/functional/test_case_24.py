from tests.support.family_case import family_case
from models.opp_hc_4 import OPPHillClimbing
from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO
from models.opp_hc_4.utils.output_handler import OutputHandler


TestServiceTimeEdgeCases = family_case(
    'tests.opp_hc_2.functional.test_case_25',
    {
        'OPPHillClimbing': OPPHillClimbing,
        'SolveHCModelDTO': SolveHC4ModelDTO,
        'OutputHandler': OutputHandler,
    },
)
