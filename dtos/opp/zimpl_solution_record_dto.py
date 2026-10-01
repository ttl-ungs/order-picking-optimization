from typing import Optional


class ZimplSolutionRecordDTO:
    """
    Instance + solution of an exact ZIMPL/SCIP model run (opp_v5_1_mono,
    opp_v5_2_split), the counterpart of SolutionRecordDTO for the heuristics.

    `scenario` is the dict handed to tests/infra/zimpl/dat_files_builder
    .build_dat_files (the instance exactly as the .dat files were written);
    `values` are SCIP's variable values of the solve that produced this
    record. opp_v5_2_split solves in two stages: its record is the Stage 2
    solve, and the split pipelines add the Stage 1 values (the routes,
    z_ijb, and r_b) with add_stage1_values once Stage 2 finished.

    Holds references only; serialization happens after the test finished,
    and only when the runner was asked to keep solutions (WRITE_SOLUTIONS,
    see verification/solution_store.py).
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
