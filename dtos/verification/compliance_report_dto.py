from typing import List, Optional


class ComplianceReportDTO:
    """
    Outcome of checking one heuristic solution against opp_mono
    (verification/mono_compliance.py).

    Three layers, cheapest first:
      - prechecks: the solution re-evaluated in plain Python (arcs exist,
        no revisits, required locations covered, one picker per batch, cold
        chain, recomputed times/objective vs the reported ones, big-M
        validity). Each failure is one human-readable string.
      - level 1 (SCIP): routes, assignment and same-picker sequence fixed,
        times free -> are the heuristic's DECISIONS feasible in mono, and
        what is the best schedule for them (level1_obj <= heuristic_obj).
      - level 2 (SCIP): completion times fixed too -> is the EXACT reported
        solution feasible in mono, and does mono price it the same
        (level2_obj == heuristic_obj).

    verdict: "compliant" (prechecks clean, both levels feasible, objective
    matches), "violations" (anything else that was actually checked),
    "error" (the check itself could not run).
    """

    def __init__(self, test: str, model: str):
        self.test: str = test
        self.model: str = model
        self.verdict: str = "error"
        self.prechecks: List[str] = []
        self.notes: List[str] = []
        self.big_m_substituted: bool = False
        self.heuristic_obj: Optional[float] = None
        self.recomputed_obj: Optional[float] = None
        self.level1_status: Optional[str] = None
        self.level1_obj: Optional[float] = None
        self.level2_status: Optional[str] = None
        self.level2_obj: Optional[float] = None
        self.diagnosis: List[str] = []
        self.error: Optional[str] = None
        self.check_time: Optional[float] = None

    def to_csv_row(self) -> dict:
        return {
            "test": self.test,
            "model": self.model,
            "verdict": self.verdict,
            "heuristic_obj": self.heuristic_obj,
            "recomputed_obj": self.recomputed_obj,
            "level1_status": self.level1_status,
            "level1_obj": self.level1_obj,
            "level2_status": self.level2_status,
            "level2_obj": self.level2_obj,
            "big_m_substituted": self.big_m_substituted,
            "prechecks": " | ".join(self.prechecks),
            "diagnosis": " | ".join(self.diagnosis),
            "notes": " | ".join(self.notes),
            "error": self.error,
            "check_time": self.check_time,
        }
