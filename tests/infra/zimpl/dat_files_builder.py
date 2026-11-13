import os

# Cold-chain limit written when a scenario does not define one: large enough
# that no batch is ever excluded (same value the opp_split migrated tests use to
# neutralize the cold chain for the v4 baseline).
DEFAULT_T_COLD = 1_000_000_000.0


def write_set_dat(path, elements):
    """Escribe un set de strings, uno por linea, entre comillas (formato ZIMPL)."""
    with open(path, "w") as f:
        for e in sorted(elements):
            f.write(f'"{e}"\n')


def write_edge_dat(path, edges):
    """Escribe pares (i, j) que forman el set E. Formato ZIMPL: \"<i>\" \"<j>\"."""
    with open(path, "w") as f:
        for i, j in sorted(edges):
            f.write(f'"{i}" "{j}"\n')


def write_scalar_dat(path, value):
    """Escribe un escalar (numerico o string) en un .dat de una sola linea."""
    with open(path, "w") as f:
        f.write(f"{value}\n")


def write_scalar_params(path, **kwargs):
    """
    Escribe escalares en orden en un .dat de una columna.
    El .zpl los lee con `use N` (posicion).
    """
    with open(path, "w") as f:
        for val in kwargs.values():
            f.write(f"{val}\n")


def write_indexed_dat(path, data):
    """
    Escribe parametros indexados por un set.
    data: dict {key: value}, donde key es string o tupla de strings.

    Formato ZIMPL clave simple:  \"<key>\" value
    Formato ZIMPL clave doble:   \"<k1>\" \"<k2>\" value
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
# reference (no copy) so zpl_utils.solve_zpl can attach the instance to the
# solve's ZimplSolutionRecordDTO (saved when WRITE_SOLUTIONS is set). Each
# test runs in its own subprocess, so this never crosses between tests --
# same pattern as models/utils/solve_registry.py.
_last_scenario = None


def last_scenario():
    """The scenario dict of the most recent build_dat_files() call, or None."""
    return _last_scenario


def build_dat_files(tmpdir, scenario_data):
    """
    Recibe un dict con todos los datos del escenario y escribe los .dat
    en tmpdir. Devuelve el path del directorio.
    """
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
    if "X_pb" in scenario_data:
        write_indexed_dat(os.path.join(tmpdir, "x_pb.dat"), scenario_data["X_pb"])

    # Heterogeneous picker speed and cold-chain limit (read by opp_mono and
    # opp_split's stage 2). Scenarios that predate them get V_p = 1.0 for
    # every picker and no binding cold-chain limit, i.e. the original problem.
    speeds = scenario_data.get("V_p") or {p: 1.0 for p in scenario_data["P"]}
    write_indexed_dat(os.path.join(tmpdir, "velocities.dat"), speeds)
    write_scalar_dat(
        os.path.join(tmpdir, "cold.dat"),
        scenario_data.get("T_cold", DEFAULT_T_COLD),
    )

    return tmpdir
