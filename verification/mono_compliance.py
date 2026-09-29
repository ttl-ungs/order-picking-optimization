"""Check a heuristic solution (opp_hc_4 / opp_aco_4) against opp_v5_1_mono.

The monolithic MIP is the single source of truth for the v5 constraints:
instead of re-implementing them in Python, the heuristic's values are fixed
on mono's own variables and SCIP decides whether they are feasible. Two
SCIP levels plus a Python precheck, see dtos/verification/
compliance_report_dto.py for what each one proves.

Variable fixing is done on the compiled LP (by variable name, ZIMPL's
`<var>$<idx1>$<idx2>...` naming), so mono's .zpl is used exactly as the
exact-model tests use it -- not a single constraint is copied or edited.
"""

import math
import os
import shutil
import subprocess
import tempfile
import time

import pyscipopt

from dtos.verification.compliance_report_dto import ComplianceReportDTO
from tests.infra.zimpl.dat_files_builder import (
    DEFAULT_T_FRIO_MAX,
    _compute_m_seq,
    build_dat_files,
    write_scalar_params,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MONO_ZPL = os.path.join(PROJECT_ROOT, "models", "opp_v5_1_mono", "opp_model_v5_1_mono.zpl")

REL_TOL = 1e-6
COLD_CHAIN_TOL = 1e-9  # same tolerance mono's u_pb upper bound uses
DIAGNOSIS_MAX_BATCHES = 40  # per-batch route diagnosis only below this size


def _close(a, b, tol=REL_TOL):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _drop_empty_batches(instance, solution, report):
    """Remove from B every batch with no orders that the heuristic didn't
    use either (agreed with the user, 2026-09-28).

    Mono forces EVERY batch in B to be routed, assigned and charged in the
    objective (its v_b), even one with no orders; opp_hc_4/opp_aco_4 skip
    empty batches. Left in, mono prices a correct solution above what the
    heuristic reports (e.g. 14.5 vs 6.25) and, with many of them free, SCIP
    can hit its time limit on an otherwise trivial instance. An empty batch
    has no real work, so dropping it verifies the same problem the heuristic
    solved; no constraint of mono is touched. A batch that IS in the
    solution is kept (and checked) even if empty."""
    used = {b for seq in solution["picker_sequences"].values() for b in seq} | set(solution["routes"])
    with_orders = {b for (_n, b), value in instance["Bn"].items() if value}
    empty = sorted(b for b in instance["B"] if b not in with_orders and b not in used)
    if not empty:
        return instance
    report.notes.append(f"dropped {len(empty)} empty batch(es) not in the solution: {empty}")
    dropped = set(empty)
    return dict(
        instance,
        B=[b for b in instance["B"] if b not in dropped],
        Bn={(n, b): v for (n, b), v in instance["Bn"].items() if b not in dropped},
    )


def _scenario(instance):
    """Instance (as read by solution_store) -> the dense dict
    dat_files_builder.build_dat_files expects. Missing entries get the same
    default the heuristics use when they read them (`.get(key, 0)`): 0 for
    A_ni/Bn/C_n/S_i."""
    N, V, B = instance["N"], instance["V"], instance["B"]
    return {
        "N": set(N),
        "V": set(V),
        "P": set(instance["P"]),
        "B": set(B),
        "E": instance["E"],
        "depot": instance["depot"],
        "final": instance["final"],
        "W_full": instance["W_full"],
        "W_ea_ta": instance["W_ea_ta"],
        "W_ea": instance["W_ea"],
        "W_ta": instance["W_ta"],
        "B_time": instance["B_time"],
        "B_setup": instance["B_setup"],
        "B_picking": instance["B_picking"],
        "C_v": instance["C_v"] if instance["C_v"] is not None else 0.0,
        "M": instance["M"],
        "C_n": {n: instance["C_n"].get(n, 0.0) for n in N},
        "Dd": dict(instance["Dd"]),
        "d_ij": instance["d_ij"],
        "S_i": {i: instance["S_i"].get(i, 0.0) for i in V},
        "A_ni": {(n, i): instance["A_ni"].get((n, i), 0) for n in N for i in V},
        "Bn": {(n, b): instance["Bn"].get((n, b), 0) for n in N for b in B},
        "V_p": dict(instance["V_p"]),
        # +inf (cold chain disabled, the heuristics' default) can't be written
        # to a .dat: use the same stand-in the v5 migrated tests use.
        "T_frio_max": instance["T_frio_max"] if math.isfinite(instance["T_frio_max"]) else DEFAULT_T_FRIO_MAX,
    }


class _Evaluation:
    """The solution re-evaluated in Python with mono's formulas."""

    def __init__(self):
        self.fixed_batches = []  # batches whose decisions get fixed in SCIP
        self.paths = {}  # b -> [depot, ..., final]
        self.picker_of = {}  # b -> p
        self.sequences = {}  # p -> [b, ...] (fixed batches only)
        self.route_time = {}  # b -> R_b_time
        self.completion = {}  # b -> recomputed v_b
        self.max_t_exec = 0.0


def _precheck(instance, solution, sc, report):
    ev = _Evaluation()
    depot, final = sc["depot"], sc["final"]
    V, E, d_ij, S_i = sc["V"], sc["E"], sc["d_ij"], sc["S_i"]
    speeds, t_frio = sc["V_p"], sc["T_frio_max"]
    violations = report.prechecks

    orders_of = {b: [n for n in sc["N"] if sc["Bn"][(n, b)] > 0.5] for b in sc["B"]}
    assigned = {}
    for p, seq in solution["picker_sequences"].items():
        if p not in sc["P"]:
            violations.append(f"picker {p} is not in P")
        for b in seq:
            assigned.setdefault(b, []).append(p)

    for b in sorted(sc["B"]):
        if not orders_of[b]:
            if b not in assigned:
                report.notes.append(f"{b} has no orders and is not in the solution: left unfixed")
                continue
        if len(assigned.get(b, [])) != 1:
            violations.append(f"{b} assigned to {len(assigned.get(b, []))} pickers (must be exactly 1)")
            continue
        stops = list(solution["routes"].get(b) or [])
        if stops and stops[0] == depot:
            stops = stops[1:]
        if stops and stops[-1] == final:
            stops = stops[:-1]
        path = [depot] + stops + [final]

        bad_nodes = [v for v in path if v not in V]
        if bad_nodes:
            violations.append(f"{b} route visits unknown locations {bad_nodes}")
        repeated = sorted({v for v in path if path.count(v) > 1})
        if repeated:
            violations.append(f"{b} route revisits {repeated}")
        arcs = list(zip(path, path[1:]))
        missing_arcs = [a for a in arcs if a not in E]
        if missing_arcs:
            violations.append(f"{b} route uses arcs not in E: {missing_arcs}")
        required = {
            i for i in V
            if i not in (depot, final) and sum(sc["A_ni"][(n, i)] * sc["Bn"][(n, b)] for n in sc["N"]) >= 1
        }
        uncovered = sorted(required - set(path))
        if uncovered:
            violations.append(f"{b} route misses required locations {uncovered}")
        if bad_nodes or missing_arcs:
            continue

        p = assigned[b][0]
        route_time = sc["B_time"] * sum(d_ij[a] for a in arcs) + sum(S_i[i] for i in stops)
        fixed_time = sc["B_setup"] + sc["B_picking"] * sum(sc["C_n"][n] * sc["Bn"][(n, b)] for n in sc["N"])
        t_exec = fixed_time + route_time / speeds[p]
        if t_exec > t_frio + COLD_CHAIN_TOL:
            violations.append(f"{b} on {p}: t_exec {t_exec:.6g} > T_frio_max {t_frio:.6g} (cold chain)")
        reported = solution["batch_times"].get(b)
        if reported is not None and not _close(reported, t_exec):
            violations.append(f"{b} on {p}: reported t_exec {reported:.6g} != recomputed {t_exec:.6g}")

        ev.fixed_batches.append(b)
        ev.paths[b] = path
        ev.picker_of[b] = p
        ev.route_time[b] = route_time
        slowest = min(speeds.values())
        ev.max_t_exec = max(ev.max_t_exec, fixed_time + route_time / slowest)

    fixed = set(ev.fixed_batches)
    t_exec_of = {
        b: sc["B_setup"] + sc["B_picking"] * sum(sc["C_n"][n] * sc["Bn"][(n, b)] for n in sc["N"])
        + ev.route_time[b] / speeds[ev.picker_of[b]]
        for b in fixed
    }
    for p, seq in solution["picker_sequences"].items():
        ev.sequences[p] = [b for b in seq if b in fixed]
        clock = instance["start_time"] or 0.0
        for b in ev.sequences[p]:
            clock += t_exec_of[b]
            ev.completion[b] = clock
            reported = solution["batch_completions"].get(b)
            if reported is not None and not _close(reported, clock):
                violations.append(f"{b}: reported completion {reported:.6g} != recomputed {clock:.6g}")

    missing_dd = [n for n in sc["N"] if n not in sc["Dd"]]
    if missing_dd:
        violations.append(f"orders without due date (mono needs one): {sorted(missing_dd)}")
    elif len(fixed) == len(sc["B"]):
        batch_of = {n: b for b in sc["B"] for n in orders_of[b]}
        v_sum = sum(ev.completion[b] for b in sc["B"])
        ea = sum(max(0.0, sc["Dd"][n] - ev.completion[batch_of[n]]) for n in sc["N"] if n in batch_of)
        ta = sum(max(0.0, ev.completion[batch_of[n]] - sc["Dd"][n]) for n in sc["N"] if n in batch_of)
        report.recomputed_obj = sc["W_full"] * v_sum + sc["W_ea_ta"] * (sc["W_ea"] * ea + sc["W_ta"] * ta)
        if report.heuristic_obj is not None and not _close(report.recomputed_obj, report.heuristic_obj):
            violations.append(
                f"reported objective {report.heuristic_obj:.10g} != recomputed with mono's formula "
                f"{report.recomputed_obj:.10g}"
            )
    return ev


def _big_m(sc, ev, report):
    """Scenario M / M_seq, or a provably valid replacement when the
    scenario's is too small for this solution (a too-small big-M would make
    mono reject a correct solution -- a formulation artifact, not a
    violation, so it's reported as a note, never as a failure)."""
    need_m = ev.max_t_exec + 1.0
    need_m_seq = max(ev.completion.values(), default=0.0) + ev.max_t_exec + 1.0
    m, m_seq = sc["M"], _compute_m_seq(sc)
    if m is None or m < need_m:
        report.notes.append(f"M {m} too small for this solution (needs >= {need_m:.6g}): replaced")
        report.big_m_substituted = True
        m = max(need_m, need_m_seq)
    if m_seq < need_m_seq:
        report.notes.append(f"M_seq {m_seq} too small for this solution (needs >= {need_m_seq:.6g}): replaced")
        report.big_m_substituted = True
        m_seq = need_m_seq
    return m, m_seq


def _compile_lp(sc, m, m_seq, workdir):
    """Write mono's .dat files and compile the .zpl to .lp, the same way
    tests/infra/zimpl/zpl_utils.solve_zpl does (zimpl run from the dat dir,
    mono reads ../dat_files/*)."""
    dat_dir = os.path.join(workdir, "dat_files")
    zpl_dir = os.path.join(workdir, "opp_v5_1_mono")
    os.makedirs(dat_dir)
    os.makedirs(zpl_dir)
    zpl_path = os.path.join(zpl_dir, os.path.basename(MONO_ZPL))
    shutil.copy2(MONO_ZPL, zpl_path)

    build_dat_files(dat_dir, dict(sc, M=m))
    write_scalar_params(
        os.path.join(dat_dir, "params.dat"),
        W_full=sc["W_full"], W_ea_ta=sc["W_ea_ta"], W_ea=sc["W_ea"], W_ta=sc["W_ta"],
        B_time=sc["B_time"], B_setup=sc["B_setup"], B_picking=sc["B_picking"],
        C_v=sc["C_v"], M=m, M_seq=m_seq,
    )
    out_base = os.path.join(dat_dir, "model")
    result = subprocess.run(
        ["zimpl", "-t", "lp", "-l", "8192", "-o", out_base, zpl_path],
        cwd=dat_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ZIMPL compilation failed: {result.stdout[-500:]} {result.stderr[-500:]}")
    return f"{out_base}.lp"


def _fixings(sc, ev, with_times, reported_completions=None):
    """name -> (lb, ub) for mono's variables. Level 2 fixes the REPORTED
    completion times (what the heuristic claims), falling back to the
    recomputed ones only for a batch the heuristic didn't report."""
    reported_completions = reported_completions or {}
    fixes = {}
    for b in ev.fixed_batches:
        arcs = set(zip(ev.paths[b], ev.paths[b][1:]))
        for (i, j) in sc["E"]:
            value = 1.0 if (i, j) in arcs else 0.0
            fixes[f"z_ijb${i}${j}${b}"] = (value, value)
        for p in sc["P"]:
            value = 1.0 if p == ev.picker_of[b] else 0.0
            fixes[f"X_pb${p}${b}"] = (value, value)
    for p, seq in ev.sequences.items():
        for pos, b in enumerate(seq):
            for k in seq[pos + 1:]:
                # Z_bk[b,k] = 1 <=> k runs after b on a shared picker
                # (mono's non_overlap_1); only b < k exists (ZIMPL string order).
                if b < k:
                    fixes[f"Z_bk${b}${k}"] = (1.0, 1.0)
                else:
                    fixes[f"Z_bk${k}${b}"] = (0.0, 0.0)
        if with_times:
            for b in seq:
                c = reported_completions.get(b, ev.completion[b])
                # Exact (lb = ub): a tolerance band would let SCIP pick the
                # cheaper end and shift the objective it reports; float noise
                # in the constraints is already absorbed by SCIP's own
                # feasibility tolerance.
                fixes[f"v_pb${p}${b}"] = (c, c)
                fixes[f"v_b${b}"] = (c, c)
    return fixes


def _solve_fixed(lp_path, fixes, time_limit):
    """Returns (status, objective or None)."""
    model = pyscipopt.Model()
    model.hideOutput()
    model.setParam("limits/time", time_limit)
    model.readProblem(lp_path)
    by_name = {v.name: v for v in model.getVars()}
    unknown = [name for name in fixes if name not in by_name]
    if unknown:
        raise RuntimeError(f"{len(unknown)} fixed variables not in mono's LP, e.g. {unknown[:3]}")
    for name, (lb, ub) in fixes.items():
        var = by_name[name]
        model.chgVarUb(var, ub)
        model.chgVarLb(var, lb)
    model.optimize()
    status = model.getStatus()
    obj = model.getObjVal() if model.getNSols() > 0 and status != "infeasible" else None
    return status, obj


def _diagnose(sc, ev, lp_path, time_limit, report):
    """Level 1 infeasible: free one group of fixed decisions at a time and
    report which one restores feasibility."""
    full = _fixings(sc, ev, with_times=False)
    groups = {
        "routes (z_ijb)": lambda n: n.startswith("z_ijb$"),
        "sequence (Z_bk)": lambda n: n.startswith("Z_bk$"),
        "assignment + sequence (X_pb, Z_bk)": lambda n: n.startswith(("X_pb$", "Z_bk$")),
    }
    for label, freed in groups.items():
        status, _ = _solve_fixed(lp_path, {n: v for n, v in full.items() if not freed(n)}, time_limit)
        report.diagnosis.append(f"freeing {label}: {status}")
    if len(ev.fixed_batches) <= DIAGNOSIS_MAX_BATCHES:
        for b in ev.fixed_batches:
            suffix = f"${b}"
            fixes = {n: v for n, v in full.items() if not (n.startswith("z_ijb$") and n.endswith(suffix))}
            status, _ = _solve_fixed(lp_path, fixes, time_limit)
            if status != "infeasible":
                report.diagnosis.append(f"route of {b} alone makes it infeasible (freed: {status})")


def check_compliance(meta, instance, solution, time_limit=300.0, keep_workdir=None):
    """Check one solution (as read by verification.solution_store) against
    opp_v5_1_mono.

    Args:
        meta: {"model", "test"}.
        instance, solution: see verification/solution_store.read_solution_record.
        time_limit: SCIP time limit (seconds) per solve.
        keep_workdir: if given, the .dat/.lp files are written there and
            kept (for debugging); otherwise a temp dir that is removed.

    Returns:
        ComplianceReportDTO.
    """
    start = time.time()
    report = ComplianceReportDTO(meta["test"], meta["model"])
    report.heuristic_obj = solution.get("objective_value")
    workdir = keep_workdir or tempfile.mkdtemp(prefix="mono_compliance_")
    try:
        instance = _drop_empty_batches(instance, solution, report)
        sc = _scenario(instance)
        ev = _precheck(instance, solution, sc, report)
        if not ev.fixed_batches:
            raise RuntimeError("no batch could be fixed (see prechecks)")
        unfixed = sorted(set(sc["B"]) - set(ev.fixed_batches))
        if unfixed:
            report.notes.append(f"SCIP levels ran with {len(unfixed)} batch(es) left free: {unfixed}")
        m, m_seq = _big_m(sc, ev, report)
        lp_path = _compile_lp(sc, m, m_seq, workdir)

        report.level1_status, report.level1_obj = _solve_fixed(lp_path, _fixings(sc, ev, False), time_limit)
        if report.level1_status == "infeasible":
            _diagnose(sc, ev, lp_path, time_limit, report)
        else:
            level2 = _fixings(sc, ev, True, solution["batch_completions"])
            report.level2_status, report.level2_obj = _solve_fixed(lp_path, level2, time_limit)

        compliant = (
            not report.prechecks
            and report.level1_status == "optimal"
            and report.level2_status == "optimal"
            and report.level2_obj is not None
            and report.heuristic_obj is not None
            and _close(report.level2_obj, report.heuristic_obj)
        )
        if report.level2_obj is not None and report.heuristic_obj is not None and not _close(
            report.level2_obj, report.heuristic_obj
        ):
            report.notes.append(
                f"mono prices the fixed solution at {report.level2_obj:.10g}, heuristic reported "
                f"{report.heuristic_obj:.10g}"
            )
        report.verdict = "compliant" if compliant else "violations"
    except Exception as e:
        report.verdict = "error"
        report.error = str(e)
    finally:
        if keep_workdir is None:
            shutil.rmtree(workdir, ignore_errors=True)
        report.check_time = time.time() - start
    return report
