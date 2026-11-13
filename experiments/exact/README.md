# Experiments on the exact models

Exploration that is not tests: sweeps and calibrations to understand where and why each model stops solving, and to design the stress tests. A test answers "does this instance solve?"; a study gives the curve.

- `exploration.py` — the tool for sweeps, point lists and the split-vs-mono frontier. Each point runs in its own process and is killed from outside when it exhausts `hard_cap_s`: SCIP's `limits/time` is not a hard limit. It writes into the study it is given:

  ```
  python -m experiments.exact.exploration --study 08_name --points experiments/exact/studies/08_name/points.json
  ```

  A `pair` point solves the same instance with the split and then with the monolithic model, and measures the monolithic run against the split's proven optimum (the two models share it). That separates finding a good solution from proving it optimal. See the module docstring for every column.
- `reports/` — the generators of the four ConTeXt reports: the two explorations (`docs/thesis/opp_split_exploration.tex`, `docs/thesis/opp_mono_exploration.tex`, from the study CSVs) and the two comparisons (`docs/thesis/opp_mono_vs_opp_split_comparison.tex` and `docs/thesis/opp_split_vs_heuristics_comparison.tex`, from the consolidated result CSVs). Each one fills the `%%FIG:id%%`, `%%TABLE:id%%` and `%%NUM:id%%` markers of its `*_template.tex`. The two comparisons use the same base, `comparable_set.py`: the instances split, opp_hc and opp_aco share according to `results/comparability/comparability_split_vs_heuristics.csv`. Edit the template, not the generated `.tex`, then regenerate and compile:

  ```
  python -m experiments.exact.reports.build_split_exploration
  python -m experiments.exact.reports.build_mono_exploration
  python -m experiments.exact.reports.build_functional_comparison
  python -m experiments.exact.reports.build_heuristics_comparison
  cd docs/thesis && context opp_split_exploration.tex && context opp_mono_exploration.tex
  cd docs/thesis && context opp_mono_vs_opp_split_comparison.tex && context opp_split_vs_heuristics_comparison.tex
  ```
- `studies/NN_name/` — one directory per question, holding the points or scripts that were run and the CSVs they produced. CSV names keep the date and time of the run.

Results live here and not in `results/<model>/<tier>/` on purpose: `analysis/load.py` globs that pattern and would take them for test runs.

The full conclusions are in the two reports: `docs/thesis/opp_split_exploration.tex` (studies 01–07 and 12) and `docs/thesis/opp_mono_exploration.tex` (studies 08–11); this index only summarizes and points.

## Studies

| # | Model | Question | Conclusion |
|---|---|---|---|
| 01 | split | Which dimension breaks first? | Batches break Stage 2 (at 8); warehouse size breaks Stage 1 (15×15). Orders per batch and pickers did not break. |
| 02 | split | Are uniform grid weights a degeneracy? | Yes, for coverage. Weights 2/6 speed Stage 1 up to 3.7x on 7×7, but the advantage is gone at 15×15: not an optimization. |
| 03 | split | Do distinct picker speeds make it harder? | All distinct on a healthy scenario: no. In bands, like a real crew: going from 1 to 2 speeds costs ~7x in Stage 2, and 4 pickers do not solve in 5 min. |
| 04 | both | Does the tool's hard kill work? | Yes: it kills the process tree and records the stage each point died in. |
| 05 | split | Which realistic profile lands in 10–20 min? | Solo: 7×7 3.6 min, 13×13 11.8 min, 15×15 > 25 min (Stage 1). Mono on 7×7: 144% gap at 25 min. Stress tests 04–07 came from here. |
| 06 | split | Does the metric closure help on realistic warehouses? | No: 67–100% of batches fall back to the full graph. Removed from the code. |
| 07 | split | Does the `<= 1` per-vertex limit change the answers or the time? | It does not change the routes (11 route functional tests and two stress scales identical). Time: faster at one scale, slower at the other. |
| 08 | pair | Where does the monolithic model stop proving the optimum, on the realistic profile? | At 10 min it closes up to 3 batches on 6×6, 4 on 5×5, 6 on 3×3; the split closes all of those. Mono finds solutions within 1% early but its dual bound stalls at 88–97%. |
| 09 | pair | The split studies' own instances (01, 02, 03), solved by both | Same split optima as the original studies. Mono proves none in 300 s; in 7 of 15 it finds no feasible solution. |
| 10 | pair | Studies 01/02/03/07's questions at a scale mono solves (4 batches, 2 pickers, 5×5) | What hurts mono most: grid size, speed bands with 3 pickers, few orders per batch. All 25 mono optima match the split. |
| 11 | pair | The three failure points and test 04's exact instance, at a 40-min cap | From 10 to 40 min mono's dual bound barely moves (90% of the optimum in two points); only 6 batches on 5×5 closes (32 min, 8× the split). Test 04: solution 0.66% from the optimum, gap 143.5%. |
| 12 | split | How much does parallel Stage 1 (6 workers) speed up routing? Controlled A/B, Stage 1 only, ABBA order, machine alone | ×2.2 on 13×13 (242 → 110 s) and ×1.9 on 14×14 (403 → 213 s); repeats within 3%, identical routes. |

## How each one was run

Studies 01–07 ran before the tool recorded incumbents, memory and model size, so their CSVs have fewer columns; the commands below use the current flag names.

The `.py` scripts inside `studies/` are kept **as they were run**; their column names and labels match the CSVs. Several run their experiment when imported, so `scripts/check_repo.py` does not import them. The ones for 01 and 03 ran with the Stage 1 metric closure on: the closure no longer exists, so rerunning them solves on the full graph. Objectives come out the same, because the closure was exact; Stage 1 times do not.

- **01** — `sweep.py`: 6 batches / 2 pickers / 26 orders per batch / 7×7, one axis at a time, 300 s per solve; gives `sweep_axes_*.csv`. `sweep_orders_50.py` extends orders per batch from 32 to 50; gives `sweep_orders_extended_*.csv`. `exploration.py` grew out of these two and sweeps the same way from the same base, but its ranges differ (for example, it takes orders per batch up to 50 in one pass). To reproduce the CSVs as they are, use these scripts.
- **02** — `--weights 2,6` gives `asymmetric_weights_*.csv`; `--axes warehouse --base 6,2,26,7 --weights 2,6` gives `warehouse_size_weights26_*.csv`.
- **03** — `--speed-spread 0.3` gives `spread_speeds_*.csv`. `speed_tiers.py` gives `speed_tiers_*.csv`.
- **04** — `--points kill_points.json --parallel 3` gives `kill_check.csv`; with `kill_points_stage1.json`, `kill_check_stage1.csv`.
- **05** — `--points` with `round1.json` (4 in parallel), `round1b.json` (8 in parallel) and `solo.json` (one at a time). Only the `solo` times are valid as absolutes: the parallel rounds are inflated 2–3x by the hybrid CPU.
- **06** — `--points` over a closure on/off points file with `--parallel 6` gave `closure_realistic_grids_*.csv`; the points file was deleted along with the closure. `fallback_rate.py` measured how many batches fell back; it depends on the closure's code and no longer runs.
- **07** — `--points le1_stage1.json --parallel 6` gives `le1_stage1_*.csv`: Stage 1 only, with and without `<= 1`. `le1_functional_routes.py` ran the 11 route functional tests with and without `<= 1` and printed the results without saving a CSV.

Studies 08–11 ran one after another with `OPP_STAGE1_WORKERS=6`, but **not alone**: 08 and 09 alongside the split stress suite, 10 alongside the split suite and then the mono suite, 11 alongside the mono suite. Their absolute times are inflated; split/mono ratios within a pair are comparable.

- **08** — the monolithic frontier on the realistic profile (26 orders per batch, weights 4/5, two speed bands), two batches per picker, each point as a `pair`:

  ```
  python -m experiments.exact.exploration --study 08_mono_frontier --frontier --frontier-batches 1,2,3,4,6 --frontier-sides 3,4,5,6,7 --batches-per-picker 2 --orders-per-batch 26 --weights 4,5 --speed-spread 0.2 --speed-tiers 2 --hard-cap 600
  ```
- **09** — `--points points.json` in its directory: 15 `pair` points reproducing instances of studies 01, 02 and 03 (`hard_cap_s` 330, so SCIP's limit is 300 s as in those studies).
- **10** — `--points points.json` in its directory: 27 `pair` points around a 4 batches / 2 pickers / 5×5 base, one factor at a time.
- **11** — `--points points.json` in its directory: 4 `pair` points with `hard_cap_s` 2430 (a 40-minute SCIP limit), including test 04's exact instance.
- **12** — `--points points.json` in its directory: 8 `stage1_only` split points, tests 05 and 06's instances, alternating `stage1_workers` 1 / 6 / 6 / 1; run alone after stopping the mono stress suite.
