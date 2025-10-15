import itertools


def two_orders_two_aisles():
    V = {"L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"}
    H = {"M1", "M2"}
    K = {1}
    P = {"P1", "P2"}
    B = set()

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    M_cost = 99999
    d = {(i, j): M_cost for i, j in itertools.product(V, repeat=2)}

    d[("L1", "L2")] = 10
    d[("L2", "L3")] = 10
    d[("L3", "L4")] = 10
    d[("L4", "L8")] = 10

    d[("L1", "L5")] = 10
    d[("L5", "L6")] = 10
    d[("L6", "L7")] = 10
    d[("L7", "L8")] = 10

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[("P1", 1, "M1")] = 1
    x[("P2", 1, "M2")] = 1

    cap_vehicle = 5.0

    return V, H, K, P, B, w1, w2, gamma, delta, d, cap_vehicle, x
