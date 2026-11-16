"""opp_hc on exactly the instances of opp_split's functional cases (see tests/infra/factories/functional_instances.py)."""

from dtos.hc.solve_hc_model_dto import SolveHCModelDTO
from models.opp_hc import OPPHillClimbing
from tests.infra.factories.functional_instances import bind_instances

bind_instances(OPPHillClimbing, SolveHCModelDTO, globals())
