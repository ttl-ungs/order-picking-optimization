"""opp_hc_4 on exactly the instances of opp_v5_2_split's functional tests (see tests/infra/factories/v5_equivalence.py)."""

from dtos.hc.solve_hc_4_model_dto import SolveHC4ModelDTO
from models.opp_hc_4 import OPPHillClimbing
from tests.infra.factories.v5_equivalence import equivalence_case

TestV5Equivalence = equivalence_case(OPPHillClimbing, SolveHC4ModelDTO)
