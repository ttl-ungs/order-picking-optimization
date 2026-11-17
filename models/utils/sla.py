"""
Service level of a heuristic's solution: the share of scheduled orders that
finished on time or early.
"""

from typing import Dict, Optional


def sla_on_time_pct(tardiness: Dict[str, float]) -> Optional[float]:
    """
    % of orders with tardiness <= 0. None if `tardiness` is empty (no order
    was scheduled), so a CSV row reports "no data" rather than a misleading 0%.
    """
    if not tardiness:
        return None
    on_time = sum(1 for t in tardiness.values() if t <= 1e-6)
    return on_time / len(tardiness) * 100
