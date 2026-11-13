# OPP-Split

Exact two-stage formulation in ZIMPL, solved with SCIP. It is the reference of the comparisons.

| File | Stage | Decides |
| --- | --- | --- |
| `opp_split_stage1_routing.zpl` | 1 | The route of each batch: the shortest path (travel + service time) that visits its required locations. Batches do not interact, so each one is independent of the picker and of the sequence. Output: `r_b[b]`. |
| `opp_split_stage2_scheduling.zpl` | 2 | Which picker runs each batch and in which order, with the route times of Stage 1 as data: `T_exec_pb[p, b] = F_b[b] + R_b[b] / V_p[p]`. Controls tardiness and earliness, and the cold chain by restricting the domain of `x_pb` to the eligible pairs `PB_elig`. |
| `utils/cold_chain_validation.py` | pre-solve | Detects batches without any eligible picker (ZIMPL rejects an empty sum at compile time) and non-positive speeds, shared by OPP-HC and OPP-ACO. |

- The decomposition is exact: Stage 1 does not depend on Stage 2, and Stage 2 only needs the route times.
- Stage 1 is solved one batch at a time (`tests/opp_split/stage1_decomposition.py`), in parallel with `OPP_STAGE1_WORKERS` workers when there are more than four batches.
- The `.zpl` files read `../dat_files/*.dat`, which the tests write with `tests/infra/zimpl/dat_files_builder.py`.
- Requires the `zimpl` binary on the `PATH`.

Tests: `tests/opp_split/`. Run a case with `python -m tests.run_suite opp_split functional --id 24`.
