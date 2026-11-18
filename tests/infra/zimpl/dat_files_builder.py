import os

# Cold-chain limit written when a scenario does not define one: large enough
# that no batch is ever excluded (the cold chain is disabled).
DEFAULT_T_COLD = 1_000_000_000.0


def write_set_dat(path, elements):
    """Write a set of strings, one quoted element per line."""
    with open(path, "w") as f:
        for e in sorted(elements):
            f.write(f'"{e}"\n')


def write_edge_dat(path, edges):
    """Write the pairs (i, j) of the set E, two quoted names per line."""
    with open(path, "w") as f:
        for i, j in sorted(edges):
            f.write(f'"{i}" "{j}"\n')


def write_scalar_dat(path, value):
    """Write a scalar (number or string) as a one-line .dat."""
    with open(path, "w") as f:
        f.write(f"{value}\n")


def write_scalar_params(path, **kwargs):
    """
    Write scalars in order, one per line. The .zpl reads them by position
    (`skip N`).
    """
    with open(path, "w") as f:
        for val in kwargs.values():
            f.write(f"{val}\n")


def write_indexed_dat(path, data):
    """
    Write a parameter indexed by a set. `data` is {key: value}, where a key is
    a string or a tuple of strings; each part of the key is written quoted,
    followed by the value.
    """
    with open(path, "w") as f:
        for key, val in sorted(data.items()):
            if isinstance(key, tuple):
                keys_str = " ".join(f'"{k}"' for k in key)
            else:
                keys_str = f'"{key}"'
            f.write(f"{keys_str} {val}\n")


def _compute_m_seq(scenario_data):
    """Upper bound on max completion time: safe Big-M for non-overlap constraints.

    M_seq must exceed the latest possible c_pb.  In the worst case every batch
    is assigned to one picker sequentially, so c_pb_max ≈ Σ_b T_exec_pb_max.
    We approximate max route time per batch as |V|*max(D_ij)*T_travel (every
    location visited) and use min(V_p) for the slowest picker.
    """
    B, N, V = scenario_data["B"], scenario_data["N"], scenario_data["V"]
    C_n, B_nb = scenario_data["C_n"], scenario_data["B_nb"]
    T_setup, T_pick, T_travel = scenario_data["T_setup"], scenario_data["T_pick"], scenario_data["T_travel"]
    D_ij = scenario_data["D_ij"]
    speeds = scenario_data.get("V_p") or {p: 1.0 for p in scenario_data["P"]}
    min_speed = min(speeds.values())
    max_dist = max(D_ij.values()) if D_ij else 1.0
    max_service = max(scenario_data["S_i"].values()) if scenario_data["S_i"] else 0.0
    max_route_time = T_travel * len(V) * max_dist + len(V) * max_service

    total = 0.0
    for b in B:
        fixed_time = T_setup + T_pick * sum(C_n[n] * B_nb[(n, b)] for n in N)
        total += fixed_time + max_route_time / min_speed

    return max(500.0, round(total + 1.0))


# The scenario dict of the most recent build_dat_files() call, kept by
# reference so that zpl_utils.solve_zpl can attach the instance to the solve's
# ZimplSolutionRecordDTO. Each test runs in its own process, so it never
# crosses between tests (like models/utils/solve_registry.py).
_last_scenario = None


def last_scenario():
    """The scenario dict of the most recent build_dat_files() call, or None."""
    return _last_scenario


def build_dat_files(tmpdir, scenario_data):
    """Write every .dat file of the scenario in `tmpdir` and return that directory."""
    global _last_scenario
    _last_scenario = scenario_data
    write_set_dat(os.path.join(tmpdir, "data_N.dat"), scenario_data["N"])
    write_set_dat(os.path.join(tmpdir, "data_V.dat"), scenario_data["V"])
    write_set_dat(os.path.join(tmpdir, "data_P.dat"), scenario_data["P"])
    write_set_dat(os.path.join(tmpdir, "data_B.dat"), scenario_data["B"])
    write_edge_dat(os.path.join(tmpdir, "data_E.dat"), scenario_data["E"])

    write_scalar_dat(os.path.join(tmpdir, "depot.dat"), scenario_data["depot"])
    write_scalar_dat(os.path.join(tmpdir, "final.dat"), scenario_data["final"])

    m_seq = _compute_m_seq(scenario_data)

    write_scalar_params(
        os.path.join(tmpdir, "params.dat"),
        W_c    = scenario_data["W_c"],
        W_pen   = scenario_data["W_pen"],
        W_e      = scenario_data["W_e"],
        W_t      = scenario_data["W_t"],
        T_travel    = scenario_data["T_travel"],
        T_setup   = scenario_data["T_setup"],
        T_pick = scenario_data["T_pick"],
        C_v       = scenario_data["C_v"],
        M         = scenario_data["M"],
        M_seq     = m_seq,
    )

    write_indexed_dat(os.path.join(tmpdir, "cap_n.dat"),       scenario_data["C_n"])
    write_indexed_dat(os.path.join(tmpdir, "due_date.dat"),    scenario_data["T_due_n"])
    write_indexed_dat(os.path.join(tmpdir, "distances.dat"),   scenario_data["D_ij"])
    write_indexed_dat(os.path.join(tmpdir, "service_time.dat"),scenario_data["S_i"])
    write_indexed_dat(os.path.join(tmpdir, "a_ni.dat"),        scenario_data["A_ni"])
    write_indexed_dat(os.path.join(tmpdir, "B_nb.dat"),          scenario_data["B_nb"])

    # Picker speeds and cold-chain limit (read by opp_mono and by opp_split's
    # Stage 2). A scenario that does not define them gets V_p = 1.0 for every
    # picker and a limit that never binds.
    speeds = scenario_data.get("V_p") or {p: 1.0 for p in scenario_data["P"]}
    write_indexed_dat(os.path.join(tmpdir, "velocities.dat"), speeds)
    write_scalar_dat(
        os.path.join(tmpdir, "cold.dat"),
        scenario_data.get("T_cold", DEFAULT_T_COLD),
    )

    return tmpdir
