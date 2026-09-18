from tests.family_case import family_case
from models.opp_hc_4 import OPPHillClimbing
from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO


TestOPPHillClimbing2 = family_case(
    'tests.opp_hc_2.tests.normal.test_opp_hc_2_model_08',
    {'OPPHillClimbing': OPPHillClimbing, 'SolveHCModelDTO': SolveHC4ModelDTO},
)
