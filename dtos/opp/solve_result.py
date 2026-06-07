class SolveResult:
    def __init__(self, status: str, output, elapsed: float, solver_time: float, params: dict):
        self.status = status
        self.output = output
        self.elapsed = elapsed
        self.solver_time = solver_time
        self.params = params

    def __iter__(self):
        return iter((self.status, self.output))

    def to_csv_row(self) -> dict:
        return {
            "model_time": self.elapsed,
            "solver_time": self.solver_time,
            **self.params,
        }
