from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO


class SolveAco3ModelDTO(SolveAcoModelDTO):
    """
    DTO for opp_aco_3: adds congestion and multi-pheromone (m-ACO4)
    hyperparameters on top of the opp_aco_2 (SolveAcoModelDTO) fields.

    Default Alpha/Beta/E come from the ACO parametrization reported for a
    real warehouse instance in:
        Lesch, V., Muller, P.B.M., Kramer, M., Hadry, M., Kounev, S., &
        Krupitzer, C. (2023). Optimizing storage assignment, order picking,
        and their interaction in mezzanine warehouses. Applied Intelligence,
        53, 18605-18629. (Table, p.18620: alpha=1.0, beta=2.0, rho=0.02,
        tau_min=1, tau_max=25, maxIterWoImpr=20, maxCataclysms=3)
    """

    def __init__(self):
        super().__init__()
        # Re-tune the inherited defaults to the values reported by Lesch et
        # al. (2023) for their ACO3/ACO4 variants, instead of opp_aco_2's.
        self._Alpha = 1.0
        self._Beta = 2.0
        self._E = 0.02

        # Congestion (Chen et al., 2013 - see models/utils/congestion.py)
        self._Min_dwell = 0.0  # minimum node occupancy/turnaround buffer

        # Multi-pheromone architecture m-ACO4(1,m) with m=2 objectives
        # (time/completion vs. congestion wait), per:
        #   Alaya, I., Solnon, C., & Ghedira, K. Ant Colony Optimization for
        #   Multi-objective Optimization Problems. Sec. 3.2 "m-ACO4(1,m)".
        self._Beta2 = 2.0  # visibility weight for the congestion pheromone matrix
        self._P_objective_switch = 0.5  # P(step guided by the time matrix, tau1)

        # MAX-MIN pheromone bounds (Lesch et al., 2023, tau_min=1, tau_max=25)
        self._Tau_min = 1.0
        self._Tau_max = 25.0

        # Cataclysm anti-stagnation mechanism (Chen et al., 2013, Sec.4.3;
        # Lesch et al., 2023, Algorithm 2) - resets both pheromone matrices
        # to their initial values after too many iterations without a global
        # improvement, up to a maximum number of resets.
        self._Max_iter_wo_improvement = 20
        self._Max_cataclysms = 3

    @property
    def Min_dwell(self) -> float:
        """float: minimum node occupancy time (congestion turnaround buffer), even
        for zero-service-time nodes. See CongestionTracker.dwell()."""
        return self._Min_dwell

    @Min_dwell.setter
    def Min_dwell(self, value: float):
        self._Min_dwell = value

    @property
    def Beta2(self) -> float:
        """float: importance weight of the congestion-avoidance visibility term,
        used for steps guided by the congestion pheromone matrix (tau2)."""
        return self._Beta2

    @Beta2.setter
    def Beta2(self, value: float):
        self._Beta2 = value

    @property
    def P_objective_switch(self) -> float:
        """float in [0,1]: probability that a construction step is guided by the
        time/completion pheromone matrix (tau1) instead of the congestion
        pheromone matrix (tau2). m-ACO4(1,m), Alaya et al."""
        return self._P_objective_switch

    @P_objective_switch.setter
    def P_objective_switch(self, value: float):
        self._P_objective_switch = value

    @property
    def Tau_min(self) -> float:
        """float: MAX-MIN Ant System lower pheromone bound (Lesch et al., 2023)."""
        return self._Tau_min

    @Tau_min.setter
    def Tau_min(self, value: float):
        self._Tau_min = value

    @property
    def Tau_max(self) -> float:
        """float: MAX-MIN Ant System upper pheromone bound (Lesch et al., 2023)."""
        return self._Tau_max

    @Tau_max.setter
    def Tau_max(self, value: float):
        self._Tau_max = value

    @property
    def Max_iter_wo_improvement(self) -> int:
        """int: iterations without a global-best improvement before triggering a cataclysm."""
        return self._Max_iter_wo_improvement

    @Max_iter_wo_improvement.setter
    def Max_iter_wo_improvement(self, value: int):
        self._Max_iter_wo_improvement = value

    @property
    def Max_cataclysms(self) -> int:
        """int: maximum number of pheromone resets before giving up on further resets."""
        return self._Max_cataclysms

    @Max_cataclysms.setter
    def Max_cataclysms(self, value: int):
        self._Max_cataclysms = value
