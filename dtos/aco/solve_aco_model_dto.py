from dtos.opp.solve_model_dto import SolveModelDTO


class SolveAcoModelDTO(SolveModelDTO):
    """
    Parameters of the Ant Colony Optimization heuristic (OPP-ACO): the
    problem's parameters (SolveModelDTO) plus the colony's hyperparameters,
    the time budget, the picker speeds and the cold-chain limit.
    """

    def __init__(self):
        super().__init__()
        self._A_ants = 15  # not _A: A is the visit matrix
        self._Max_it = 60
        self._Alpha = 1.0
        self._Beta = 2.5
        self._E = 0.15
        self._Q = 100.0
        self._V_p: dict = {}
        self._T_cold: float = float("inf")
        self._Max_time: float = 1800.0

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

    @property
    def Max_time(self) -> float:
        """Wall-clock budget (seconds) of the solve. When it runs out the
        current iteration stops building ants, its ants still update the
        best solution, and the run ends. It never ends a run that has no
        cold-chain-compliant solution yet, so it cannot turn a solvable
        instance into a false "infeasible". The default of 1800 s is above
        every realistic-crew stress run (at most ~410 s) and below the
        stress runner's 40-minute timeout, so it only bounds the very large
        instances (the 100x100 grid would need about 5 h for its 60
        iterations)."""
        return self._Max_time

    @Max_time.setter
    def Max_time(self, value: float):
        self._Max_time = value

    @property
    def V_p(self) -> dict:
        """dict {picker: speed}. A picker missing from it has speed 1.0."""
        return self._V_p

    @V_p.setter
    def V_p(self, value: dict):
        self._V_p = value or {}

    @property
    def T_cold(self) -> float:
        """Cold-chain limit: the largest T_exec_pb[p, b] for which the pair
        (picker, batch) is eligible. The default, +inf, disables it."""
        return self._T_cold

    @T_cold.setter
    def T_cold(self, value: float):
        self._T_cold = value
