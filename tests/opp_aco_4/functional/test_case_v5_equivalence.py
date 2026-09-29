"""opp_aco_4 on exactly the instances of opp_v5_2_split's functional tests (see tests/infra/factories/v5_equivalence.py)."""

from dtos.aco.solve_aco_4_model_dto import SolveAco4ModelDTO
from models.opp_aco_4 import OPPAntColonyOptimization
from tests.infra.factories.v5_equivalence import equivalence_case

TestV5Equivalence = equivalence_case(OPPAntColonyOptimization, SolveAco4ModelDTO)
