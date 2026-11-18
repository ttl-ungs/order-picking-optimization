from typing import Optional


class ZimplSolutionRecordDTO:
    """
    Instance and solution of a run of an exact model (opp_mono, opp_split):
    the counterpart of SolutionRecordDTO.

    `scenario` is the dict given to dat_files_builder.build_dat_files (the
    instance as the .dat files were written) and `values` are SCIP's variable
    values. opp_split's record is the one of Stage 2; add_stage1_values adds
    the routes (z_ijb) and r_b of Stage 1.

    Holds references only; it is serialized after the test, and only when the
    runner keeps solutions (WRITE_SOLUTIONS, verification/solution_store.py).
    """

    def __init__(self, zpl_path: str, scenario: Optional[dict], status: str, objective: Optional[float], values: dict):
        self._zpl_path = zpl_path
        self._scenario = scenario
        self._status = status
        self._objective = objective
        self._values = values
        self._stage1_values: Optional[dict] = None

    @property
    def zpl_path(self) -> str:
        return self._zpl_path

    @property
    def scenario(self) -> Optional[dict]:
        return self._scenario

    @property
    def status(self) -> str:
        return self._status

    @property
    def objective(self) -> Optional[float]:
        return self._objective

    @property
    def values(self) -> dict:
        return self._values

    @property
    def stage1_values(self) -> Optional[dict]:
        return self._stage1_values

    def add_stage1_values(self, values: dict) -> None:
        self._stage1_values = values
