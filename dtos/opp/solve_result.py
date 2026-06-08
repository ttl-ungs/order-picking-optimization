class SolveResult:
    def __init__(self, status: str, output, elapsed: float, params: dict):
        self.status = status
        self.output = output
        self.elapsed = elapsed
        self.params = params

    def __iter__(self):
        return iter((self.status, self.output))

    def to_csv_row(self) -> dict:
        return {
            "model_time": self.elapsed,
            **self.params,
        }
