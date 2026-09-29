class SolveResult:
    def __init__(self, status: str, output, elapsed: float, params: dict, solution_record=None):
        self.status = status
        self.output = output
        self.elapsed = elapsed
        self.params = params
        # Optional SolutionRecordDTO (instance + solution) for models whose
        # solutions can be re-checked by verification/ -- see
        # dtos/opp/solution_record_dto.py. None for every other model.
        self.solution_record = solution_record

    def __iter__(self):
        return iter((self.status, self.output))

    def to_csv_row(self) -> dict:
        return {
            "model_time": self.elapsed,
            **self.params,
        }
