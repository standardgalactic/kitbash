#!/usr/bin/env python3
"""Reproduces every count in Chapter 8 (amendments, footprints, correction events)."""
import itertools, random
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
from lawnmodel import *

times = {1: 0, 2: 1, 3: 2, 4: 2, 5: 3}
event_time = {"a": 1, "b": 2, "c": 3}
foot = {"a": [1, 2, 3, 5], "b": [1, 3, 5], "c": [1, 4, 5]}
def side(strip, j):
    return "post" if times[j] >= event_time[strip] else "pre"
def interval_fp(strip, j):
    return [x for x in foot[strip] if side(strip, x) == side(strip, j)]

base = {p: State(p) for p in "ABC"}

def stale_list(p):
    cl = classes(p)
    return [(j + 1, k, c["wrong"]) for j in range(m) for k, c in enumerate(cl[j]) if c["stale"]]

print("== from one report to a rule: what each level covers ==")
for p in "ABC":
    sl = stale_list(p)
    total = len(sl)
    print(p, "stale classes in pool:", total)
    seen = set()
    for (j, k, s) in sl:
        key = (s, side(s, j))
        if key in seen: continue
        seen.add(key)
        iv = set(interval_fp(s, j))
        cov_i = sum(1 for (j2, k2, s2) in sl if s2 == s and j2 in iv)
        cov_e = sum(1 for (j2, k2, s2) in sl if s2 == s)
        cov_t = total
        print("   first report on strip", s, "at slot", j, "(", side(s, j), ") covers: interval", cov_i, "entity", cov_e, "type", cov_t,
              "| capacity after interval", alpha(base[p], {s}, iv).capacity(), "entity", alpha(base[p], {s}, set(foot[s])).capacity(),
              "type", alpha(base[p], {"a", "b", "c"}, {1, 2, 3, 4, 5}).capacity())

print("\n== order of arrival: interval-level amendments in every order ==")
for p in "AB":
    pairs = sorted({(s, side(s, j)) for (j, k, s) in stale_list(p)})
    N0 = base[p].capacity()
    paths = {}
    for order in itertools.permutations(pairs):
        S = base[p]; path = [N0]
        for (s, sd) in order:
            iv = {x for x in foot[s] if side(s, x) == sd}
            S = alpha(S, {s}, iv); path.append(S.capacity())
        paths[order] = path
    finals = {tuple(v)[-1] for v in paths.values()}
    print(p, "pairs", pairs, "events", len(pairs), "final capacities over all orders", finals)
    firsts = sorted({tuple(v) for v in paths.values()})
    for o, v in paths.items():
        print("   order", [x[0] + x[1][0] for x in o], "capacities", v)

print("\n== the correction event: atomic versus separate ==")
def matchable(rs):
    rids = sorted({r for l in rs for r in l})
    if not rs: return True
    if not rids: return False
    idx = {r: i for i, r in enumerate(rids)}
    rows, cols = [], []
    for i, l in enumerate(rs):
        for r in l:
            rows.append(i); cols.append(idx[r])
    M = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(rs), len(rids)))
    return int((maximum_bipartite_matching(M, perm_type="column") >= 0).sum()) == len(rs)

def repair(alloc, Pn):
    Pset = set(Pn)
    held = {t for t in alloc if t in Pset}
    inval = [i for i, t in enumerate(alloc) if t not in Pset]
    free = [t for t in Pn if t not in held]
    new = list(alloc)
    if inval:
        if len(free) < len(inval): return None
        C = np.array([[hamming(alloc[i], q) for q in free] for i in inval], float)
        r_, c_ = linear_sum_assignment(C)
        for a_, b_ in zip(r_, c_):
            new[inval[a_]] = free[b_]
    return new, len(inval)

for p in "AB":
    P = base[p].tuples()
    alloc = random.Random(2026 + ord(p)).sample(P, audience[p])
    S = base[p]; cur = list(alloc); win = []; ok = True
    for name, (strips, js) in [("alpha_a", ({"a"}, {2, 3, 5})), ("alpha_b", ({"b"}, {3, 5})), ("alpha_c", ({"c"}, {1, 4, 5}))]:
        S = alpha(S, strips, js)
        Pn = S.tuples(); Pset = set(Pn)
        r_ = repair(cur, Pn)
        new, ninv = r_
        win.append(ninv)
        # invariant after atomic event
        ok &= all(t in Pset for t in new) and len(set(new)) == len(new)
        cur = new
    print(p, "viewers on inadmissible editions if the rule precedes the repair, per event:", win, "total viewer-revisions:", sum(win),
          "| atomic events: 0; admissibility invariant holds after every event:", ok)

print("\n== when the event cannot be formed ==")
for p in "ABC":
    G = alpha(base[p], {"a", "b", "c"}, {1, 2, 3, 4, 5})
    print(p, "under G: capacity", G.capacity(), "audience", audience[p], "formable (capacity)", G.capacity() >= audience[p])
# A and B under G with per-viewer budget 1
for p in "AB":
    G = alpha(base[p], {"a", "b", "c"}, {1, 2, 3, 4, 5}); Pn = G.tuples(); Pset = set(Pn)
    alloc = random.Random(2026 + ord(p)).sample(base[p].tuples(), audience[p])
    held = {t for t in alloc if t in Pset}
    inval = [t for t in alloc if t not in Pset]
    free = [t for t in Pn if t not in held]
    res = {}
    for r in (1, 2, 3):
        res[r] = matchable([[f for f in free if hamming(t, f) <= r] for t in inval])
    print(p, "under G, survivors fixed, budget r -> repair exists:", res)

print("\n== replacement footage for C: where the clone goes ==")
G = alpha(base["C"], {"a", "b", "c"}, {1, 2, 3, 4, 5})
P0 = base["C"].tuples()
alloc = list(P0)               # two viewers, one per premiere class tuple
for j1 in range(1, 6):
    S = G.copy(); S.cl = [list(col) for col in S.cl]
    # clone the admissible class at slot j1 (class index 0 for slots 1..5 with direction L ok)
    src = next(k for k in sorted(S.dom[j1 - 1]) if not S.cl[j1 - 1][k]["stale"] and S.cl[j1 - 1][k]["dir"] == "L")
    newc = dict(S.cl[j1 - 1][src]); S.cl[j1 - 1].append(newc)
    nk = len(S.cl[j1 - 1]) - 1
    S.dom[j1 - 1].add(nk); S.takes[j1 - 1].append(newc["mu"])
    Pn = S.tuples(); Pset = set(Pn)
    held = {t for t in alloc if t in Pset}
    inval = [t for t in alloc if t not in Pset]
    free = [t for t in Pn if t not in held]
    rstar = None
    for r in range(1, 6):
        if matchable([[f for f in free if hamming(t, f) <= r] for t in inval]):
            rstar = r; break
    print("clone at slot", j1, "capacity", len(Pn), "invalid viewers", len(inval), "repair radius", rstar)

print("\n== relaxing the direction rule at one edge, after G ==")
def tuples_relaxed(S, relaxed_edge):
    out = []
    for tup in itertools.product(*[S.live(j) for j in range(m)]):
        ok = True
        for j in range(m - 1):
            if j + 1 == relaxed_edge: continue
            if not compat(S.cl[j][tup[j]]["dir"], S.cl[j + 1][tup[j + 1]]["dir"]):
                ok = False; break
        if ok: out.append(tup)
    return out
for p in "ABC":
    G = alpha(base[p], {"a", "b", "c"}, {1, 2, 3, 4, 5})
    print(p, "G capacity", G.capacity(), "| relax edge (j,j+1):", {e: len(tuples_relaxed(G, e)) for e in range(1, 5)})
