import itertools


def two_orders_two_aisles():
    V = {1, 2, 3, 4, 5, 6, 7, 8}
    H = {1, 2}
    K = {1}
    P = {1, 2}
    B = set()

    w1 = 1.0
    w2 = 10.0
    gamma = 1.0
    delta = 5.0

    M_cost = 99999
    d = {(i, j): M_cost for i, j in itertools.product(V, repeat=2)}

    d[(1, 2)] = 10
    d[(2, 3)] = 10
    d[(3, 4)] = 10
    d[(4, 8)] = 10

    d[(1, 5)] = 10
    d[(5, 6)] = 10
    d[(6, 7)] = 10
    d[(7, 8)] = 10

    x = {(p, k, h): 0 for p in P for k in K for h in H}
    x[(1, 1, 1)] = 1
    x[(2, 1, 2)] = 1

    cap_vehicle = 5.0
    cap_n = {1: 3.0, 2: 3.0}

    return V, H, K, P, B, w1, w2, gamma, delta, d, cap_vehicle, cap_n, x
