#!/usr/bin/env python3
"""Reproduces every count in Chapter 13 (the lifetime repertoire)."""
import random, math, time
from math import gcd
from lawnmodel import *

FILM_S = 5222            # measured length of the passage film of Chapter 6, seconds
H = FILM_S / 3600
print("film length hours %.4f" % H)

print("== A. viewing budget (60 years of viewing)")
for hw in (2, 6, 14):
    L = hw * 52 * 60
    N = int(L // H)
    print("hours/week", hw, "lifetime hours", L, "viewings N", N, "per year %.1f" % (N / 60))

print("== B. novelty horizon, production A and B after the agreement rule (packing numbers from Chapter 2)")
M = {"A": {0: 238, 1: 54, 2: 16}, "B": {0: 96, 1: 32, 2: 12}}
for hw in (2,):
    N = int((hw * 52 * 60) // H); per_week = hw / H
    for p in "AB":
        for e in (0, 1, 2):
            Me = M[p][e]
            weeks = Me / (per_week)  # weeks to exhaust at hw hours/week
            prods = math.ceil(N / Me)
            newfilms_year = (N / 60) / Me
            print(p, "eps", e, "M", Me, "viewings/week %.2f" % per_week, "weeks to exhaust one production %.1f" % weeks,
                  "productions for a life with no perceptual repeat", prods, "films per year %.2f" % newfilms_year,
                  "versus films if never revisited", N)

print("== C. counting and unranking without enumeration")
def dp_tables(st):
    lv = [st.live(j) for j in range(m)]
    suf = [dict() for _ in range(m)]
    for k in lv[m - 1]:
        suf[m - 1][k] = 1
    for j in range(m - 2, -1, -1):
        for k in lv[j]:
            suf[j][k] = sum(suf[j + 1][k2] for k2 in lv[j + 1] if compat(st.cl[j][k]["dir"], st.cl[j + 1][k2]["dir"]))
    return lv, suf

def unrank(st, lv, suf, r):
    out = []; prev = None
    for j in range(m):
        for k in lv[j]:
            if prev is not None and not compat(st.cl[j - 1][prev]["dir"], st.cl[j][k]["dir"]):
                continue
            c = suf[j][k]
            if r < c:
                out.append(k); prev = k; break
            r -= c
    return tuple(out)

for p in "ABC":
    for name, st in (("premiere", base_state := State(p)), ("after G", alpha(State(p), {"a", "b", "c"}, {1, 2, 3, 4, 5}))):
        lv, suf = dp_tables(st)
        total = sum(suf[0].values())
        T = st.tuples()
        ok = total == len(T) and all(unrank(st, lv, suf, r) == T[r] for r in range(total))
        print(p, name, "dp count", total, "enumerated", len(T), "unrank equals r-th tuple for all r:", ok)

def synth(mm, q, dens, seed):
    rng = random.Random(seed)
    allow = [[[rng.random() < dens for _ in range(q)] for _ in range(q)] for _ in range(mm - 1)]
    suf = [[0] * q for _ in range(mm)]
    suf[mm - 1] = [1] * q
    for j in range(mm - 2, -1, -1):
        for a in range(q):
            suf[j][a] = sum(suf[j + 1][b] for b in range(q) if allow[j][a][b])
    return allow, suf

def synth_unrank(allow, suf, r, mm, q):
    out = []; prev = None
    for j in range(mm):
        for a in range(q):
            if prev is not None and not allow[j - 1][prev][a]:
                continue
            c = suf[j][a]
            if r < c:
                out.append(a); prev = a; break
            r -= c
    return out

for mm, q in ((40, 10), (1000, 20)):
    t0 = time.time()
    allow, suf = synth(mm, q, 0.7, 5)
    total = sum(suf[0])
    rng = random.Random(1)
    rs = [rng.randrange(total) for _ in range(20)]
    tuples = [synth_unrank(allow, suf, r, mm, q) for r in rs]
    valid = all(all(allow[j][t[j]][t[j + 1]] for j in range(mm - 1)) for t in tuples)
    distinct = len({tuple(t) for t in tuples}) == len(tuples)
    print("synthetic m", mm, "q", q, "count has", len(str(total)), "digits, log10 %.1f" % (len(str(total)) - 1),
          "20 unranked valid", valid, "distinct", distinct, "seconds %.2f" % (time.time() - t0))

print("== D. cyclic schedule over the corrected pool")
for p in "AB":
    st = alpha(State(p), {"a", "b", "c"}, {1, 2, 3, 4, 5})
    T = st.tuples(); K = len(T); U = audience[p]
    s = 1
    a = list(range(U))
    rounds_ok = all(len({(a[v] + k * s) % K for v in range(U)}) == U for k in range(K))
    norepeat = all(len({(a[v] + k * s) % K for k in range(K)}) == K for v in range(U))
    def consec(s):
        ds = [hamming(T[i], T[(i + s) % K]) for i in range(K)]
        return sum(ds) / K, min(ds)
    best = max((s2 for s2 in range(1, K) if gcd(s2, K) == 1), key=lambda s2: (consec(s2)[1], consec(s2)[0]))
    print(p, "K", K, "U", U, "distinct in every round", rounds_ok, "no repeat in K rounds", norepeat,
          "stride 1 mean/min consecutive Hamming %.2f / %d" % consec(1),
          "best stride", best, "mean/min %.2f / %d" % consec(best))

print("== E. lifetime ledger size per viewer, compact encoding")
for p, bits in (("A", 17), ("B", 14), ("C", 28)):
    for hw in (2, 14):
        N = int((hw * 52 * 60) // H)
        print(p, hw, "h/week N", N, "bits", N * bits, "bytes", N * bits // 8)

print("== F. simultaneous audience at tolerance after G")
for p in "AB":
    U = audience[p]
    print(p, "audience", U, [(e, M[p][e], "fits" if M[p][e] >= U else "does not fit") for e in (0, 1, 2)])
