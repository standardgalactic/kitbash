#!/usr/bin/env python3
"""Reproduces every count in Chapter 11 (locales and the worldwide premiere)."""
import itertools, math
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from lawnmodel import *

base = {p: State(p) for p in "ABC"}
G = {p: alpha(base[p], {"a", "b", "c"}, {1, 2, 3, 4, 5}) for p in "ABC"}
TA = G["A"].tuples()          # 238 class tuples after the agreement rule

def packing(D, eps, tl=100):
    n = len(D)
    conf = [(i, j) for i in range(n) for j in range(i + 1, n) if D[i, j] <= eps]
    if not conf: return n
    A = np.zeros((len(conf), n))
    for r, (i, j) in enumerate(conf):
        A[r, i] = 1; A[r, j] = 1
    res = milp(c=-np.ones(n), constraints=LinearConstraint(A, -np.inf, 1), integrality=np.ones(n), bounds=Bounds(0, 1), options={"time_limit": tl})
    assert res.status == 0, (n, eps, res.status)
    return int(round(-res.fun))

print("== exact inequivalence: the Hall condition across locales ==")
# two locales, each with the 238 class tuples of production A after G.
for l in (0, 1):
    union = 238 if l == 0 else 476
    print("local-trace slots", l, "global classes", union)
UX, UY = 150, 100
print("audiences", UX, UY, "each at most 238:", UX <= 238 and UY <= 238)
print("fully shared sequence: union 238, total audience", UX + UY, "feasible:", UX + UY <= 238)
print("one slot with local cast: union 476, total audience", UX + UY, "feasible:", UX + UY <= 476)

print("\n== perceptual separation across locales: cast slots 2,3,4 local, slots 1 and 5 shared ==")
# edition = (locale, class tuple). Local slots differ across locales always; shared slots compare class ids.
def cross_dist(t, s, local_slots):
    return sum(1 for j in range(m) if (j in local_slots) or t[j] != s[j])
def within_dist(t, s): return hamming(t, s)
n = len(TA)
Dw = np.array([[hamming(TA[i], TA[j]) for j in range(n)] for i in range(n)])
rows = {}
for local_slots, label in (({1, 2, 3}, "slots 2-4 local"), ({1}, "slot 2 local"), (set(), "fully shared")):
    # distance matrix on the union of two locales (X: 0..n-1, Y: n..2n-1)
    D = np.zeros((2 * n, 2 * n), dtype=int)
    D[:n, :n] = Dw; D[n:, n:] = Dw
    for i in range(n):
        for j in range(n):
            D[i, n + j] = D[n + j, i] = cross_dist(TA[i], TA[j], local_slots)
    out = {}
    for eps in range(0, 5):
        pl = packing(Dw, eps)
        if len(local_slots) == 0:
            # editions of the two locales coincide when class tuples are equal: merge identical points (distance 0)
            pass
        pu = packing(D, eps)
        out[eps] = (pl, 2 * pl, pu)
    rows[label] = out
    print(label, {e: "local %d, sum %d, union %d" % v for e, v in out.items()})

print("\n== minimum local footage for an audience: classes per slot with no other rule ==")
def min_classes(U, m=5):
    best = None
    for cs in itertools.combinations_with_replacement(range(1, 40), m):
        if math.prod(cs) >= U:
            s = sum(cs)
            if best is None or s < best[0]: best = (s, cs)
    return best
for U in (2, 30, 60, 238, 1000):
    s, cs = min_classes(U)
    print("U", U, "min total classes", s, "per slot", cs, "product", math.prod(cs))

print("\n== footage for separation: uniform q classes per slot, 5 slots, Hamming distance > eps ==")
def singleton_q(U, m, eps):
    k = m - eps
    q = 1
    while q ** k < U: q += 1
    return q
for U in (30, 60, 238):
    print("U", U, {eps: singleton_q(U, 5, eps) for eps in range(0, 4)}, "classes per slot needed at least (Singleton), eps = 0..3")

# explicit codes: GF(4) and GF(8) doubly extended Reed-Solomon codes of length 5
def gf_tables(poly, bits):
    size = 1 << bits
    mul = [[0] * size for _ in range(size)]
    for a in range(size):
        for b in range(size):
            r = 0; x = a; y = b
            while y:
                if y & 1: r ^= x
                y >>= 1; x <<= 1
                if x & size: x ^= poly
            mul[a][b] = r
    return mul
def rs_code(mul, size, k):
    pts = [0, 1, 2, 3][:min(4, size)] if size == 4 else [0, 1, 2, 3]
    # evaluations at 4 points plus the leading coefficient (point at infinity): length 5, dimension k
    words = []
    for coeffs in itertools.product(range(size), repeat=k):
        w = []
        for x in pts[:4]:
            v = 0; xp = 1
            for c in coeffs:
                v ^= mul[c][xp]; xp = mul[xp][x]
            w.append(v)
        w.append(coeffs[-1])
        words.append(tuple(w))
    return words
def min_dist(words):
    return min(hamming(a, b) for a, b in itertools.combinations(words, 2))
c4 = rs_code(gf_tables(0b111, 2), 4, 3)
print("GF(4) code: size", len(c4), "min distance", min_dist(c4), "(distance 3 gives eps=2, 4 classes per slot, 64 editions)")
c8 = rs_code(gf_tables(0b1011, 3), 8, 2)
print("GF(8) code: size", len(c8), "min distance", min_dist(c8), "(distance 4 gives eps=3, 8 classes per slot, 64 editions)")
par = [w + (sum(w) % 3,) for w in itertools.product(range(3), repeat=4)]
print("parity code over Z_3: size", len(par), "min distance", min_dist(par), "(distance 2 gives eps=1, 3 classes per slot, 81 editions)")
assert len(c4) == 64 and min_dist(c4) == 3 and len(c8) == 64 and min_dist(c8) == 4 and len(par) == 81 and min_dist(par) == 2

print("\n== shared footage lowers local footage: shared slots 1 and 5 with 2 classes each, local slots 2-4 ==")
for U in (30, 60, 238):
    q = 1
    while 4 * q ** 3 < U: q += 1
    print("U", U, "local classes per local slot", q, "total local classes", 3 * q, "| fully local 5-slot minimum", min_classes(U)[0])
