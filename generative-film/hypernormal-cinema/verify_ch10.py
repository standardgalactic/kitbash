#!/usr/bin/env python3
"""Reproduces every count in Chapter 10 (repairability from a current allocation)."""
import random, itertools
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
from lawnmodel import *

base = {p: State(p) for p in "ABC"}
amend = {
    "alpha_a": lambda s: alpha(s, {"a"}, {2, 3, 5}),
    "alpha_b": lambda s: alpha(s, {"b"}, {3, 5}),
    "alpha_c": lambda s: alpha(s, {"c"}, {1, 4, 5}),
    "G": lambda s: alpha(s, {"a", "b", "c"}, {1, 2, 3, 4, 5}),
}

def draw(p, seed=None):
    P = base[p].tuples()
    rng = random.Random(2026 + ord(p) if seed is None else seed)
    return rng.sample(P, audience[p])

def matchable(left, right_sets):
    """does every left item have a distinct partner? right_sets: list of lists of right ids"""
    rids = sorted({r for rs in right_sets for r in rs})
    idx = {r: i for i, r in enumerate(rids)}
    if not rids:
        return len(left) == 0
    rows, cols = [], []
    for i, rs in enumerate(right_sets):
        for r in rs:
            rows.append(i); cols.append(idx[r])
    M = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(right_sets), len(rids)))
    mt = maximum_bipartite_matching(M, perm_type="column")
    return int((mt >= 0).sum()) == len(right_sets)

def radius_fixed(alloc, Pn, rmax=5):
    """smallest r so invalid viewers can be placed in free valid tuples within Hamming r, survivors fixed"""
    Pset = set(Pn)
    held = {t for t in alloc if t in Pset}
    invalid = [t for t in alloc if t not in Pset]
    if not invalid:
        return 0, 0
    free = [t for t in Pn if t not in held]
    for r in range(1, rmax + 1):
        rs = [[f for f in free if hamming(t, f) <= r] for t in invalid]
        if matchable(invalid, rs):
            return r, len(invalid)
    return None, len(invalid)

def radius_free(alloc, Pn, rmax=5):
    """all viewers may move; each moves at most r (Hamming), final tuples distinct and valid"""
    for r in range(0, rmax + 1):
        rs = [[q for q in Pn if hamming(t, q) <= r] for t in alloc]
        if matchable(alloc, rs):
            return r
    return None

def min_total(alloc, Pn, lam=0.0):
    """min total Hamming movement, all viewers free; returns (cost, moved viewers)"""
    n = len(alloc)
    if len(Pn) < n:
        return None
    C = np.array([[hamming(t, q) for q in Pn] for t in alloc], float)
    r_, c_ = linear_sum_assignment(C)
    moved = sum(1 for i, j in zip(r_, c_) if alloc[i] != Pn[j])
    return int(C[r_, c_].sum()), moved

def min_total_fixed(alloc, Pn):
    Pset = set(Pn)
    held = {t for t in alloc if t in Pset}
    invalid = [t for t in alloc if t not in Pset]
    free = [t for t in Pn if t not in held]
    if len(free) < len(invalid):
        return None
    if not invalid:
        return 0
    C = np.array([[hamming(t, q) for q in free] for t in invalid], float)
    r_, c_ = linear_sum_assignment(C)
    return int(C[r_, c_].sum())

def ball_radius(alloc, Pn, U, rmax=5):
    """smallest r with every invalid viewer's ball holding >= U valid tuples (sufficient for matching)"""
    Pset = set(Pn)
    invalid = [t for t in alloc if t not in Pset]
    for r in range(0, rmax + 1):
        if all(sum(1 for q in Pn if hamming(t, q) <= r) >= U for t in invalid):
            return r
    return None

print("== Chapter 10 table: one audience per production, each amendment ==")
rows = {}
for p in "ABC":
    alloc = draw(p)
    for name, f in amend.items():
        S = f(base[p]); Pn = S.tuples()
        rf, ninv = radius_fixed(alloc, Pn)
        rfree = radius_free(alloc, Pn)
        tot = min_total(alloc, Pn)
        totf = min_total_fixed(alloc, Pn)
        br = ball_radius(alloc, Pn, audience[p])
        rows[(p, name)] = (ninv, len(Pn), rf, rfree, totf, tot, br)
        print(p, name, "invalid", ninv, "capacity", len(Pn), "audience", audience[p],
              "| r* fixed", rf, "| r* free", rfree, "| cost fixed", totf, "| cost free", tot, "| ball radius", br)

print("\n== capacity slack but r* > 1: search random allocations ==")
best = None
for p in "AB":
    for name in amend:
        S = amend[name](base[p]); Pn = S.tuples()
        worst = (0, None)
        for seed in range(400):
            alloc = draw(p, seed)
            rf, ninv = radius_fixed(alloc, Pn)
            if rf is not None and rf > worst[0]:
                worst = (rf, seed, ninv)
        print(p, name, "capacity", len(Pn), "audience", audience[p], "worst r* fixed over 400 audiences:", worst)

print("\n== a witness with r*=2 survivors fixed (and r* free) ==")
found = None
for p in "AB":
    for name in amend:
        S = amend[name](base[p]); Pn = S.tuples()
        for seed in range(2000):
            alloc = draw(p, seed)
            rf, ninv = radius_fixed(alloc, Pn)
            if rf is not None and rf >= 2:
                rfree = radius_free(alloc, Pn)
                found = (p, name, seed, rf, rfree, ninv, len(Pn))
                break
        if found: break
    if found: break
print(found)

print("\n== the capacity-versus-repair gap: small adversarial instance ==")
# two viewers on invalid tuples whose only valid tuple within radius 1 is the same free tuple
for p in "AB":
    for name in amend:
        S = amend[name](base[p]); Pn = S.tuples(); Pset = set(Pn)
        allP = base[p].tuples()
        inval = [t for t in allP if t not in Pset]
        for t1, t2 in itertools.combinations(inval, 2):
            n1 = [q for q in Pn if hamming(t1, q) <= 1]
            n2 = [q for q in Pn if hamming(t2, q) <= 1]
            if len(n1) == 1 and n1 == n2:
                print(p, name, "viewers", t1, t2, "share sole radius-1 replacement", n1[0], "while capacity is", len(Pn))
                break
        else:
            continue
        break
    else:
        continue
    break

print("\n== sequence of amendments: drift ==")
for p in "AB":
    alloc = draw(p)
    cur = list(alloc)
    total_move = [0] * len(alloc)
    for name in ["alpha_a", "alpha_b", "alpha_c"]:
        Pn = amend[name](base[p]).tuples()  # each amendment individually applied to premiere pool
    # cumulative: apply in turn
    S = base[p]
    for name, (strips, js) in [("alpha_a", ({"a"}, {2, 3, 5})), ("alpha_b", ({"b"}, {3, 5})), ("alpha_c", ({"c"}, {1, 4, 5}))]:
        S = alpha(S, strips, js); Pn = S.tuples(); Pset = set(Pn)
        inval = [i for i, t in enumerate(cur) if t not in Pset]
        held = {t for t in cur if t in Pset}
        free = [t for t in Pn if t not in held]
        rf = None
        for r in range(1, 6):
            rs = [[f for f in free if hamming(cur[i], f) <= r] for i in inval]
            if not inval or matchable(inval, rs):
                rf = r if inval else 0; break
        # perform min-cost repair with survivors fixed
        if inval:
            C = np.array([[hamming(cur[i], q) for q in free] for i in inval], float)
            r_, c_ = linear_sum_assignment(C)
            for a_, b_ in zip(r_, c_):
                i = inval[a_]
                total_move[i] += hamming(cur[i], free[b_])
                cur[i] = free[b_]
        print(p, name, "capacity", len(Pn), "invalid", len(inval), "r*", rf, "max accumulated movement", max(total_move), "viewers moved", sum(1 for x in total_move if x))
    # compare with one repair against intersection G-type pool
    Pn = S.tuples()
    rf, ninv = radius_fixed(alloc, Pn)
    print(p, "one repair straight to the cumulative pool:", "invalid", ninv, "r*", rf)

print("\n== reproducibility: ledger replay ==")
# assignment as keyed permutation over sorted class tuples: repair deterministic given ledger
import hashlib
def keyed_alloc(p, Pn, key):
    order = sorted(Pn, key=lambda t: hashlib.sha256((key + repr(t)).encode()).hexdigest())
    return order[:audience[p]]
for p in "AB":
    a1 = keyed_alloc(p, base[p].tuples(), "k")
    Pn = amend["G"](base[p]).tuples()
    Pset = set(Pn)
    inval = [t for t in a1 if t not in Pset]
    free = [t for t in sorted(Pn) if t not in set(a1)]
    C = np.array([[hamming(t, q) for q in free] for t in inval], float) if inval else None
    runs = []
    for _ in range(2):
        if inval:
            r_, c_ = linear_sum_assignment(C)
            runs.append(tuple(free[j] for j in c_))
        else:
            runs.append(())
    print(p, "invalid", len(inval), "two replays identical:", runs[0] == runs[1])
