from dtos.aco.solve_aco_model_dto import SolveAcoModelDTO


class SolveAco4ModelDTO(SolveAcoModelDTO):
    """
    DTO for opp_aco_4: adds picker speed and cold-chain hyperparameters on
    top of opp_aco_2's (SolveAcoModelDTO) fields - the ACO counterpart of
    opp_hc_4 (itself the Hill Climbing counterpart of opp_v5_2_split's
    opp_model_v5_2_split_stage2_scheduling.zpl additions over opp_v4).

    Unlike opp_aco_3, congestion between concurrent pickers is intentionally
    left out here (see models/opp_aco_4/opp_aco_4.py header for why) - the
    two extensions are orthogonal (opp_aco_3 keeps opp_v4's fixed t_exec_b,
    this one replaces it with a per-picker t_exec_pb), so they don't need
    to be combined into a single model. Field semantics are identical to
    dtos/hc/solve_hc_4_model_dto.py's:

        t_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]

    where fixed_time(b) = B_setup + B_picking * sum(C_n over b's orders)
    does NOT depend on picker speed (setup/picking are manual work, not
    walking), and route_time(b) = B_time * travel_distance + service_time
    is the part scaled by how fast the picker walks/scans.
    """

    def __init__(self):
        super().__init__()
        self._V_p: dict = {}
        self._T_frio_max: float = float("inf")
        self._Max_time: float = 600.0

    @property
    def Max_time(self) -> float:
        """Wall-clock budget (seconds) for the ant colony loop -- the ACO
        counterpart of SolveHCModelDTO.Max_time. When it runs out, the
        current iteration stops building ants, its ants still update the
        best solution, and the run ends. It never ends a run that has no
        cold-chain-compliant solution yet (see opp_aco_4's solve()), so it
        can't turn a solvable instance into a false "infeasible". Default
        600 s: above every realistic_crew stress run measured on
        2026-09-27 (<= ~390 s), so it only bounds the very large instances
        -- e.g. the 100x100 migrated grid, where one iteration alone takes
        ~5 min and the full 60 would take ~5 h."""
        return self._Max_time

    @Max_time.setter
    def Max_time(self, value: float):
        self._Max_time = value

    @property
    def V_p(self) -> dict:
        """dict {picker: speed}. A picker missing from this dict defaults to
        speed 1.0 (see opp_aco_4's _picker_speed) - the same default opp_v5_2_split's
        migrated_case.py uses to make the cold-chain/speed extensions a no-op
        for scenarios that don't care about them."""
        return self._V_p

    @V_p.setter
    def V_p(self, value: dict):
        self._V_p = value or {}

    @property
    def T_frio_max(self) -> float:
        """Cold-chain deadline (seconds): the max allowed t_exec_pb[p, b]
        for a (picker, batch) pair to remain eligible for that assignment.
        Default +inf disables cold-chain entirely (every picker is eligible
        for every batch), matching opp_v5_2_split's migrated-baseline behavior."""
        return self._T_frio_max

    @T_frio_max.setter
    def T_frio_max(self, value: float):
        self._T_frio_max = value
