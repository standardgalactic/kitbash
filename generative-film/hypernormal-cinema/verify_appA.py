#!/usr/bin/env python3
"""Reproduces every check of Appendix A (counting and matching)."""
import itertools, random
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
from lawnmodel import *

print("== A.1 transfer matrices against enumeration")
for p in "ABC":
    for name, st in (("premiere", State(p)), ("after G", alpha(State(p), {"a", "b", "c"}, {1, 2, 3, 4, 5}))):
        lv = [st.live(j) for j in range(m)]
        v = np.ones(len(lv[0]), dtype=object)
        w = np.array([st.takes[0][k] for k in lv[0]], dtype=object)
        for j in range(1, m):
            M = np.array([[1 if compat(st.cl[j - 1][a]["dir"], st.cl[j][b]["dir"]) else 0 for b in lv[j]] for a in lv[j - 1]], dtype=object)
            v = v.dot(M)
            w = w.dot(M) * np.array([st.takes[j][k] for k in lv[j]], dtype=object)
        cnt = int(v.sum()); tk = int(w.sum())
        print(p, name, "matrix count", cnt, "enumerated", st.capacity(), "match" if cnt == st.capacity() else "MISMATCH",
              "| weighted", tk, "take tuples", st.take_tuples(), "match" if tk == st.take_tuples() else "MISMATCH")

print("== A.3 Hall's theorem against maximum matching on random bipartite graphs")
rng = random.Random(3)
bad = 0; hall_true = 0; trials = 3000
for _ in range(trials):
    n = rng.randint(1, 7); k = rng.randint(1, 8); dens = rng.choice([0.2, 0.35, 0.5])
    adj = [[j for j in range(k) if rng.random() < dens] for _ in range(n)]
    hall = all(len(set().union(*[adj[i] for i in S])) >= len(S) for r in range(1, n + 1) for S in itertools.combinations(range(n), r))
    rows = [i for i in range(n) for _ in adj[i]]; cols = [j for i in range(n) for j in adj[i]]
    if rows:
        M = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, k))
        mt = maximum_bipartite_matching(M, perm_type="column")
        full = int((mt >= 0).sum()) == n
    else:
        full = False
    hall_true += hall
    if hall != full: bad += 1
print("graphs", trials, "Hall holds in", hall_true, "disagreements with matching", bad)

print("== A.4 minimum-cost assignment: cycle criterion and dual certificate")
bad = 0; negcyc = 0
for _ in range(400):
    n = rng.randint(2, 6)
    C = np.array([[rng.randint(0, 9) for _ in range(n)] for _ in range(n)], float)
    best = min(sum(C[i, p[i]] for i in range(n)) for p in itertools.permutations(range(n)))
    r, c = linear_sum_assignment(C)
    if abs(C[r, c].sum() - best) > 1e-9: bad += 1
    # dual certificate: potentials u,v with u_i + v_j <= C_ij and equality on the assignment (Bellman-Ford on the residual graph)
    match = {i: c[k] for k, i in enumerate(r)}
    # residual graph on rows: edge i->i' with weight C[i,match[i']] - C[i,match[i]]
    W = np.array([[C[i, match[i2]] - C[i, match[i]] for i2 in range(n)] for i in range(n)])
    d = np.zeros(n)
    for _ in range(n):
        for i in range(n):
            for i2 in range(n):
                if d[i] + W[i, i2] < d[i2] - 1e-12: d[i2] = d[i] + W[i, i2]
    neg = any(d[i] + W[i, i2] < d[i2] - 1e-9 for i in range(n) for i2 in range(n))
    negcyc += neg
print("instances 400 optimal cost equals brute force in all but", bad, "; residual graphs with a negative cycle at the solver's optimum:", negcyc)

print("== A.5 packing and covering inequalities on random subsets of a Hamming space")
def hd(a, b): return sum(x != y for x, y in zip(a, b))
def max_packing(S, eps):
    best = 0
    def rec(i, chosen):
        nonlocal best
        if len(chosen) + (len(S) - i) <= best: return
        if i == len(S): best = max(best, len(chosen)); return
        if all(hd(S[i], c) > eps for c in chosen): rec(i + 1, chosen + [S[i]])
        rec(i + 1, chosen)
    rec(0, []); return best
def min_cover(S, eps):
    for k in range(1, len(S) + 1):
        for C in itertools.combinations(S, k):
            if all(any(hd(s, c) <= eps for c in C) for s in S): return k
viol = 0; cases = 0
for _ in range(60):
    space = list(itertools.product(range(3), repeat=4))
    S = rng.sample(space, rng.randint(6, 14))
    for eps in (1, 2):
        M = max_packing(S, eps); N = min_cover(S, eps); N2 = min_cover(S, eps // 2)
        cases += 1
        if not (N <= M <= N2): viol += 1
print("cases", cases, "violations of N_eps <= M_eps <= N_floor(eps/2)", viol)
print("== A.5 Singleton: largest code of length 4 over 3 symbols with distance 2 and 3 (exact, by integer programming)")
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix
space = list(itertools.product(range(3), repeat=4))
for eps in (1, 2):
    edges = [(i, j) for i in range(len(space)) for j in range(i + 1, len(space)) if hd(space[i], space[j]) <= eps]
    Am = lil_matrix((len(edges), len(space)))
    for r, (i, j) in enumerate(edges):
        Am[r, i] = 1; Am[r, j] = 1
    res = milp(-np.ones(len(space)), constraints=LinearConstraint(Am.tocsr(), -np.inf, 1), integrality=np.ones(len(space)), bounds=Bounds(0, 1), options={"time_limit": 120})
    print("distance >=", eps + 1, "largest code", int(round(-res.fun)), "optimal" if res.status == 0 else "bound only", "Singleton bound", 3 ** (4 - eps))
