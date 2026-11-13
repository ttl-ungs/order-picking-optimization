"""opp_aco on exactly the instances of opp_split's functional tests (see tests/infra/factories/functional_instances.py)."""

from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO
from models.opp_aco import OPPAntColonyOptimization
from tests.infra.factories.functional_instances import functional_instances_case

TestFunctionalInstances = functional_instances_case(OPPAntColonyOptimization, SolveAcoModelDTO)
