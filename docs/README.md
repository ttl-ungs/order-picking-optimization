# Docs

Documents about the code and its results. The documents themselves are in Spanish, like the thesis.

| Where | What |
| --- | --- |
| `specs/comparabilidad_split_heuristicas.md` | Which results of the exact models and the heuristics can be compared, and why. The source of truth is the CSV that `python -m experiments.comparison.comparability` writes. |
| `guides/context_style_guide.md` | Page layout, palette, tables and charts that every ConTeXt document of the thesis follows. |
| `thesis/*.tex`, `thesis/*.pdf` | The four generated reports: the explorations of OPP-Split and OPP-Mono, OPP-Mono vs OPP-Split, and OPP-Split vs the heuristics. |

The `.tex` files in `thesis/` are generated: edit the `*_template.tex` in `experiments/exact/reports/`
instead, then regenerate and compile (see [experiments/exact/README.md](../experiments/exact/README.md)).
