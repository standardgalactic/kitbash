#!/usr/bin/env python3
"""Reproduces every count in Chapter 2 (perceptual equivalence and the measurement of difference)."""
import itertools
import numpy as np
from collections import Counter
from scipy.optimize import milp, LinearConstraint, Bounds
from lawnmodel import *

base = {p: State(p) for p in "ABC"}
G = {p: alpha(base[p], {"a", "b", "c"}, {1, 2, 3, 4, 5}) for p in "ABC"}

def dist_matrix(T, d):
    n = len(T)
    D = np.zeros((n, n), dtype=int)
    for i in range(n):
        for j in range(i + 1, n):
            D[i, j] = D[j, i] = d(T[i], T[j])
    return D

def packing(D, eps):
    n = len(D)
    if n == 0: return 0
    if eps < 0: return n
    conf = [(i, j) for i in range(n) for j in range(i + 1, n) if D[i, j] <= eps]
    if not conf: return n
    A = np.zeros((len(conf), n))
    for r, (i, j) in enumerate(conf):
        A[r, i] = 1; A[r, j] = 1
    res = milp(c=-np.ones(n), constraints=LinearConstraint(A, -np.inf, 1), integrality=np.ones(n), bounds=Bounds(0, 1), options={'time_limit': 100})
    assert res.status == 0, ('packing not optimal', n, eps, res.status)
    return int(round(-res.fun))

def covering(D, eps):
    n = len(D)
    if n == 0: return 0
    A = (D <= eps).astype(float)       # rows: points, cols: centres
    res = milp(c=np.ones(n), constraints=LinearConstraint(A, 1, np.inf), integrality=np.ones(n), bounds=Bounds(0, 1), options={'time_limit': 100})
    ub = int(round(res.fun))
    lb = int(np.ceil(res.mip_dual_bound - 1e-6)) if res.status != 0 else ub
    return (lb, ub)

print("== three notions of difference on the admissible editions after G ==")
def cls(p, t, j): return base[p].cl[j][t[j]]
for p in "ABC":
    for name, S in (("R0", base[p]), ("R1", G[p])):
        T = S.tuples()
        det = len(T)
        aff = len({tuple(cls(p, t, j)["dir"] for j in range(m)) for t in T})
        comp = len({tuple(cls(p, t, j)["stale"] for j in range(m)) for t in T})
        print(p, name, "detection (class tuples)", det, "| affective (direction sequences)", aff, "| comprehension (stale pattern)", comp)

print("\n== thresholded similarity is not transitive (Hamming on class tuples, after G) ==")
for p in "AB":
    T = G[p].tuples(); D = dist_matrix(T, hamming)
    n = len(T)
    for eps in (1, 2):
        S = (D <= eps)
        bad = 0
        total = 0
        # count ordered triples x,y,z distinct with x~y, y~z, not x~z
        for y in range(n):
            nb = np.where(S[y])[0]; nb = nb[nb != y]
            for a_ in nb:
                for b_ in nb:
                    if a_ < b_:
                        total += 1
                        if not S[a_, b_]: bad += 1
        # connected components of the eps-similarity graph
        seen = [False] * n; comps = 0
        for s0 in range(n):
            if seen[s0]: continue
            comps += 1; stack = [s0]; seen[s0] = True
            while stack:
                u = stack.pop()
                for v in np.where(S[u])[0]:
                    if not seen[v]: seen[v] = True; stack.append(v)
        print(p, "eps", eps, "editions", n, "wedges (x~y~z)", total, "of which x not~ z", bad, "| components of similarity graph", comps)

print("\n== packing and covering numbers (Hamming, after G) ==")
rows = {}
for p in "AB":
    T = G[p].tuples(); D = dist_matrix(T, hamming)
    for eps in range(0, 3):
        M = packing(D, eps); N = covering(D, eps)
        Nhalf = covering(D, eps // 2)
        N_lb, N_ub = N; Nh_lb, Nh_ub = Nhalf
        assert N_lb <= M and M <= Nh_ub, (p, eps, M, N, Nhalf)
        print(p, "eps", eps, "packing M", M, "| covering N in [", N_lb, ",", N_ub, "] | N(floor(eps/2)) in [", Nh_lb, ",", Nh_ub, "]",
              "| log2 N <=", round(float(np.log2(N_ub)), 2), "log2 M", round(float(np.log2(M)), 2))
print("N(eps) <= M(eps) <= N(floor(eps/2)) is consistent with every computed bound")

print("\n== local productions with shared footage: labels (direction, status, index within group) ==")
def labels(p):
    out = []
    for j in range(m):
        cnt = Counter(); lab = []
        for k, c in enumerate(base[p].cl[j]):
            key = (c["dir"], c["stale"])
            lab.append((c["dir"], c["stale"], cnt[key])); cnt[key] += 1
        out.append(lab)
    return out
LA, LB = labels("A"), labels("B")
def label_tuples(p, L):
    return {tuple(L[j][t[j]] for j in range(m)) for t in G[p].tuples()}
TA, TB = label_tuples("A", LA), label_tuples("B", LB)
inter = TA & TB
union = sorted(TA | TB)
print("A after G", len(TA), "B after G", len(TB), "shared label tuples", len(inter), "union", len(union), "sum", len(TA) + len(TB))
def lab_h(x, y): return sum(1 for a, b in zip(x, y) if a != b)
Du = dist_matrix(union, lab_h)
DA = dist_matrix(sorted(TA), lab_h); DB = dist_matrix(sorted(TB), lab_h)
print("exact inequivalence: global capacity", len(union), "versus disjoint sum", len(TA) + len(TB))
for eps in (1, 2):
    pu = packing(Du, eps); pa = packing(DA, eps); pb = packing(DB, eps)
    print("eps", eps, "packing A", pa, "B", pb, "sum", pa + pb, "| packing of the union with shared footage", pu)

print("\n== disjoint footage: cross distance is the full slot count ==")
print("every cross pair differs at all", m, "slots, so the union packs to the sum for every eps <", m)
