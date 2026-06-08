from dtos.opp.solve_model_dto import SolveModelDTO


class SolveAcoModelDTO(SolveModelDTO):
    """
    Data Transfer Object (DTO) for Ant Colony Optimization (ACO) model parameters.
    Inherits from SolveModelDTO to maintain exact model constraints and inputs,
    while adding specific metaheuristic hyperparameters.
    """

    def __init__(self):
        super().__init__()
        self._A_ants = 15  # Renamed from _A to avoid collision with visitation matrix A
        self._Max_it = 60
        self._Alpha = 1.0  # Importance of accumulated pheromone
        self._Beta = 2.5  # Importance of visibility (inverse distance)
        self._E = 0.15  # Pheromone evaporation rate
        self._Q = 100.0  # Pheromone deposit factor

    @property
    def A_ants(self) -> int:
        """int: Number of ants in the colony."""
        return self._A_ants

    @A_ants.setter
    def A_ants(self, value: int):
        self._A_ants = value

    @property
    def Max_it(self) -> int:
        """int: Maximum number of iterations for the ACO algorithm."""
        return self._Max_it

    @Max_it.setter
    def Max_it(self, value: int):
        self._Max_it = value

    @property
    def Alpha(self) -> float:
        """float: Importance weight of the accumulated pheromone (tau)."""
        return self._Alpha

    @Alpha.setter
    def Alpha(self, value: float):
        self._Alpha = value

    @property
    def Beta(self) -> float:
        """float: Importance weight of the visibility or heuristic desirability (eta)."""
        return self._Beta

    @Beta.setter
    def Beta(self, value: float):
        self._Beta = value

    @property
    def E(self) -> float:
        """float: Pheromone evaporation rate (rho). Must be between 0 and 1."""
        return self._E

    @E.setter
    def E(self, value: float):
        self._E = value

    @property
    def Q(self) -> float:
        """float: Pheromone deposit constant factor."""
        return self._Q

    @Q.setter
    def Q(self, value: float):
        self._Q = value
