# OPP-Mono

Exact monolithic formulation in ZIMPL, solved with SCIP: routing, assignment and sequencing are decided
together in one MIP (`opp_mono.zpl`). It solves the same problem as OPP-Split and must reach the same
optimum wherever both finish.

- Heterogeneous picker speeds: the speed scales only the route time, so a batch lasts `F_b[b] + r_b[b] / V_p[p]` (setup and picking are not scaled).
- Cold chain: a batch can go to a picker only if its duration at that picker's speed is at most `T_cold`.
- The objective is taken on `c_b` and the earliness/tardiness rows exist only for the pairs `(n, b)` with `B_nb = 1` (the same formulation improvements as OPP-Split).
- With every `V_p = 1` and a very large `T_cold` (the defaults written by `dat_files_builder.py`) it reduces to the problem without speeds or cold chain.

It is also the single source of truth for the constraints: `verification/mono_compliance.py` fixes a
heuristic's solution on this model's own variables and lets SCIP decide whether it is feasible.

Tests: `tests/opp_mono/`. Requires the `zimpl` binary on the `PATH`. Run a case with
`python -m tests.run_suite opp_mono functional --id 24`.
