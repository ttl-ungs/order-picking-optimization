# Usage examples

Small runnable scripts showing how to call each heuristic model directly
(build the DTOs, attach an `OutputHandler`, call `solve()`). From the repo root:

```bash
python examples/opp_hc_2_usage.py
```

Available for `opp_hc_1`, `opp_hc_2`, `opp_hc_3`, `opp_aco_1`, `opp_aco_2` and `opp_aco_3`
(`opp_hc_3`/`opp_aco_3` use the same two-picker bottleneck instance so their congestion
results can be compared directly).
