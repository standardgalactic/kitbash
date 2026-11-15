#!/usr/bin/env python3
"""Reproduces every count in Chapter 7 (reports and adjudication)."""
import random
from collections import Counter, defaultdict
from lawnmodel import *

times = {1: 0, 2: 1, 3: 2, 4: 2, 5: 3}
vis = {1: "abc", 2: "a", 3: "ab", 4: "c", 5: "abc"}
event_time = {"a": 1, "b": 2, "c": 3}

def required(j, s):
    return "mown" if times[j] >= event_time[s] else "unmown"

def displayed(prod, j, k, s):
    """appearance of strip s at slot j shown by class k of the production"""
    c = classes(prod)[j - 1][k]
    r = required(j, s)
    if c["stale"] and c["wrong"] == s:
        return "unmown" if r == "mown" else "mown"
    return r

base = {p: State(p) for p in "ABC"}
Gp = {p: alpha(base[p], {"a", "b", "c"}, {1, 2, 3, 4, 5}) for p in "ABC"}

def draw_with_takes(p, seed=None):
    P = base[p].tuples()
    rng = random.Random(2026 + ord(p) if seed is None else seed)
    alloc = rng.sample(P, audience[p])      # same draw as Chapter 10
    rng2 = random.Random(7000 + ord(p))
    out = []
    for t in alloc:
        takes = tuple(rng2.randrange(base[p].cl[j][t[j]]["mu"]) for j in range(m))
        out.append((t, takes))
    return out

def verdict(prod, rules_Gset, assigned_class, claim):
    """claim = (slot, strip, appearance). Returns (outcome, kind)"""
    j, s, ap = claim
    shown = displayed(prod, j, assigned_class[j - 1], s)
    if ap != shown:
        return "unsupported", None
    if shown == required(j, s):
        return "rejected", None
    # upheld: is the assigned class admissible under the rules in force at assignment
    admissible_under_rules = rules_Gset  # True if G was in force, so stale classes were excluded
    cl = classes(prod)[j - 1][assigned_class[j - 1]]
    if admissible_under_rules and cl["stale"]:
        return "upheld", "violation"
    return "upheld", "amendment"

print("== all possible claims about every showing, under R0 and under R1 ==")
for p in "ABC":
    aud = draw_with_takes(p)
    for inforce, label in [(False, "R0 in force"), (True, "R1 in force (assembly fault)")]:
        cnt = Counter()
        for t, takes in aud:
            for j in range(1, m + 1):
                for s in vis[j]:
                    for ap in ("mown", "unmown"):
                        out = verdict(p, inforce, t, (j, s, ap))
                        cnt[out] += 1
        print(p, label, dict(cnt))

print("\n== who can file what: viewers holding a stale class, and which stale classes the audience holds ==")
stale_all = {}
for p in "ABC":
    cl = classes(p)
    stale_all[p] = {(j + 1, k) for j in range(m) for k, c in enumerate(cl[j]) if c["stale"]}
for p in "ABC":
    aud = draw_with_takes(p)
    holders = defaultdict(list)
    for i, (t, takes) in enumerate(aud):
        for j in range(m):
            if (j + 1, t[j]) in stale_all[p]:
                holders[(j + 1, t[j])].append(i)
    viewers = {i for v in holders.values() for i in v}
    print(p, "stale classes in pool", len(stale_all[p]), "held by audience", len(holders), "viewers holding a stale class", len(viewers),
          "viewers per held class", sorted(len(v) for v in holders.values()))
    # entity interval pairs
    pairs_pool = set(); pairs_held = set()
    for (j, k) in stale_all[p]:
        c = classes(p)[j - 1][k]; s = c["wrong"]
        pairs_pool.add((s, "post" if times[j] >= event_time[s] else "pre"))
    for (j, k) in holders:
        c = classes(p)[j - 1][k]; s = c["wrong"]
        pairs_held.add((s, "post" if times[j] >= event_time[s] else "pre"))
    print("   (strip, interval) pairs in pool", sorted(pairs_pool), "revealed by audience", sorted(pairs_held))

print("\n== assigned versus played: stale cache after a repair ==")
import numpy as np
from scipy.optimize import linear_sum_assignment
for p in "AB":
    aud = draw_with_takes(p)
    Pn = Gp[p].tuples(); Pset = set(Pn)
    alloc = [t for t, _ in aud]
    held = {t for t in alloc if t in Pset}
    inval_idx = [i for i, t in enumerate(alloc) if t not in Pset]
    free = [t for t in Pn if t not in held]
    C = np.array([[hamming(alloc[i], q) for q in free] for i in inval_idx], float)
    r_, c_ = linear_sum_assignment(C)
    rev2 = list(alloc)
    for a_, b_ in zip(r_, c_):
        rev2[inval_idx[a_]] = free[b_]
    misjudged = 0; right_by_played = 0
    for i in inval_idx:
        t1 = alloc[i]
        # the viewer saw a stale class under revision 1: pick one stale showing
        for j in range(m):
            if (j + 1, t1[j]) in stale_all[p]:
                c = classes(p)[j][t1[j]]
                s = c["wrong"]
                claim = (j + 1, s, displayed(p, j + 1, t1[j], s))
                break
        against_assigned = verdict(p, True, rev2[i], claim)
        against_played = verdict(p, False, t1, claim)
        misjudged += (against_assigned[0] == "unsupported")
        right_by_played += (against_played[0] == "upheld")
    print(p, "invalid viewers repaired", len(inval_idx), "truthful claims judged unsupported against the assigned revision", misjudged,
          "upheld against the played revision", right_by_played)

print("\n== retention: takes needed to adjudicate the premiere assignments ==")
for p in "ABC":
    aud = draw_with_takes(p)
    used = {(j, t[j], takes[j]) for t, takes in aud for j in range(m)}
    pool_takes = sum(len(base[p].cl[j]) * base[p].cl[j][0]["mu"] if False else sum(c["mu"] for c in base[p].cl[j]) for j in range(m))
    withdrawn = sum(1 for t, takes in aud if any(takes[j] == 0 for j in range(m)))
    wd_slots = sum(1 for t, takes in aud for j in range(m) if takes[j] == 0)
    print(p, "distinct takes assigned", len(used), "of", pool_takes, "in pool;",
          "viewers with at least one take of variant 0 (withdrawn by omega)", withdrawn, "of", len(aud), "assigned take slots affected", wd_slots, "of", len(aud) * m)
