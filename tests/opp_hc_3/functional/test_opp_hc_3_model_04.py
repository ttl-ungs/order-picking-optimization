from tests.family_case import family_case
from models.opp_hc_3 import OPPHillClimbing
from dtos.hc.solve_hc_3_model_dto import SolveHC3ModelDTO


TestOPPHillClimbing2Model4 = family_case(
    'tests.opp_hc_2.functional.test_opp_hc_2_model_04',
    {'OPPHillClimbing': OPPHillClimbing, 'SolveHCModelDTO': SolveHC3ModelDTO},
)
