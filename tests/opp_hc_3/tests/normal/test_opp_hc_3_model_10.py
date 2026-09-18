from tests.family_case import family_case
from models.opp_hc_3 import OPPHillClimbing
from dtos.hc.solve_hc_3_model_dto import SolveHC3ModelDTO


TestOPPHillClimbing2 = family_case(
    'tests.opp_hc_2.tests.normal.test_opp_hc_2_model_10',
    {'OPPHillClimbing': OPPHillClimbing, 'SolveHCModelDTO': SolveHC3ModelDTO},
)
