from dtos.opp.solve_result import SolveResult

_last_solve_result: "SolveResult | None" = None

def register(solve_result: SolveResult) -> None:
    global _last_solve_result
    _last_solve_result = solve_result


def get_last() -> "SolveResult | None":
    return _last_solve_result
