from tests.support.family_case import family_case
from models.opp_hc_3 import OPPHillClimbing
from dtos.hc.solve_hc_3_model_dto import SolveHC3ModelDTO
from models.opp_hc_3.utils.output_handler import OutputHandler


TestFractionalZeroCapacities = family_case(
    'tests.opp_hc_2.functional.test_case_21',
    {
        'OPPHillClimbing': OPPHillClimbing,
        'SolveHCModelDTO': SolveHC3ModelDTO,
        'OutputHandler': OutputHandler,
    },
)
