#!/usr/bin/env python3
"""Reproduces every count in Chapter 9 (capacity, survival, robustness)."""
import itertools
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from lawnmodel import *

print("== stale classes and the strip they misdepict ==")
for prod in "ABC":
    cl = classes(prod)
    print(prod, [(j + 1, c["dir"], c["wrong"]) for j in range(m) for c in cl[j] if c["stale"]])

base = {p: State(p) for p in "ABC"}
print("\n== capacity at the premiere (direction rule only) ==")
for p in "ABC":
    print(p, "capacity", base[p].capacity(), "audience", audience[p], "spare", base[p].capacity() - audience[p], "take tuples", base[p].take_tuples())

family = {
    "alpha_a": lambda s: alpha(s, {"a"}, {2, 3, 5}),
    "alpha_b": lambda s: alpha(s, {"b"}, {3, 5}),
    "alpha_c": lambda s: alpha(s, {"c"}, {1, 4, 5}),
    "G": lambda s: alpha(s, {"a", "b", "c"}, {1, 2, 3, 4, 5}),
    "omega": lambda s: omega(s, 1),
}
print("\n== amendments: capacity, classes lost, take tuples ==")
res = {}
for p in "ABC":
    N0 = base[p].capacity()
    for name, f in family.items():
        s = f(base[p])
        res[(p, name)] = s
        print(p, name, "capacity", s.capacity(), "lost", N0 - s.capacity(), "take tuples", s.take_tuples(), "survives audience", s.capacity() >= audience[p])

print("\n== zero spare capacity: production C ==")
S = base["C"]
print("C capacity", S.capacity(), "audience", audience["C"], "zero spare:", S.capacity() == audience["C"])
for name in family:
    s = res[("C", name)]
    retained = set(S.tuples()) <= set(s.tuples()) and set(s.tuples()) == set(S.tuples())
    print("  ", name, "classes retained:", s.capacity() == S.capacity(), "(capacity", s.capacity(), ")")
print("  omega leaves take tuples", res[("C", "omega")].take_tuples(), "of", S.take_tuples())

print("\n== worst single-class withdrawal ==")
worst = {}
for p in "ABC":
    cnt = through_counts(base[p])
    (j, k), v = max(cnt.items(), key=lambda kv: (kv[1], -kv[0][0], -kv[0][1]))
    worst[p] = (j + 1, k, v)
    print(p, "slot", j + 1, "class", k, "dir", base[p].cl[j][k]["dir"], "stale", base[p].cl[j][k]["stale"], "tuples through it", v, "of", base[p].capacity())
    # check by recomputation
    assert withdraw_class(base[p], j + 1, k).capacity() == base[p].capacity() - v

print("\n== robust capacity (alternatives) and invariant capacity (intersection) ==")
for p in "ABC":
    j1, k, v = worst[p]
    fam = {name: res[(p, name)] for name in ["alpha_a", "alpha_b", "alpha_c", "omega"]}
    fam["x*"] = withdraw_class(base[p], j1, k)
    caps = {n: s.capacity() for n, s in fam.items()}
    inter = intersect(list(fam.values()))
    print(p, caps, "robust capacity", min(caps.values()), "invariant capacity", inter.capacity(), "audience", audience[p],
          "robust at audience:", min(caps.values()) >= audience[p], "invariant at audience:", inter.capacity() >= audience[p])
    # pair intersections
    names = list(fam)
    pair = {(a, b): intersect([fam[a], fam[b]]).capacity() for a, b in itertools.combinations(names, 2)}
    lowest = min(pair.items(), key=lambda kv: kv[1])
    print("   lowest pairwise intersection", lowest)

print("\n== threshold separation with Hamming dissimilarity ==")


def packing(tuples, eps):
    """largest subset with pairwise Hamming distance > eps, by integer programming"""
    n = len(tuples)
    if n == 0:
        return 0
    if eps == 0:
        return n
    conflicts = [(i, j) for i in range(n) for j in range(i + 1, n) if hamming(tuples[i], tuples[j]) <= eps]
    if not conflicts:
        return n
    A = np.zeros((len(conflicts), n))
    for r, (i, j) in enumerate(conflicts):
        A[r, i] = 1
        A[r, j] = 1
    res_ = milp(c=-np.ones(n), constraints=LinearConstraint(A, -np.inf, 1), integrality=np.ones(n), bounds=Bounds(0, 1))
    return int(round(-res_.fun))


for p in "AB":
    for eps in (1, 2):
        row = {"premiere": packing(base[p].tuples(), eps)}
        for name in ["alpha_a", "alpha_b", "alpha_c", "G"]:
            row[name] = packing(res[(p, name)].tuples(), eps)
        print(p, "eps", eps, row)

# class tuples at distance zero from each other collapse: retention argument
print("\n== toy line example for the threshold ==")
pts = [0.0, 0.6, 1.2, 1.8]
eps = 1.0


def packnum(P):
    best = 0
    for r_ in range(len(P) + 1):
        for sub in itertools.combinations(P, r_):
            if all(abs(x - y) > eps for x, y in itertools.combinations(sub, 2)):
                best = max(best, r_)
    return best


print("all four:", packnum(pts))
for gone in pts:
    rest = [x for x in pts if x != gone]
    print("remove", gone, "packing", packnum(rest))
for gone in itertools.combinations(pts, 2):
    rest = [x for x in pts if x not in gone]
    print("remove", gone, "packing", packnum(rest))

print("\n== reserve footage: cloning a class ==")
# C under G: capacity 1; add a perceptually distinct clone of the admissible class at slot 5
s = res[("C", "G")]
print("C after G capacity", s.capacity())
cnt = through_counts(s)
print("tuples through each class after G:", cnt)
# build state with a clone at slot 5 (index 4) of class 0
c2 = s.copy()
newc = dict(c2.cl[4][0])
c2.cl = [list(col) for col in c2.cl]
c2.cl[4].append(newc)
c2.dom[4].add(len(c2.cl[4]) - 1)
c2.takes[4].append(newc["mu"])
print("after cloning the slot 5 class: capacity", c2.capacity(), "gain equals tuples through source:", c2.capacity() - s.capacity() == cnt[(4, 0)])
for p in "AB":
    s = res[(p, "G")]
    cnt = through_counts(s)
    for (j, k), v in sorted(cnt.items(), key=lambda kv: -kv[1])[:1]:
        c3 = s.copy()
        c3.cl = [list(col) for col in c3.cl]
        newc = dict(c3.cl[j][k])
        c3.cl[j].append(newc)
        c3.dom[j].add(len(c3.cl[j]) - 1)
        c3.takes[j].append(newc["mu"])
        print(p, "after G: clone of slot", j + 1, "class", k, "adds", c3.capacity() - s.capacity(), "= tuples through source", v)


print("\n== family of anticipated amendments without the worst-class withdrawal ==")
for p in "ABC":
    fam = {name: res[(p, name)] for name in ["alpha_a", "alpha_b", "alpha_c", "omega"]}
    caps = {n: x.capacity() for n, x in fam.items()}
    inter = intersect(list(fam.values()))
    print(p, caps, "robust capacity", min(caps.values()), "invariant capacity", inter.capacity(), "audience", audience[p])

print("\n== threshold, zero spare capacity ==")
# B at eps=1 with U equal to the premiere packing number
P = base["B"].tuples()
U1 = packing(P, 1)
print("B eps=1 premiere packing", U1)
for name in ["alpha_a", "alpha_b", "alpha_c", "G", "omega"]:
    sT = res[("B", name)].tuples()
    print("  ", name, "classes", len(sT), "lost", len(P) - len(sT), "packing", packing(sT, 1), "survives at U =", U1, ":", packing(sT, 1) >= U1)
