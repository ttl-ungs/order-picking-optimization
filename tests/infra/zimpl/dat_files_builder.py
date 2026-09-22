import os

# Cold-chain limit written when a scenario does not define one: large enough
# that no batch is ever excluded (same value the opp_v5_2_split migrated tests use to
# neutralize the cold chain for the v4 baseline).
DEFAULT_T_FRIO_MAX = 1_000_000_000.0


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


def build_dat_files(tmpdir, scenario_data):
    """
    Recibe un dict con todos los datos del escenario y escribe los .dat
    en tmpdir. Devuelve el path del directorio.
    """
    write_set_dat(os.path.join(tmpdir, "data_N.dat"), scenario_data["N"])
    write_set_dat(os.path.join(tmpdir, "data_V.dat"), scenario_data["V"])
    write_set_dat(os.path.join(tmpdir, "data_P.dat"), scenario_data["P"])
    write_set_dat(os.path.join(tmpdir, "data_B.dat"), scenario_data["B"])
    write_edge_dat(os.path.join(tmpdir, "data_E.dat"), scenario_data["E"])

    write_scalar_dat(os.path.join(tmpdir, "depot.dat"), scenario_data["depot"])
    write_scalar_dat(os.path.join(tmpdir, "final.dat"), scenario_data["final"])

    write_scalar_params(
        os.path.join(tmpdir, "params.dat"),
        W_full    = scenario_data["W_full"],
        W_ea_ta   = scenario_data["W_ea_ta"],
        W_ea      = scenario_data["W_ea"],
        W_ta      = scenario_data["W_ta"],
        B_time    = scenario_data["B_time"],
        B_setup   = scenario_data["B_setup"],
        B_picking = scenario_data["B_picking"],
        C_v       = scenario_data["C_v"],
        M         = scenario_data["M"],
    )

    write_indexed_dat(os.path.join(tmpdir, "cap_n.dat"),       scenario_data["C_n"])
    write_indexed_dat(os.path.join(tmpdir, "due_date.dat"),    scenario_data["Dd"])
    write_indexed_dat(os.path.join(tmpdir, "distances.dat"),   scenario_data["d_ij"])
    write_indexed_dat(os.path.join(tmpdir, "service_time.dat"),scenario_data["S_i"])
    write_indexed_dat(os.path.join(tmpdir, "a_ni.dat"),        scenario_data["A_ni"])
    write_indexed_dat(os.path.join(tmpdir, "Bn.dat"),          scenario_data["Bn"])
    if "X_pb" in scenario_data:
        write_indexed_dat(os.path.join(tmpdir, "x_pb.dat"), scenario_data["X_pb"])

    # Heterogeneous picker speed and cold-chain limit (read by opp_v5_1_mono and
    # opp_v5_2_split's stage 2). Scenarios that predate them get V_p = 1.0 for
    # every picker and no binding cold-chain limit, i.e. the original problem.
    speeds = scenario_data.get("V_p") or {p: 1.0 for p in scenario_data["P"]}
    write_indexed_dat(os.path.join(tmpdir, "velocities.dat"), speeds)
    write_scalar_dat(
        os.path.join(tmpdir, "frio.dat"),
        scenario_data.get("T_frio_max", DEFAULT_T_FRIO_MAX),
    )

    return tmpdir
