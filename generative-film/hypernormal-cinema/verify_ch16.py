#!/usr/bin/env python3
"""Reproduces every count in Chapter 16 (generation under constraint) on the lawn scene."""
import random, itertools, statistics
from math import prod
from lawnmodel import *

def final(p): return alpha(State(p), {"a", "b", "c"}, {1, 2, 3, 4, 5})
pools = {(p, w): (State(p) if w == "premiere" else final(p)) for p in "ABC" for w in ("premiere", "after G")}

print("== A. rejection from the class product")
for (p, w), st in pools.items():
    full = prod(len(c) for c in st.cl)
    cap = st.capacity()
    print(p, w, "admissible", cap, "product", full, "acceptance %.4f" % (cap / full), "expected draws per accepted %.1f" % (full / cap))
    
print("== B. left-to-right sampling without lookahead (uniform among locally compatible classes)")
def forward_dist(st):
    lv = [st.live(j) for j in range(m)]
    dist = {}
    dead = 0.0
    def rec(j, prev, pr, acc):
        nonlocal dead
        if j == m:
            dist[tuple(acc)] = dist.get(tuple(acc), 0) + pr; return
        opts = [k for k in lv[j] if prev is None or compat(st.cl[j - 1][prev]["dir"], st.cl[j][k]["dir"])]
        if not opts:
            dead += pr; return
        for k in opts:
            rec(j + 1, k, pr / len(opts), acc + [k])
    rec(0, None, 1.0, [])
    return dist, dead
for (p, w), st in pools.items():
    dist, dead = forward_dist(st)
    T = st.tuples(); n = len(T)
    ok = 1 - dead
    # conditioned on not dead-ending
    tv = 0.5 * sum(abs(dist.get(t, 0) / ok - 1 / n) for t in T)
    mx = max(dist.values()) / ok * n
    print(p, w, "dead-end probability %.4f" % dead, "TV distance from uniform (given success) %.4f" % tv,
          "most over-sampled tuple at %.2f times uniform" % mx, "tuples never produced", sum(1 for t in T if dist.get(t, 0) == 0))

print("== C. table work to rebuild an exact sampler after a correction")
for p in "AB":
    for w in ("premiere", "after G"):
        st = pools[(p, w)]
        lv = [st.live(j) for j in range(m)]
        ops = sum(len(lv[j]) * len(lv[j + 1]) for j in range(m - 1))
        print(p, w, "live classes per slot", [len(x) for x in lv], "compatibility checks", ops)

print("== D. draws needed to fill an audience with distinct editions")
for p in "AB":
    K = final(p).capacity(); U = audience[p]
    cc = sum(K / (K - i) for i in range(U))
    full = prod(len(c) for c in State(p).cl)
    print(p, "K", K, "U", U, "expected exact-sampler draws %.1f" % cc, "expected rejection-sampler proposals %.0f" % (cc * full / K))

print("== E. random greedy packing by a generator that proposes and rejects")
def greedy_pack(T, eps, rng):
    order = T[:]; rng.shuffle(order)
    chosen = []
    for t in order:
        if all(hamming(t, c) > eps for c in chosen):
            chosen.append(t)
    return len(chosen)
rng = random.Random(16)
opt = {("A", 1): 54, ("A", 2): 16, ("B", 1): 32, ("B", 2): 12}
for p in "AB":
    T = final(p).tuples()
    for eps in (1, 2):
        sizes = [greedy_pack(T, eps, rng) for _ in range(500)]
        print(p, "eps", eps, "optimum", opt[(p, eps)], "random greedy mean %.1f" % statistics.mean(sizes), "min", min(sizes), "max", max(sizes),
              "reaches optimum in %d of 500" % sum(1 for s in sizes if s == opt[(p, eps)]))

print("== F. nested commands")
def restrict(st, j, allowed):
    s = st.copy()
    s.dom[j] = {k for k in s.dom[j] if allowed(s.cl[j][k])}
    return s
for p in "AB":
    st = final(p)
    steps = [("scene: no R at any slot", lambda s: _noR(s))]
    def _noR(s):
        s = s.copy()
        for j in range(m):
            s.dom[j] = {k for k in s.dom[j] if s.cl[j][k]["dir"] != "R"}
        return s
    s0 = st
    s1 = _noR(s0)
    s2 = restrict(s1, 1, lambda c: c["dir"] != "N")      # slot 2 must move
    live1 = s2.live(0)
    s3 = s2.copy(); s3.dom[0] = {live1[0]}               # slot 1 fixed to its first live class
    live3 = s3.live(2)
    s4 = s3.copy(); s4.dom[2] = {live3[0]} if live3 else set()   # slot 3 fixed
    counts = [x.capacity() for x in (s0, s1, s2, s3, s4)]
    print(p, "pool after: none, scene command, + mid command, + shot 1 fixed, + shot 3 fixed:", counts, "audience", audience[p],
          "fits at each level:", [c >= audience[p] for c in counts])
