"""Scaffold the test files of a new model family from an existing one.

Every test of a derived family (opp_hc_3, opp_hc_4, opp_aco_3, ...) that is a literal clone of
its base family's test is a one-line tests.support.family_case.family_case() call. This writes
those files, so adding e.g. opp_hc_5 on top of opp_hc_2 is one command:

    python -m scripts.new_family_tests --base opp_hc_2 --new opp_hc_5 --tier functional \\
        --model-import models.opp_hc_5:OPPHillClimbing \\
        --dto-import dtos.hc.solve_hc_5_model_dto:SolveHC5ModelDTO \\
        --handler-import models.opp_hc_5.utils.output_handler:OutputHandler

The names that the base tests use for the model, the params DTO and the output handler are read
from each base file, so only the replacement classes have to be given. New files keep the base's
numbering (test_case_<same NN|slug>.py); existing files are left alone unless --force.

Not every base test should be cloned: tests that exercise something the new family changes need
their own assertions, and a base test whose scenario helper builds a DTO at import time is not
reachable by the factory (see tests/opp_hc_4/functional/test_case_22.py). Use --only / --skip to
pick, review the output, and run the new suite.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

HEADER = "from tests.support.family_case import family_case\n"


def parse_import(spec, flag):
    if ":" not in spec:
        sys.exit(f"{flag} must look like module.path:ClassName, got {spec!r}")
    module, cls = spec.split(":", 1)
    return module, cls


def base_names(source, base):
    """Names the base test module binds for the model class, the params DTO and the output handler."""
    found = {}
    m = re.search(rf"from models\.{base}(?:\.{base})? import (\w+)", source)
    if m:
        found["model"] = m.group(1)
    m = re.search(r"from dtos\.\w+\.\w+ import (Solve\w*DTO)", source)
    if m:
        found["dto"] = m.group(1)
    m = re.search(rf"from models\.{base}\.utils\.output_handler import (\w+)", source)
    if m:
        found["handler"] = m.group(1)
    m = re.search(r"^class (\w+)\(", source, re.M)
    found["class"] = m.group(1) if m else "TestCase"
    return found


def render(base, tier, stem, names, new_model, new_dto, new_handler):
    overrides = [(names["model"], new_model[1]), (names["dto"], new_dto[1])]
    imports = [f"from {new_model[0]} import {new_model[1]}\n", f"from {new_dto[0]} import {new_dto[1]}\n"]
    if "handler" in names:
        overrides.append((names["handler"], new_handler[1]))
        imports.append(f"from {new_handler[0]} import {new_handler[1]}\n")
    body = ",\n".join(f"        '{k}': {v}" for k, v in overrides)
    return (
        HEADER + "".join(imports) + "\n\n"
        f"{names['class']} = family_case(\n    'tests.{base}.{tier}.{stem}',\n    {{\n{body},\n    }},\n)\n"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="existing family whose tests are reused, e.g. opp_hc_2")
    ap.add_argument("--new", required=True, help="new family directory under tests/, e.g. opp_hc_5")
    ap.add_argument("--tier", required=True, choices=["functional", "stress"])
    ap.add_argument("--model-import", required=True, help="module:Class of the new model")
    ap.add_argument("--dto-import", required=True, help="module:Class of the new params DTO")
    ap.add_argument("--handler-import", help="module:Class of the new output handler (needed if the base tests attach one)")
    ap.add_argument("--only", nargs="+", metavar="ID", help="generate only these ids/slugs (e.g. 01 02 22)")
    ap.add_argument("--skip", nargs="+", metavar="ID", default=[], help="do not generate these ids/slugs")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--dry-run", action="store_true", help="only list what would be written")
    args = ap.parse_args()

    new_model = parse_import(args.model_import, "--model-import")
    new_dto = parse_import(args.dto_import, "--dto-import")
    new_handler = parse_import(args.handler_import, "--handler-import") if args.handler_import else None

    base_dir = os.path.join("tests", args.base, args.tier)
    out_dir = os.path.join("tests", args.new, args.tier)
    if not os.path.isdir(base_dir):
        sys.exit(f"no such base suite: {base_dir}")
    written = skipped = 0
    for fname in sorted(os.listdir(base_dir)):
        m = re.fullmatch(r"(test_case_([\w]+))\.py", fname)
        if not m:
            continue
        stem, ident = m.groups()
        if (args.only and ident not in args.only) or ident in args.skip:
            continue
        with open(os.path.join(base_dir, fname), encoding="utf-8") as fh:
            source = fh.read()
        if "family_case(" in source or "migrated_case(" in source:
            print(f"skip   {fname}: the base test is itself a factory call")
            skipped += 1
            continue
        names = base_names(source, args.base)
        if "model" not in names or "dto" not in names:
            print(f"skip   {fname}: could not find the model/DTO imports (not a plain model test)")
            skipped += 1
            continue
        if "handler" in names and new_handler is None:
            print(f"skip   {fname}: attaches an output handler; pass --handler-import")
            skipped += 1
            continue
        target = os.path.join(out_dir, fname)
        if os.path.exists(target) and not args.force:
            print(f"exists {target}")
            skipped += 1
            continue
        print(f"{'would write' if args.dry_run else 'write'} {target}")
        if not args.dry_run:
            os.makedirs(out_dir, exist_ok=True)
            init = os.path.join(out_dir, "__init__.py")
            if not os.path.exists(init):
                open(init, "w").close()
            with open(target, "w", encoding="utf-8", newline="") as fh:
                fh.write(render(args.base, args.tier, stem, names, new_model, new_dto, new_handler))
        written += 1
    print(f"\n{written} file(s) {'to write' if args.dry_run else 'written'}, {skipped} skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
