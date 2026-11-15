#!/usr/bin/env python3
"""Reproduces every count in Chapter 12 (ledgers, archives, and the release slider)."""
import random, itertools, math
import numpy as np
from scipy.optimize import linear_sum_assignment
from lawnmodel import *

base = {p: State(p) for p in "ABC"}
final = {p: alpha(base[p], {"a", "b", "c"}, {1, 2, 3, 4, 5}) for p in "ABC"}
steps = [("alpha_a", lambda s: alpha(s, {"a"}, {2, 3, 5})),
         ("alpha_b", lambda s: alpha(s, {"b"}, {3, 5})),
         ("alpha_c", lambda s: alpha(s, {"c"}, {1, 4, 5}))]

def draw(p):
    rng = random.Random(2026 + ord(p))
    return rng.sample(base[p].tuples(), audience[p])

def take_draw(p, alloc):
    rng = random.Random(7000 + ord(p))
    return [tuple(rng.randrange(base[p].cl[j][t[j]]["mu"]) for j in range(m)) for t in alloc]

def repair(alloc, Pn):
    Pset = set(Pn)
    held = {t for t in alloc if t in Pset}
    inv = [i for i, t in enumerate(alloc) if t not in Pset]
    free = [t for t in Pn if t not in held]
    if not inv:
        return list(alloc), 0, 0, 0
    C = np.array([[hamming(alloc[i], q) for q in free] for i in inv], float)
    r_, c_ = linear_sum_assignment(C)
    new = list(alloc)
    for a, b in zip(r_, c_):
        new[inv[a]] = free[b]
    d = [hamming(alloc[inv[a]], free[b]) for a, b in zip(r_, c_)]
    return new, len(inv), max(d), int(sum(d))

print("== A. record size and assets")
for p in "ABC":
    st = base[p]
    P = st.tuples()
    nclass = [len(c) for c in st.cl]
    mus = [[c["mu"] for c in col] for col in st.cl]
    total_takes = sum(sum(x) for x in mus)
    stale_takes = sum(c["mu"] for col in st.cl for c in col if c["stale"])
    stale_classes = sum(1 for col in st.cl for c in col if c["stale"])
    tt = st.take_tuples()
    bits_ct = sum(math.ceil(math.log2(n)) for n in nclass) if max(nclass) > 1 else 0
    bits_take = sum(math.ceil(math.log2(max(c["mu"] for c in col))) if max(c["mu"] for c in col) > 1 else 0 for col in st.cl)
    print(p, "classes per slot", nclass, "takes total", total_takes, "stale classes", stale_classes,
          "stale takes", stale_takes, "premiere take tuples", tt,
          "log2 take tuples %.2f -> %d bits" % (math.log2(tt), math.ceil(math.log2(tt))),
          "slotwise class bits", bits_ct, "take bits", bits_take, "total", bits_ct + bits_take)
    print("   class tuples premiere", len(P), "after G", final[p].capacity(), "take tuples after G", final[p].take_tuples(),
          "takes live after G", sum(final[p].takes[j][k] for j in range(m) for k in final[p].dom[j]))

print("== B. reconstruction after the final amendment, by retention policy")
alloc, takes = {}, {}
for p in "ABC":
    alloc[p] = draw(p); takes[p] = take_draw(p, alloc[p])
    Pg = set(final[p].tuples())
    inv = [i for i, t in enumerate(alloc[p]) if t not in Pg]
    ref = set()
    for i in inv:
        for j in range(m):
            k = alloc[p][i][j]
            if base[p].cl[j][k]["stale"]:
                ref.add((j, k, takes[p][i][j]))
    refall = set()
    for i, t in enumerate(alloc[p]):
        for j in range(m):
            refall.add((j, t[j], takes[p][i][j]))
    stale_ref = {x for x in refall if base[p].cl[x[0]][x[1]]["stale"]}
    print(p, "viewers", len(alloc[p]), "hold a stale class", len(inv),
          "distinct stale takes referenced", len(stale_ref), "of", sum(c["mu"] for col in base[p].cl for c in col if c["stale"]),
          "distinct takes referenced by ledger", len(refall))
    print("   viewers whose edition cannot be reconstructed if stale takes are purged:", len(inv))

print("== C. take-level withdrawal (variant 0 of every class), viewers whose played edition uses it")
for p in "ABC":
    hit = sum(1 for tk in takes[p] if any(x == 0 for x in tk))
    slots_hit = sum(sum(1 for x in tk if x == 0) for tk in takes[p])
    print(p, "viewers", len(takes[p]), "with a variant-0 take", hit, "take slots", slots_hit, "of", m * len(takes[p]))

print("== D. anonymity set given observed slots (class level, premiere allocation)")
for p in "ABC":
    n = len(alloc[p])
    row = []
    for s in range(1, m + 1):
        tot = 0; cnt = 0
        for S in itertools.combinations(range(m), s):
            for a in alloc[p]:
                tot += sum(1 for b in alloc[p] if all(a[j] == b[j] for j in S)); cnt += 1
        row.append(round(tot / cnt, 2))
    print(p, n, "mean anonymity set for 1..5 observed slots", row)

print("== E. slider timeline: sequential repair versus one shot versus anticipated allocation")
for p in "ABC":
    cur = list(alloc[p]); Pn_state = base[p]
    hist = [[t] for t in cur]
    line = []
    for name, f in steps:
        Pn_state = f(Pn_state)
        Pn = Pn_state.tuples()
        if len(Pn) < len(cur):
            line.append((name, "capacity", len(Pn), "< audience", len(cur))); continue
        cur, ninv, r, cost = repair(cur, Pn)
        for i, t in enumerate(cur):
            if t != hist[i][-1]:
                hist[i].append(t)
        line.append((name, "pool", len(Pn), "invalid", ninv, "radius", r, "cost", cost))
    moved = sum(1 for h in hist if len(h) > 1)
    changes = sum(len(h) - 1 for h in hist)
    mx = max(len(h) - 1 for h in hist)
    print(p, line)
    print("   viewers who ever moved", moved, "total changes", changes, "max per viewer", mx)
    Pg = final[p].tuples()
    if len(Pg) >= len(alloc[p]):
        new, ninv, r, cost = repair(alloc[p], Pg)
        print("   one shot G: invalid", ninv, "radius", r, "cost", cost)
    else:
        print("   one shot G: capacity", len(Pg), "< audience", len(alloc[p]))
    rng = random.Random(99)
    if len(Pg) >= audience[p]:
        ant = rng.sample(Pg, audience[p])
        bad = sum(1 for t in ant if t not in set(Pg))
        print("   anticipated allocation inside final pool: capacity", len(Pg), "audience", audience[p], "moves", 0)
    else:
        print("   anticipated allocation impossible: invariant capacity", len(Pg), "< audience", audience[p])

print("== F. booking before premiere")
for p in "AB":
    Pa = steps[0][1](base[p]).tuples()
    new, ninv, r, cost = repair(alloc[p], Pa)
    print(p, "booked assignments invalidated by alpha_a before premiere", ninv, "radius", r, "cost", cost,
          "visible changes to viewers 0 (nothing has been shown); deferred assignment moves 0")
