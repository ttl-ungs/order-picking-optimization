"""Small scenarios adapted from the normal OPP v4 routing cases."""


def two_batches_two_routes():
    """Two independent batches with a unique shortest route each."""
    return {
        "N": {"O1", "O2"},
        "P": {"P_slow", "P_fast"},
        "B": {"B1", "B2"},
        "V": {"D", "A", "B", "F"},
        "E": {
            ("D", "A"), ("A", "F"),
            ("D", "B"), ("B", "F"),
            # More expensive alternatives ensure routing is actually decided.
            ("D", "F"), ("A", "B"),
        },
        "depot": "D",
        "final": "F",
        "d_ij": {
            ("D", "A"): 2.0, ("A", "F"): 2.0,
            ("D", "B"): 6.0, ("B", "F"): 6.0,
            ("D", "F"): 30.0, ("A", "B"): 20.0,
        },
        "S_i": {"D": 0.0, "A": 1.0, "B": 2.0, "F": 0.0},
        "A_ni": {
            ("O1", "D"): 0, ("O1", "A"): 1, ("O1", "B"): 0, ("O1", "F"): 0,
            ("O2", "D"): 0, ("O2", "A"): 0, ("O2", "B"): 1, ("O2", "F"): 0,
        },
        "Bn": {("O1", "B1"): 1, ("O1", "B2"): 0, ("O2", "B1"): 0, ("O2", "B2"): 1},
        "C_n": {"O1": 1.0, "O2": 1.0},
        "Dd": {"O1": 100.0, "O2": 100.0},
        "W_full": 1.0,
        "W_ea_ta": 0.0,
        "W_ea": 1.0,
        "W_ta": 1.0,
        "B_time": 1.0,
        "B_setup": 1.0,
        "B_picking": 1.0,
        "C_v": 10.0,
        "M": 10000.0,
        "V_p": {"P_slow": 1.0, "P_fast": 2.0},
        "T_frio_max": 100.0,
    }


def one_cold_batch(cold_limit=10.0):
    """A batch which only the fast picker can prepare under the cold limit."""
    data = two_batches_two_routes()
    data.update(
        N={"O1"},
        B={"B1"},
        V={"D", "B", "F"},
        E={("D", "B"), ("B", "F"), ("D", "F")},
        d_ij={("D", "B"): 6.0, ("B", "F"): 6.0, ("D", "F"): 30.0},
        S_i={"D": 0.0, "B": 2.0, "F": 0.0},
        A_ni={("O1", "D"): 0, ("O1", "B"): 1, ("O1", "F"): 0},
        Bn={("O1", "B1"): 1},
        C_n={"O1": 1.0},
        Dd={"O1": 100.0},
        T_frio_max=cold_limit,
    )
    return data
