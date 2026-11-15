#!/usr/bin/env python3
"""Reproduces every count in Chapter 15 (exclusion and reference corpora), on the lawn scene after the agreement rule."""
import random, itertools, statistics
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix
from lawnmodel import *

G = {p: alpha(State(p), {"a", "b", "c"}, {1, 2, 3, 4, 5}) for p in "AB"}
P = {p: G[p].tuples() for p in "AB"}
full = {p: list(itertools.product(*[range(len(c)) for c in State(p).cl])) for p in "AB"}
print("pool sizes", {p: len(P[p]) for p in P}, "full product", {p: len(full[p]) for p in full})

print("== A. exact subtraction")
for p in "AB":
    st = G[p]
    tt = st.take_tuples()
    mus = lambda t: np.prod([st.takes[j][t[j]] for j in range(m)])
    per = sorted({int(mus(t)) for t in P[p]})
    print(p, "class tuples", len(P[p]), "take tuples", tt, "takes removed by excluding one class tuple", per,
          "excluding 10 class tuples removes", 10, "class tuples and", 10 * per[0], "take tuples" if len(per) == 1 else "(varies)")
    print("   excluding 1,000 take tuples by digest leaves", tt - 1000)

def ball_remove(pool, X, rho):
    return [t for t in pool if all(hamming(t, x) > rho for x in X)]

_CL = {p: State(p).cl for p in "AB"}
def dirpat(p, t):
    return tuple(_CL[p][j][t[j]]["dir"] for j in range(m))

print("== B. approximate subtraction: survivors after n excluded items")
rng = random.Random(15)
for p in "AB":
    pool = P[p]
    print(p, "pool", len(pool))
    for src in ("corpus drawn from the pool", "corpus drawn from the full class product"):
        for n in (1, 5, 10, 20):
            res = {}
            for lab, f in (("exact", lambda X: ball_remove(pool, X, 0)), ("rho1", lambda X: ball_remove(pool, X, 1)),
                           ("rho2", lambda X: ball_remove(pool, X, 2)),
                           ("dirpattern", lambda X: [t for t in pool if dirpat(p, t) not in {dirpat(p, x) for x in X}])):
                v = []
                for _ in range(60):
                    X = rng.sample(pool if src.startswith("corpus drawn from the pool") else full[p], n)
                    v.append(len(f(X)))
                res[lab] = round(statistics.mean(v), 1)
            print("   ", src, "n", n, res)
    # ball sizes
    for rho in (1, 2):
        sizes = [sum(1 for u in pool if hamming(t, u) <= rho) for t in pool]
        print("   ball radius", rho, "mean size in pool %.1f" % statistics.mean(sizes), "min", min(sizes), "max", max(sizes))
    pats = Counter = {}
    from collections import Counter
    c = Counter(dirpat(p, t) for t in pool)
    print("   distinct direction patterns", len(c), "largest group", max(c.values()), "mean group %.1f" % (len(pool) / len(c)))

print("== C. grammar: classes that lose all tuples")
for p in "AB":
    pool = P[p]
    base_cnt = {}
    for t in pool:
        for j in range(m):
            base_cnt[(j, t[j])] = base_cnt.get((j, t[j]), 0) + 1
    print(p, "(slot,class) pairs in pool", len(base_cnt), "fewest tuples through a class", min(base_cnt.values()), "most", max(base_cnt.values()))
    for rho in (0, 1, 2):
        for n in (1, 5, 10, 20):
            lost = []; low = []
            for _ in range(60):
                X = rng.sample(pool, n)
                S = ball_remove(pool, X, rho)
                cnt = {}
                for t in S:
                    for j in range(m):
                        cnt[(j, t[j])] = cnt.get((j, t[j]), 0) + 1
                lost.append(sum(1 for k in base_cnt if cnt.get(k, 0) == 0))
                low.append(sum(1 for k in base_cnt if cnt.get(k, 0) < 0.05 * base_cnt[k]))
            print("   rho", rho, "n", n, "mean classes with no surviving tuple %.2f" % statistics.mean(lost),
                  "mean classes below 5%% of original %.2f" % statistics.mean(low))

def packing(nodes, eps, tl=40):
    n = len(nodes)
    if n == 0: return 0, True
    A = lil_matrix((0, n))
    rows = []
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if hamming(nodes[i], nodes[j]) <= eps]
    if not edges: return n, True
    Am = lil_matrix((len(edges), n))
    for r, (i, j) in enumerate(edges):
        Am[r, i] = 1; Am[r, j] = 1
    res = milp(-np.ones(n), constraints=LinearConstraint(Am.tocsr(), -np.inf, 1), integrality=np.ones(n), bounds=Bounds(0, 1),
               options={"time_limit": tl})
    val = int(round(-res.fun)) if res.x is not None else None
    return val, res.status == 0

print("== D. packing number after removing balls (rho <= eps/2)")
rng = random.Random(150)
for p, eps, rho in (("A", 2, 1), ("B", 2, 1), ("A", 1, 0), ("B", 1, 0)):
    pool = P[p]
    M0, ok0 = packing(pool, eps)
    out = [("base", len(pool), M0, ok0)]
    X = rng.sample(pool, 20)
    for n in (1, 3, 5, 10):
        S = ball_remove(pool, X[:n], rho)
        Mn, okn = packing(S, eps)
        out.append((n, len(S), Mn, okn, "bound >=", M0 - n))
    print(p, "eps", eps, "rho", rho, out)
