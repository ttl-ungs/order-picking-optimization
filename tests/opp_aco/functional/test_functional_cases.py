"""opp_aco on exactly the instances of opp_split's functional cases (see tests/infra/factories/functional_instances.py)."""

from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.opp_aco import OPPAntColonyOptimization
from tests.infra.factories.functional_instances import bind_instances

bind_instances(OPPAntColonyOptimization, SolveAcoModelDTO, globals())
