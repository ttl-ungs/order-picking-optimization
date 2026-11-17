# DTOs

Data Transfer Objects: every input and output of a model travels in one of these, never as loose primitives.

| DTO | Holds |
| --- | --- |
| `opp/model_dto.py` — `ModelDTO` | The instance structure: orders `N`, batches `B`, pickers `P`, the location graph, `start_time`. |
| `opp/solve_model_dto.py` — `SolveModelDTO` | The parameters of the problem: weights (`W_c`, `W_pen`, `W_e`, `W_t`), `C_n`, `C_v`, the visit matrix `A_ni`, `B_nb`, the times `T_travel`, `T_setup`, `T_pick` and the service time per location `S`, `T_due_n`, `M`, and `Seed` for the heuristics. |
| `hc/solve_hc_model_dto.py` — `SolveHCModelDTO` | `SolveModelDTO` plus the Hill Climbing budget (`Max_it`, `Max_imp`, `Max_time`) and the picker speeds `V_p` and cold-chain limit `T_cold`. |
| `aco/solve_aco_model_dto.py` — `SolveAcoModelDTO` | `SolveModelDTO` plus the colony (`A_ants`, `Max_it`, `Alpha`, `Beta`, `E`, `Q`, `Max_time`) and the picker speeds `V_p` and cold-chain limit `T_cold`. |
| `opp/solve_result.py`, `opp/solution_record_dto.py`, `opp/zimpl_solution_record_dto.py` | The outcome of a solve and the records saved for verification. |
| `verification/compliance_report_dto.py` | The outcome of checking a heuristic's solution against OPP-Mono. |
