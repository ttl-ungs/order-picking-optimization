from dtos.opp.solve_model_dto import SolveModelDTO


class SolveAcoModelDTO(SolveModelDTO):
    """
    Parameters of the Ant Colony Optimization heuristic (OPP-ACO): the colony's
    hyperparameters, the time budget, the picker speeds and the cold-chain limit.
    Inherits from SolveModelDTO to maintain the exact models' constraints and inputs.

    The execution time per (picker, batch) is the one of the exact models:
        T_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]
    where fixed_time(b) = T_setup + T_pick * sum(C_n over b's orders)
    does NOT depend on picker speed (setup/picking are manual work, not
    walking), and route_time(b) = T_travel * travel_distance + service_time
    is the part scaled by how fast the picker walks/scans.

    There is no congestion between concurrent pickers, like in the exact models.
    """

    def __init__(self):
        super().__init__()
        self._A_ants = 15  # Renamed from _A to avoid collision with visitation matrix A
        self._Max_it = 60
        self._Alpha = 1.0  # Importance of accumulated pheromone
        self._Beta = 2.5  # Importance of visibility (inverse distance)
        self._E = 0.15  # Pheromone evaporation rate
        self._Q = 100.0  # Pheromone deposit factor
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
        """Wall-clock budget (seconds) for the ant colony loop -- the ACO
        counterpart of SolveHCModelDTO.Max_time. When it runs out, the
        current iteration stops building ants, its ants still update the
        best solution, and the run ends. It never ends a run that has no
        cold-chain-compliant solution yet (see OPP-ACO's solve()), so it
        can't turn a solvable instance into a false "infeasible". Default
        1800 s: above every realistic_crew stress run measured on
        2026-09-27 (<= ~410 s), so it only bounds the very large instances
        -- e.g. the 100x100 migrated grid, where the full 60 iterations
        would take ~5 h -- while staying under the stress runner's 40-min
        timeout. Measured there with 600 s: objective 1,061,148, vs 917,328
        when ACO ran ~1878 s (before the budget also covered the
        post-processing); 1800 s gives it about that same time back."""
        return self._Max_time

    @Max_time.setter
    def Max_time(self, value: float):
        self._Max_time = value

    @property
    def V_p(self) -> dict:
        """dict {picker: speed}. A picker missing from this dict defaults to
        speed 1.0 (see OPP-ACO's _picker_speed), which makes the speed a no-op."""
        return self._V_p

    @V_p.setter
    def V_p(self, value: dict):
        self._V_p = value or {}

    @property
    def T_cold(self) -> float:
        """Cold-chain deadline (seconds): the max allowed T_exec_pb[p, b]
        for a (picker, batch) pair to remain eligible for that assignment.
        Default +inf disables the cold chain entirely (every picker is eligible
        for every batch)."""
        return self._T_cold

    @T_cold.setter
    def T_cold(self, value: float):
        self._T_cold = value
