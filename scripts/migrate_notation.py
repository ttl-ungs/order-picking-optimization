"""Staged rename of the model notation (ZIMPL models, Python code and results/).

Renames the decision variables and parameters of opp_v4 / opp_v5_1_mono /
opp_v5_2_split (and every Python module, scenario and saved result that uses
the same names) to the notation agreed for the thesis: variables lowercase,
parameters uppercase, one letter plus labels/indices (T^{setup} -> T_setup).

    python -m scripts.migrate_notation <group>            # dry run: what would change
    python -m scripts.migrate_notation <group> --apply    # rewrite the files

Groups are applied in this order, one commit each:
  variables   solution variables (x_pb, y_bk, q_ijb, c_pb, c_b, r_b, d_b)
  zpl         names that only exist inside the .zpl files (v_start/v_end,
              L_b, R_b as Stage 2 input, constraint names)
  params      scenario/DTO parameters, repo-wide (T_setup, W_c, T_due_n, ...)

How the replacement avoids ordering problems: a file is scanned once, token by
token (a token is a maximal [A-Za-z0-9_]+ run), and each token is looked up in
the file's mapping. Every rename in a group therefore happens simultaneously:
"R_b" -> "L_b" and "R_b_time" -> "R_b" in the same pass never chain into
"R_b_time" -> "L_b". Only whole tokens match ("W_ea" never touches "W_ea_ta"),
and leading underscores are kept ("_T_frio_max" -> "_T_cold").

A group whose new names could be renamed again by the same group declares
sentinel tokens; --apply refuses to run if a sentinel is already present
(i.e. the group was already applied).

Only files tracked by git are touched, so every change is reviewable with
git diff and revertible with git checkout.
"""

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

TOKEN = re.compile(r"[A-Za-z0-9_]+")

# Never rewritten by any group: the thesis documents and report templates are
# updated by hand (LaTeX notation, not code identifiers) and meta.md is a
# historical changelog.
GLOBAL_EXCLUDE = [
    "docs/thesis/*",
    "*.tex",
    "*.pdf",
    "*.png",
    "*.lp",
    "*.tbl",
    "meta.md",
    "scripts/migrate_notation.py",
]

V4_V5_ZPL = [
    "models/opp_v4/*.zpl",
    "models/opp_v5_1_mono/*.zpl",
    "models/opp_v5_2_split/*.zpl",
]


class Rule:
    """A token mapping applied to the tracked files matching `include`."""

    def __init__(self, mapping, include, exclude=(), literals=()):
        self.mapping = mapping
        self.include = include
        self.exclude = list(exclude)
        self.literals = list(literals)

    def matches(self, path):
        if any(fnmatch.fnmatch(path, pattern) for pattern in self.exclude):
            return False
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.include)


VARIABLE_CONSUMERS = [
    *V4_V5_ZPL,
    "models/opp_v5_2_split/*",
    "models/opp_hc_4/*",
    "models/opp_aco_4/*",
    "dtos/opp/zimpl_solution_record_dto.py",
    "dtos/hc/solve_hc_4_model_dto.py",
    "dtos/aco/solve_aco_4_model_dto.py",
    "verification/*",
    "analysis/*.py",
    "experiments/opp_v5/*.py",
    "tests/infra/*",
    "tests/shared_scenarios/*",
    "tests/opp_v4/*",
    "tests/opp_v5_1_mono/*",
    "tests/opp_v5_2_split/*",
    "tests/opp_hc_4/*",
    "tests/opp_aco_4/*",
    "results/opp_v4/*",
    "results/opp_v5_1_mono/*",
    "results/opp_v5_2_split/*",
    "results/compliance/*",
    "results/comparability/*",
]

GROUPS = {
    "variables": {
        "rules": [
            Rule(
                {
                    "X_pb": "x_pb",
                    "Z_bk": "y_bk",
                    "z_bk": "y_bk",
                    "f_ijb": "q_ijb",
                    "v_pb": "c_pb",
                    "v_pb_max": "c_pb_max",
                    "v_b": "c_b",
                    "v_b_lower_bound": "c_b_lower_bound",
                    "t_exec_b": "d_b",
                    "r_b_time": "r_b",
                },
                VARIABLE_CONSUMERS,
                # "X_pb" there is a scenario key of the legacy opp_v2 ZIMPL model
                # (a fixed assignment, not a variable); edited by hand.
                exclude=["tests/infra/zimpl/dat_files_builder.py"],
            ),
            # R_b_time is a variable (-> r_b) in the mono model and in split's
            # Stage 1, and in the solutions they wrote. In split's Stage 2 it
            # is an input parameter (-> R_b, zpl group); Python mentions are
            # edited by hand because the meaning depends on the sentence.
            Rule(
                {"R_b_time": "r_b"},
                [
                    "models/opp_v5_1_mono/*.zpl",
                    "models/opp_v5_2_split/opp_model_v5_2_split_stage1_routing.zpl",
                    "results/opp_v5_1_mono/*",
                    "results/opp_v5_2_split/*",
                ],
            ),
        ],
        "sentinels": [],
    },
    "zpl": {
        "rules": [
            Rule(
                {
                    "v_1": "v_start",
                    "v_f": "v_end",
                    "R_b": "L_b",
                    "flow_conservation": "route_flow_conservation",
                    "f_flow_conservation": "load_flow_conservation",
                    "subtour_elimination_bound": "load_flow_bound",
                    "f_depot_source": "load_flow_source",
                    "batch_execution_time": "batch_execution_time_lower",
                },
                V4_V5_ZPL,
            ),
            Rule(
                {"R_b_time": "R_b"},
                ["models/opp_v5_2_split/opp_model_v5_2_split_stage2_scheduling.zpl"],
            ),
        ],
        # after this group "R_b" is the Stage 2 route-time input: a second run
        # would turn it into L_b
        "sentinels": ["L_b"],
    },
    # Legacy models (v1-v3, hc_1-3, aco_1-3): their comments, docstrings,
    # prints and heuristic locals use the same variable names. The PySCIPOpt
    # locals/SCIP names of v1-v3 (v, f, t_exec) are renamed separately with a
    # tokenizer, since a token map cannot tell a local `f` from an f-string.
    "legacy": {
        "rules": [
            Rule(
                {
                    "X_pb": "x_pb",
                    "Z_bk": "y_bk",
                    "f_ijb": "q_ijb",
                    "f_ijh": "q_ijh",
                    "v_pb": "c_pb",
                    "v_pk": "c_pk",
                    "v_b": "c_b",
                    "t_exec_b": "d_b",
                    "t_exec_h": "d_h",
                    "v_1": "v_start",
                    "v_f": "v_end",
                },
                [
                    "models/opp_v1/*",
                    "models/opp_v2/*.py",
                    "models/opp_v3/*",
                    "models/opp_hc_1/*",
                    "models/opp_hc_2/*",
                    "models/opp_hc_3/*",
                    "models/opp_aco_1/*",
                    "models/opp_aco_2/*",
                    "models/opp_aco_3/*",
                    "examples/*",
                    "tests/opp_hc_2/*",
                    "tests/opp_aco_2/*",
                    "tests/opp_aco_3/*",
                    "docs/specs/*",
                    "docs/tests/*",
                ],
            ),
            # Legacy opp_v2 ZIMPL model: same variables and ZIMPL-only names as
            # opp_v4, except X_pb, which is an input parameter there (a fixed
            # assignment) and keeps its uppercase name.
            Rule(
                {
                    "Z_bk": "y_bk",
                    "f_ijb": "q_ijb",
                    "v_pb": "c_pb",
                    "v_b": "c_b",
                    "t_exec_b": "d_b",
                    "v_1": "v_start",
                    "v_f": "v_end",
                    "R_b": "L_b",
                    "flow_conservation": "route_flow_conservation",
                    "f_flow_conservation": "load_flow_conservation",
                    "f_depot_source": "load_flow_source",
                },
                ["models/opp_v2/*.zpl"],
            ),
        ],
        "sentinels": [],
    },
    "params": {
        "rules": [
            Rule(
                {
                    "W_full": "W_c",
                    "W_ea_ta": "W_pen",
                    "W_ea": "W_e",
                    "W_ta": "W_t",
                    "B_time": "T_travel",
                    "B_setup": "T_setup",
                    "B_picking": "T_pick",
                    "T_frio_max": "T_cold",
                    "t_frio_max": "t_cold",
                    "DEFAULT_T_FRIO_MAX": "DEFAULT_T_COLD",
                    "Dd": "T_due_n",
                    "t_exec_pb": "T_exec_pb",
                    "t_exec_pb_max": "T_exec_pb_max",
                    "d_ij": "D_ij",
                    "Bn": "B_nb",
                    "tiempo_fijo": "F_b",
                    "B_sin_picker_elegible": "B_no_eligible_picker",
                },
                ["*"],
                # "frio" is also a Spanish word in comments: only the file name
                literals=[("frio.dat", "cold.dat")],
            ),
        ],
        "sentinels": [],
    },
}


def tracked_files():
    output = subprocess.run(
        ["git", "ls-files", "-z"], cwd=PROJECT_ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [path for path in output.split("\0") if path]


def excluded(path):
    return any(fnmatch.fnmatch(path, pattern) for pattern in GLOBAL_EXCLUDE)


def rewrite(text, mapping, literals):
    """Return (new_text, Counter of old_name -> replacements)."""
    counts = Counter()

    def replace(match):
        token = match.group(0)
        core = token.lstrip("_")
        if core in mapping:
            counts[core] += 1
            return token[: len(token) - len(core)] + mapping[core]
        return token

    new_text = TOKEN.sub(replace, text)
    for old, new in literals:
        occurrences = new_text.count(old)
        if occurrences:
            counts[old] += occurrences
            new_text = new_text.replace(old, new)
    return new_text, counts


def plan(group):
    """Yield (path, new_text, counts) for every file the group would change."""
    rules = GROUPS[group]["rules"]
    for path in tracked_files():
        if excluded(path):
            continue
        applicable = [rule for rule in rules if rule.matches(path)]
        if not applicable:
            continue
        mapping, literals = {}, []
        for rule in applicable:
            mapping.update(rule.mapping)
            literals.extend(rule.literals)
        full_path = os.path.join(PROJECT_ROOT, path)
        try:
            with open(full_path, encoding="utf-8", newline="") as f:
                text = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        new_text, counts = rewrite(text, mapping, literals)
        if counts:
            yield path, new_text, counts


def sentinel_hits(group):
    sentinels = set(GROUPS[group]["sentinels"])
    if not sentinels:
        return []
    hits = []
    for path in tracked_files():
        rules = GROUPS[group]["rules"]
        if excluded(path) or not any(rule.matches(path) for rule in rules):
            continue
        with open(os.path.join(PROJECT_ROOT, path), encoding="utf-8", errors="ignore") as f:
            found = sentinels & set(TOKEN.findall(f.read()))
        if found:
            hits.append((path, sorted(found)))
    return hits


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("group", choices=list(GROUPS))
    parser.add_argument("--apply", action="store_true", help="rewrite the files (default: dry run)")
    parser.add_argument("--summary", action="store_true", help="only print totals per name and per directory")
    args = parser.parse_args()

    if args.apply:
        hits = sentinel_hits(args.group)
        if hits:
            print(f"Refusing to apply '{args.group}': sentinel names already present (group already applied?)")
            for path, found in hits:
                print(f"  {path}: {', '.join(found)}")
            return 1

    totals, per_dir, changed = Counter(), Counter(), 0
    for path, new_text, counts in plan(args.group):
        changed += 1
        totals.update(counts)
        per_dir[os.path.dirname(path) or "."] += sum(counts.values())
        if not args.summary:
            detail = ", ".join(f"{name} x{n}" for name, n in sorted(counts.items()))
            print(f"{path}: {detail}")
        if args.apply:
            with open(os.path.join(PROJECT_ROOT, path), "w", encoding="utf-8", newline="") as f:
                f.write(new_text)

    if args.summary:
        for directory, n in sorted(per_dir.items()):
            print(f"{directory}: {n}")
    print()
    print(f"{'Applied' if args.apply else 'Dry run'}: {changed} files")
    for name, n in sorted(totals.items()):
        print(f"  {name}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
