from dtos.hc.solve_hc_model_dto import SolveHCModelDTO


class SolveHC3ModelDTO(SolveHCModelDTO):
    """
    DTO for opp_hc_3: adds the congestion hyperparameter on top of
    opp_hc_2's (SolveHCModelDTO) fields. Hill Climbing has no pheromones, so
    unlike opp_aco_3's multi-pheromone m-ACO4 architecture, congestion here
    is purely a pricing mechanism plugged into RouteEvaluator (see
    models/opp_hc_3/utils/route_evaluator.py and
    models/utils/congestion.py::CongestionTracker) - same underlying
    capacity-1 resource model, adapted from:
        Chen, F., Wang, H., Qi, C., & Xie, Y. (2013). An ant colony
        optimization routing algorithm for two order pickers with congestion
        consideration. Computers & Industrial Engineering, 66(1), 77-85.
    """

    def __init__(self):
        super().__init__()
        self._Min_dwell = 0.0  # minimum node occupancy/turnaround buffer

    @property
    def Min_dwell(self) -> float:
        """float: minimum node occupancy time (congestion turnaround buffer), even
        for zero-service-time nodes. See CongestionTracker.dwell()."""
        return self._Min_dwell

    @Min_dwell.setter
    def Min_dwell(self, value: float):
        self._Min_dwell = value
