# Documentation index

| Where | What |
| --- | --- |
| `thesis/` | LaTeX/ConTeXt sources and PDFs of the thesis material (`models`, `opp_model_v4`, `opp_v5` (historical), `opp_v5_models` (unified v5.1 mono + v5.2 split), `opp_v5_1_mono_vs_opp_v5_2_split_comparison`, `opp_v5_2_split_vs_heuristics_comparison` (split against hc_4 and aco_4 on the instances the three share), `opp_v5_2_split_exploration` (what drives each stage's cost, from the `experiments/opp_v5/studies/` data), `opp_v5_1_mono_exploration` (where the monolithic model stops proving the optimum, measured against the split on the same instances), `opp_v4_vs_opp_v5_comparision`, `algorithm_advances_31_08_2026`, `algorithm_results`) and `results_outline.md`, the outline of the results section (every number and finding behind it). Figures are read from `analysis/output/`. |
| `guides/` | `context_style_guide.md`: ConTeXt style rules for the thesis `.tex` files. |
| `specs/` | Design specs: `model_analysis.md` (original analysis pipeline spec, historical) and `model_based_on_opp_v3_specs.md` (rules for building a heuristic that must match `opp_v3`). |
| `tests/<model>/` | Test-case descriptions (`test_cases*.md`) for the legacy models `opp_v1`, `opp_v2`, `opp_v3`, `opp_hc_1`, `opp_aco_1`. |

Other documentation lives next to the code it describes:

| Model | Model docs | Test docs |
| --- | --- | --- |
| `opp_hc_1` | `models/opp_hc_1/README.md` | `tests/opp_hc_1/README.md`, `docs/tests/opp_hc_1/` |
| `opp_hc_2` | `models/opp_hc_2/README.md` | `tests/opp_hc_2/README.md` |
| `opp_hc_3` | `models/opp_hc_3/README.md`, `PSEUDOCODE.md` | |
| `opp_hc_4` | | `tests/opp_hc_4/README.md` |
| `opp_aco_2` | `models/opp_aco_2/README.md` | |
| `opp_aco_3` | `models/opp_aco_3/README.md`, `PSEUDOCODE.md` | |
| `opp_aco_4` | | `tests/opp_aco_4/README.md` |
| `opp_v1`..`opp_v3`, `opp_aco_1` | | `docs/tests/<model>/` |
| `opp_v4`, `opp_v5_1_mono`, `opp_v5_2_split` | (ZIMPL models: see `docs/thesis/`) | |

CI and repo tooling: `../scripts/README.md`, `../.github/workflows/`.

Repo-level: `../README.md` (overview), `../conventions.md` (binding conventions), `../meta.md` (live changelog and project state), `../analysis/README.md` (analysis pipeline and every audit finding), `../tests/README.md` (how tests are organized), `../examples/README.md`.
