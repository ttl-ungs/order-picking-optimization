from dtos.hc.solve_hc_model_dto import SolveHCModelDTO


class SolveHC4ModelDTO(SolveHCModelDTO):
    """
    DTO for opp_hc_4: adds picker speed and cold-chain hyperparameters on
    top of opp_hc_2's (SolveHCModelDTO) fields - the Hill Climbing
    counterpart of opp_v5_2_split's opp_model_v5_2_split_stage2_scheduling.zpl additions over opp_v4.

    Unlike opp_hc_3, congestion between concurrent pickers is intentionally
    left out here (see models/opp_hc_4/opp_hc_4.py header for why) - the two
    extensions are orthogonal (opp_hc_3 keeps opp_v4's fixed d_b, this
    one replaces it with a per-picker t_exec_pb), so they don't need to be
    combined into a single model.

    Execution time per (picker, batch) mirrors opp_v5_2_split's t_exec_pb:
        t_exec_pb[p, b] = fixed_time(b) + route_time(b) / V_p[p]
    where fixed_time(b) = B_setup + B_picking * sum(C_n over b's orders)
    does NOT depend on picker speed (setup/picking are manual work, not
    walking), and route_time(b) = B_time * travel_distance + service_time
    is the part scaled by how fast the picker walks/scans (same split as
    opp_model_v5_2_split_stage2_scheduling.zpl lines ~72-81).
    """

    def __init__(self):
        super().__init__()
        self._V_p: dict = {}
        self._T_frio_max: float = float("inf")

    @property
    def V_p(self) -> dict:
        """dict {picker: speed}. A picker missing from this dict defaults to
        speed 1.0 (see opp_hc_4's _picker_speed) - the same default opp_v5_2_split's
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
