class SolveResult:
    """Outcome of one solve: status, output graph, model time and the
    parameters that go to the results CSV."""

    def __init__(self, status: str, output, elapsed: float, params: dict, solution_record=None):
        self.status = status
        self.output = output
        self.elapsed = elapsed
        self.params = params
        # SolutionRecordDTO or ZimplSolutionRecordDTO (instance + solution),
        # for verification/; None when the model does not attach one.
        self.solution_record = solution_record

    def __iter__(self):
        return iter((self.status, self.output))

    def to_csv_row(self) -> dict:
        return {
            "model_time": self.elapsed,
            **self.params,
        }
