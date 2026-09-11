"""
Shared SLA (nivel de servicio) computation for every Hill Climbing/ACO
model (hc_2/3/4, aco_2/3/4): % of orders that finished on time or early
(tardiness <= 0), out of every order that actually got scheduled (has a
tardiness entry in solution_info).
"""

from typing import Dict, Optional


def sla_on_time_pct(tardiness: Dict[str, float]) -> Optional[float]:
    """
    % of orders with tardiness <= 0 (on time or early). None if `tardiness`
    is empty (no order was ever scheduled -- e.g. an all-empty-batches
    instance), so a CSV row reports "no data" rather than a misleading 0%.
    """
    if not tardiness:
        return None
    on_time = sum(1 for t in tardiness.values() if t <= 1e-6)
    return on_time / len(tardiness) * 100
