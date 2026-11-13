# Stress test design for the exact models (mono and split)

> Status: **implemented on 2026-09-23 and run on the split**. Results in section 0. The rest of the document is the original proposal with its calibration. The content is the proposal as written.

> ⚠ **Written before later changes.**
> - **Numbering.** The stress suite has 19 scenarios. Tests 09, 10 and 11 in this document are now **04, 05 and 07**.
> - **The metric closure was removed** from the code on 2026-09-23; the references to `OPP_STAGE1_METRIC_CLOSURE` below are historical.
> - **The `<= 1` limit does change answers in one case** found later: a batch that saturates a small grid (26 orders on 4×4) becomes infeasible. It does not affect the tests proposed here, which start at 7×7.
> - The tool's flags are now in English (`--points`, `--hard-cap`, ...); see `experiments/exact/README.md`.

## 0. Results of the run (split, 2026-09-23)

`python -m tests.run_suite opp_split stress --id 09 10 11 --timeout-minutes 40`, sequentially and with the machine alone. CSV: `results/opp_split/stress/output_opp_split_stress_tests_20260923_142920.csv`.

| Test | Warehouse | Status | **Total** | Stage 1 | Stage 2 | Objective | SLA | Peak RAM |
|---|---|---|---|---|---|---|---|---|
| 09 | 7×7 | ok | **2.0 min** | 6 s | 117 s | 79,046.86 | 67.9% | 148 MB |
| 10 | 13×13 | ok | **5.9 min** | 224 s | 128 s | 127,210.11 | 67.9% | 261 MB |
| 11 | 15×15 | ok | **28.5 min** | 1485 s | 222 s | 143,318.61 | 67.9% | 261 MB |

- **All three pass, with no timeouts.** 15×15 **did not turn out to be the ceiling**: it solves within the runner's 40 min, so it takes the 40-minute rung planned for the next phase.
- **None lands in the 10–20 min band**: the jump from 13×13 to 15×15 skips it. Candidate to cover it: **14×14**, not measured.
- **Stage 1 is what grows** (6 → 224 → 1485 s); Stage 2 stays nearly flat (117 → 128 → 222 s). With this profile, on large warehouses the cost is routing — the stage the split decomposes per batch.
- **Exactly the same objective as the calibration** on 7×7 and 13×13, but both stages ran almost exactly twice as fast. The "solo" calibration started after half an hour of 16 parallel processes, with the laptop hot. **On this machine absolute times can vary ~2x between runs**; to cite them in the thesis, repeat and report the conditions.
- SLA 67.9% in all three, on the formula of section 2.2.

## 1. Summary

**Three new stress tests (09, 10, 11), in split and in mono, with a realistic profile and a single varying axis: warehouse size.**

| Test | Warehouse | Split, measured alone | Role |
|---|---|---|---|
| 09 | 7×7 | 3.6 min | comfortable regime; direct comparison with mono |
| **10** | **13×13** | **11.8 min** | **the 10–20 min band test** |
| 11 | 15×15 | Stage 1 > 25 min | the ceiling |

Common profile: 6 batches over 3 pickers, 156 orders, grid weights 4/5, speeds in two bands (0.8 and 1.2), no closure.

Three things worth knowing before confirming:

1. **Only one size falls in the 10–20 band.** With realistic speeds, Stage 2 does not tolerate more than two batches per picker, so size has to come from the warehouse; and Stage 1 jumps from 11.8 min on 13×13 to more than 25 on 15×15. 14×14 is not measured and is the candidate for a second test in the band.
2. **Mono, measured on the same 7×7 instance, did not reach the optimum in 25 minutes** (144% gap). The split solved it. This is the 1:1 comparison that backs the thesis; the other two sizes will confirm it when the suite runs.
3. **"Large" is relative here**: 156 orders and 169 locations is larger and much more realistic than the only two stress tests that pass today (100 orders on 10×10 and 60 on 7×7, both all uniform), but it is what the exact model allows with realistic crews and aisles.

---

## 2. What we know

Everything in this section is measured. Where something is a hypothesis, it says so.

### 2.1 What drives each stage

The split's two stages have **distinct and independent** difficulty drivers, and that is what makes it possible to design large scenarios that still solve.

**Stage 1 (routing, one MIP per batch)**

| Depends on | Does not depend on |
|---|---|
| distinct locations per batch (≈ orders per batch minus collisions) | number of pickers |
| grid size, **by itself** | picker speeds |
| number of batches (linear: one solve per batch) | due dates |

Scaling measured on 2026-09-22 with 6 batches and 26 orders per batch, **weights 4/4, with closure, two processes in parallel**:

| Grid | Vertices | Locations/batch | Stage 1 |
|---|---|---|---|
| 7×7 | 49 | 18-22 | 12.9 s |
| 10×10 | 100 | 21-26 | 50.4 s |
| 15×15 | 225 | 24-26 | 464.4 s |

With this proposal's profile (weights 4/5, no closure, measured alone) 15×15 **did not finish Stage 1 in 25 minutes** — see section 4. That is three differences at once, and which one produces the jump is not identified; it is the warning of section 2.5 in action.

The grid costs by itself, not only through the locations: reaching ~31 locations per batch by growing the orders (7×7, 50 orders/batch) costs 46 s, and reaching ~25 by growing the grid (15×15) costs 464 s. The mechanism is not identified.

**Stage 2 (assignment and sequencing)**

| Depends on | Does not depend on |
|---|---|
| batches/pickers ratio | grid size (except through route times) |
| speed heterogeneity | edge weights |
| number of pickers (not monotone) | |

- With `|B| = |P|` each batch takes its own picker and sequencing does not activate: it is an assignment problem.
- With `|B| > |P|` sequencing activates. With uniform speeds: 6 batches/2 pickers 8 s, 6/3 17.7 s, 6/4 26.3 s; **8 batches/2 pickers does not finish in 5 min**.
- Difficulty peaks at intermediate ratios, not at the extremes (6 batches: 2P 14.5 s → 3P 31.2 s → 4P 43.1 s → 5P 37.4 s → 6P 17.1 s, at 50 orders/batch).

**Which axis breaks where** (one axis at a time from 6 batches / 2 pickers / 26 orders / 7×7):

| Axis | Range | Breaks | Stage |
|---|---|---|---|
| Orders per batch | 10 → 50 | never | — |
| Pickers | 2 → 6 | never (not monotone) | — |
| **Batches** | 6 → 8 | **at 8** | 2 |
| **Grid** | 7×7 → 15×15 | **at 15×15** | 1 |

### 2.2 SLA is set by the objective function, not by the due dates

With due dates spread and reachable:

**SLA = (N_b + W_c) / (2 · N_b)**, with N_b = orders per batch.

Delaying a batch costs `W_c` per unit of time and saves one unit for each order that would still arrive early, so the model delays each batch until #early − #late ≈ W_c. Verified at 8 sizes (10 to 50 orders per batch), all within 1.7 points.

Consequences for the design:
- **Due dates need no calibration**: it is enough that they are spread and reachable. With 26 orders per batch, SLA comes out ~67%.
- The model is **just-in-time**: it inserts idle time on purpose. It is an earliness/tardiness objective, a notoriously hard class of scheduling. Relevant for optimizing Stage 2.

### 2.3 Realistic speeds change the sizing

A real crew has two or three speed bands, not one per person. Fixed instance (6 batches, 26 orders/batch, 7×7), varying only how many distinct speeds there are:

| Pickers | Uniform | 2 tiers | 3 tiers |
|---|---|---|---|
| 3 | 17.7 s | 134.2 s | 113.5 s |
| 4 | 26.3 s | > 300 s | > 300 s |
| 6 (= batches) | 7.2 s | 110.4 s | > 3000 s |

- The step is from 1 to 2 speeds; more tiers add nothing.
- **Every edge measured before (8 batches, 15×15) was measured with uniform speeds**, that is, on the artificially easy case. With realistic speeds Stage 2 reaches considerably less.

### 2.4 Current state of the stress suite

| Test | Configuration | split | mono |
|---|---|---|---|
| 01 | 30B/30P, 750 orders, 25×25 | timeout | timeout |
| 02 | 30B/30P, 750 orders, 100×100 | timeout | out of memory |
| 03 | 20B/20P, 600 orders, 100×100 | timeout | ZIMPL out of memory |
| 04 | 25B/25P, 100 orders, 10×10 | timeout | — |
| 05 | 10B/10P, 100 orders, 10×10 | **ok (~45 s)** | — |
| 06 | 25B/10P, 100 orders, 10×10 | timeout | — |
| 07 | 10B/25P, 100 orders, 10×10 | timeout | — |
| 08 | 40B/1P, 320 orders, 7×7 | timeout | — |
| 09* | 6B/2P, 60 orders, 7×7 | **ok (39 s)** | — |

\* version of the ladder designed on 2026-09-22, with uniform speeds and weights.

Six degeneracies found in those scenarios:

| # | Degeneracy | Type |
|---|---|---|
| 3 | Identical, unreachable due dates (`T_due_n = 30`) | performance |
| 1 | `\|P\| > \|B\|` (test 07) | coverage |
| 2 | `\|B\| = \|P\|` in 5 of 8 | coverage |
| 4 | Uniform `V_p` everywhere | coverage |
| 5 | Empty batches (functional 30) | coverage |
| 6 | Uniform grid weights | coverage |

### 2.5 Measurement discipline

- **Same instance → same tree.** SCIP is deterministic: two runs of the same configuration gave exactly 250,037 nodes and times within 0.7%.
- **Conclusions do not transfer**, not even to the neighbouring instance. Every time a result was generalized from one point to another, a controlled run refuted it (pseudocost branching, "neutral" speeds, asymmetric weights moving the grid edge). **That is why every test proposed here is measured on its own instance**, not extrapolated.
- **SCIP's `limits/time` is not a hard cap** (300 s ended at 3079 s). The test suite is protected because the runner kills the process tree; the calibration tool now does too.

---

## 3. Design principles

Each principle comes from a measurement in section 2.

1. **A fixed realistic profile in every test.** Grid weights 4/5 (aisles do not vary much), speeds in **2 bands** (0.8 and 1.2: a crew of similar age, same cart, but not identical), 26 orders per batch. None of the six degeneracies: `|B| > |P|`, no empty batches, due dates spread and reachable.

2. **Vary a single axis between tests.** That way the test where each model stops solving is directly comparable, and the difference can be attributed. The chosen axis is **warehouse size**.

3. **Size comes from Stage 1, not Stage 2.** With realistic speeds, Stage 2 does not tolerate more than ~2 batches per picker: 6 batches/3 pickers solves, but 6/4, 7/3 and 8/3 run past 25 minutes. Stage 1, on the other hand, scales more predictably with the grid, and it is where the split's decomposition has a structural advantage over mono.

4. **The scheduling shape stays fixed: 6 batches over 3 pickers.** Its Stage 2 showed a difficulty that is stable against grid size (321,137 nodes on 7×7, 314,331 on 13×13), so each test's cost is governed by the grid, which is what we want to vary.

5. **No metric closure.** At these sizes the closure falls back on 67–100% of batches and ends up slower (7×7: +75%; 13×13: +9%). It is also the current default in `.env`. The fallback seems to come from which shortest path Dijkstra picks among many tied ones, so it could be fixed technically; meanwhile, it stays out.

6. **Uncalibrated due dates.** SLA is set by the objective: with 26 orders per batch it comes out ~67%, within the range where both earliness and tardiness are exercised.

7. **Times calibrated one measurement at a time.** The CPU is a hybrid laptop one: in parallel, times inflate 2-3x. The times in section 5 were measured with the machine alone, which is how the runner runs.

## 4. Calibration

Tool: `python -m experiments.exact.exploration --study 05_realistic_calibration --points <file>.json` (the flags were Spanish when this ran). Each configuration runs in its own process with a 25-min hard kill covering the whole process tree. Points and results in `experiments/exact/studies/05_realistic_calibration/` (index in `experiments/exact/README.md`).

**Absolute times (one measurement at a time, no closure)** — `solo_20260923_*.csv`:

| Warehouse | Locations/batch | Stage 1 | Stage 2 | **Total** | Stage 2 nodes | SLA |
|---|---|---|---|---|---|---|
| 7×7 | 18-22 | 9.6 s | 204.2 s | **3.6 min** | 321,137 | 67.9% |
| 13×13 | 23-26 | 445.3 s | 263.8 s | **11.8 min** | 314,331 | 67.9% |
| 15×15 | 24-26 | > 1500 s | — | **Stage 1 > 25 min** | — | — |

**Mono on the same 7×7 instance** (in parallel, so its time is inflated; its gap is not): at 25 min, `timelimit` with a **144.3% gap**. The split solved it to optimality.

**Scheduling shapes discarded** (7×7, in parallel, 25 min): 6 batches/**4** pickers → 1.09% gap; **7** batches/3 → 2.6%; **8** batches/3 → 9.48%. None finished.

**Controls that validate the measurements:**
- With and without the closure, Stage 2 gave exactly the same node count (321,137 on 7×7, 314,331 on 13×13): the closure is exact and the whole difference is in Stage 1.
- The same instance measured alone and in parallel gave exactly the same tree, 2.3x faster alone: contention inflates the clock, it does not change the problem.
- SLA was 67.9% in all, on the formula (67.3%).

## 5. Proposed tests

**Profile common to all three** (the only thing that varies is the warehouse):

| Parameter | Value | Why |
|---|---|---|
| Batches / pickers | 6 / 3 | 2 batches per picker: sequencing activates; more than that does not solve with realistic speeds |
| Orders | 156 (26 per batch) | SLA ~67%: both earliness and tardiness are exercised |
| Grid weights | vertical 4, horizontal 5 | similar aisles, not identical |
| Speeds | 2 bands: 0.8 and 1.2 | realistic crew |
| Closure | off | it is the default and at these sizes it is slower |

**Generator call** (identical in split and mono, only `side` changes):

```python
designed_stress_scenario(6, 3, 156, side, side,
                         speed_spread=0.2, speed_tiers=2,
                         vertical_weight=4, horizontal_weight=5)
```

| Test | Warehouse | Split (measured alone) | What it shows |
|---|---|---|---|
| **09** | 7×7 (49 locations) | 3.6 min | Comfortable regime. Direct comparison: the split solves fast; mono, measured, does not get there in 25 min. |
| **10** | 13×13 (169 locations) | **11.8 min** | **The 10–20 min band test.** A realistic, solvable instance. |
| **11** | 15×15 (225 locations) | Stage 1 > 25 min | **The ceiling.** Probably exhausts the runner's 40 min; marks where the exact approach stops reaching with this profile. |

Assertions: the same as today (`assert_stress_pipeline`): optimal or feasible status, routes covering the required locations, every batch with a picker, no overlap. None is added or removed.

**For the next phase (40 minutes or the cap):**
- **6 batches / 4 pickers on 7×7** with the same profile: it was at a 1.09% gap after 25 min measured in parallel. Run alone it might fit in 40. It is a Stage-2-dominated test, so it also serves as a reference for any attempt to optimize it.
- **14×14** with the same profile: not measured. It sits between 11.8 min and more than 25; if a second test in the band is wanted, it is the candidate.

## 6. What to do with the existing tests

| Tests | Proposal | Why |
|---|---|---|
| 01–03 (plain grids) | **Leave them as they are** | They keep the same sizes and have history in `results/`. Their degeneracies are listed above; they are not used as evidence of realistic scalability. |
| 07 (10 batches, 25 pickers) | **Keep it with a note** in the docstring and exclude it from comparisons | It is the degenerate `\|P\| > \|B\|` case. Deleting it throws away evidence and breaks the continuous numbering. |
| 09, 10, 11 (2026-09-22 version) | **Replace their scenario** with the one in section 5 | They use uniform speeds and weights. They exist in the repo but are uncommitted; the change is only the `designed_stress_scenario` call and the docstring, in split and in mono. |

Already implemented (uncommitted), because you asked for it explicitly: `speed_tiers` in `designed_stress_scenario` and the calibration tool with hard kill.

## 7. Risks and what we do not know

- **Stage 2 is very sensitive to the instance.** Changing the seed, the weights or the separation between bands moves its cost a lot (0.7/1.3 with weights 4/4 gave 134 s; 0.8/1.2 with weights 4/5 gave 486 s, at the same size). **If the generator changes, these times have to be recalibrated.** That is why each proposed test is measured on its own instance.
- **The times are from this laptop.** On another machine the absolute values change; node counts hold for the same SCIP version.
- **Mono is not measured at the proposed sizes running alone.** The only measurement: on 7×7, running in parallel, after 25 min it had a 144% gap; the split finds that same optimum in 3.6 min alone (8.3 in parallel). That mono does not solve the larger sizes is an inference; the suite run will confirm it.
- **If the closure is enabled** (`OPP_STAGE1_METRIC_CLOSURE=1`), Stage 1 changes: +9% on 13×13, +75% on 7×7. No need to recalibrate to decide, but the times in section 5 are without the closure.
- **`<= 1` does not affect this proposal.** Removing it was tried (split only, on temporary copies): same objectives in the 11 route functional tests and the same route times on 7×7 and 13×13, with speed improving at one size and worsening at the other. It is not a performance lever and does not change answers.
- **What limits Stage 1 on large warehouses is not identified.** The jump from 13×13 (445 s) to 15×15 (more than 1500 s) is much steeper than the growth in locations per batch suggests (23-26 → 24-26). To extend the ladder, that would have to be understood first.
- **The 40-minute rung, for later.** The best measured candidate is 6 batches / **4** pickers on 7×7: after 25 min (in parallel) it had a gap of only 1.09%. Run alone, it might finish within 40. It is also a Stage-2-dominated test, useful as a reference if optimizing it is attempted.
