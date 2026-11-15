#!/usr/bin/env python3
"""Reproduces every count in Chapter 17 (three case studies)."""
import itertools, random, json, statistics
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from lawnmodel import *

# ======================================================= Study 1: the engine scene, three locales
print("== STUDY 1: engine scene, three locales, delayed recognition")
Hh = []
for t in itertools.product("TS", repeat=3):
    Hh.append(t + ("N", "none"))
    if "S" in t:
        Hh.append(t + ("Y", "honest")); Hh.append(t + ("Y", "concealed"))
def reading(h):
    t1, t2, t3, notice, rep = h
    if "S" not in (t1, t2, t3): return "diligence"
    if notice == "N": return "negligence"
    return "disclosure" if rep == "honest" else "concealment"
hstar = ("T", "T", "S", "Y", "concealed")
A_all = lambda h: True
slots = [[("wide-1", A_all), ("wide-2", A_all)]]
s2 = [("bench", A_all)]
for i in range(3):
    s2.append((f"close{i+1}-tight", lambda h, i=i: h[i] == "T"))
    s2.append((f"close{i+1}-loose", lambda h, i=i: h[i] == "S"))
slots.append(s2)
slots.append([("glance-yes", lambda h: h[3] == "Y"), ("glance-no", lambda h: h[3] == "N"), ("cutaway-3", A_all)])
slots.append([("handoff-clean", lambda h: h[4] in ("none", "concealed")), ("handoff-honest", lambda h: h[4] == "honest"), ("cutaway-4", A_all)])
def committed(tup, sl=None):
    sl = sl or slots
    return frozenset(h for h in Hh if all(sl[j][tup[j]][1](h) for j in range(4)))
eds = list(itertools.product(*[range(len(s)) for s in slots]))
faithful = [e for e in eds if hstar in committed(e)]
R = lambda K: frozenset(reading(h) for h in K)
print("class tuples", len(eds), "faithful", len(faithful))
# local trace at slots 2 and 4 (indices 1 and 3): global class = (locale, tuple); cross distance >= 2
loc = ["L1", "L2", "L3"]
rng = random.Random(17)
U = 30
alloc = {l: rng.sample(faithful, U) for l in loc}
print("per locale faithful", len(faithful), "audience", U, "total", U * 3, "total faithful global classes", 3 * len(faithful), "fits")
big = 40
print("audience of", big, "per locale needs", big * 3, "of", 3 * len(faithful), "->", "does not fit" if big > len(faithful) else "fits")
open_dist = {1: 0, 2: 0, 3: 0, 4: 0}
for l in loc:
    for e in alloc[l]:
        open_dist[len(R(committed(e)))] += 1
print("viewers by readings left open at first viewing (all three locales):", open_dist)
later = frozenset(h for h in Hh if h[3] == "Y" and h[4] == "concealed")
settled_before = open_dist[1]
changed = sum(1 for l in loc for e in alloc[l] if len(R(committed(e) & later)) < len(R(committed(e))))
print("viewers settled at first viewing", settled_before, "of 90; viewers whose reading set narrows when the reveal film arrives", changed,
      "; after the reveal all 90 have reading set", {frozenset(R(committed(e) & later)) == frozenset({"concealment"}) for l in loc for e in alloc[l]})
# wrong removal of close3-loose
k3 = [k for k, (n, f) in enumerate(slots[1]) if n == "close3-loose"][0]
valid = [e for e in faithful if e[1] != k3]
print("faithful editions after wrongly removing close3-loose", len(valid), "of", len(faithful))
recov = lambda es: sum(1 for e in es if all(reading(h) == "concealment" for h in committed(e)) and committed(e))
print("editions recoverable as concealment: before", recov(faithful), "after", recov(valid))
tot_inv = tot_free = tot_unplaced = 0
for l in loc:
    held = set(alloc[l])
    inv = [e for e in alloc[l] if e[1] == k3]
    free = [e for e in valid if e not in held]
    placed = min(len(inv), len(free))
    tot_inv += len(inv); tot_free += len(free); tot_unplaced += len(inv) - placed
    print(l, "viewers invalidated", len(inv), "free valid editions", len(free), "viewers who cannot be re-placed", len(inv) - placed,
          "audience", U, "valid pool", len(valid), "shortfall", max(0, U - len(valid)))
print("totals: invalidated", tot_inv, "free", tot_free, "unplaced", tot_unplaced)

# ======================================================= Study 2: lawn plus dishwashing scene, full ledger
print("\n== STUDY 2: lawn and dishwashing scene, one correction through a ledger")
# dishwashing scene (constructed here): 4 slots, classes per slot [3,3,2,3], two takes each, slot 3 class 1 is stale
dish_cl = [3, 3, 2, 3]
dish_stale = {(2, 1)}
dishP = [t for t in itertools.product(*[range(c) for c in dish_cl])]
dishG = [t for t in dishP if not any((j, t[j]) in dish_stale for j in range(4))]
lawnP = State("A").tuples()
lawnG = alpha(State("A"), {"a", "b", "c"}, {1, 2, 3, 4, 5}).tuples()
print("dish scene", len(dishP), "->", len(dishG), "; lawn", len(lawnP), "->", len(lawnG),
      "; film", len(lawnP) * len(dishP), "->", len(lawnG) * len(dishG))
nlawn_take = State("A").take_tuples(); nlawn_takeG = alpha(State("A"), {"a", "b", "c"}, {1, 2, 3, 4, 5}).take_tuples()
print("take tuples: lawn", nlawn_take, "->", nlawn_takeG, "dish", len(dishP) * 2 ** 4, "->", len(dishG) * 2 ** 4,
      "film", nlawn_take * len(dishP) * 16, "->", nlawn_takeG * len(dishG) * 16)
N = 500
rng = random.Random(1700)
film = [(a, b) for a in lawnP for b in dishP]
alloc = rng.sample(film, N)
ham = lambda x, y: sum(1 for p, q in zip(x[0] + x[1], y[0] + y[1]) if p != q)
def repair(alloc, pool):
    pset = set(pool)
    held = {t for t in alloc if t in pset}
    inv = [i for i, t in enumerate(alloc) if t not in pset]
    free = [t for t in pool if t not in held]
    A_ = np.array([a[0] + a[1] for a in (alloc[i] for i in inv)]); F_ = np.array([f[0] + f[1] for f in free])
    C = (A_[:, None, :] != F_[None, :, :]).sum(axis=2)
    r, c = linear_sum_assignment(C)
    new = list(alloc)
    for a, b in zip(r, c): new[inv[a]] = free[b]
    d = C[r, c]
    return new, len(inv), int(d.max()), int(d.sum())
lset = set(lawnG); dset = set(dishG)
poolL = [(a, b) for a in lawnG for b in dishP]
poolLD = [(a, b) for a in lawnG for b in dishG]
inv_l = sum(1 for t in alloc if t[0] not in lset); inv_d = sum(1 for t in alloc if t[1] not in dset)
inv_any = sum(1 for t in alloc if t[0] not in lset or t[1] not in dset)
print("viewers", N, "invalid under lawn rule", inv_l, "under dish rule", inv_d, "under both", inv_any)
a1, n1, r1, c1 = repair(alloc, poolL)
a2, n2, r2, c2 = repair(a1, poolLD)
print("sequential: lawn correction moves", n1, "(radius", r1, "cost", c1, ") then dish correction moves", n2, "(radius", r2, "cost", c2, ")")
moved = sum(1 for x, y in zip(alloc, a2) if x != y); changes = n1 + n2
twice = sum(1 for x, y, z in zip(alloc, a1, a2) if x != y and y != z)
print("viewers ever moved", moved, "total records added", changes, "moved twice", twice, "ledger records", N + changes)
a3, n3, r3, c3 = repair(alloc, poolLD)
print("joint one shot: moves", n3, "radius", r3, "cost", c3)
# stale takes referenced
rngt = random.Random(5)
def takes_of(t):
    lt = tuple(rngt.randrange(State("A").cl[j][t[0][j]]["mu"]) for j in range(5)); dt = tuple(rngt.randrange(2) for _ in range(4))
    return lt, dt
tk = [takes_of(t) for t in alloc]
Sa = State("A")
stale_l = {(j, t[0][j], tk[i][0][j]) for i, t in enumerate(alloc) for j in range(5) if Sa.cl[j][t[0][j]]["stale"]}
stale_d = {(j, t[1][j], tk[i][1][j]) for i, t in enumerate(alloc) for j in range(4) if (j, t[1][j]) in dish_stale}
print("stale lawn takes named by the ledger", len(stale_l), "of 12; stale dish takes", len(stale_d), "of", 2 * len(dish_stale))
inv_ids = [i for i, t in enumerate(alloc) if t[0] not in lset or t[1] not in dset]
print("viewers whose edition cannot be reconstructed if stale takes are purged", len(inv_ids))
anticip = rng.sample(poolLD, N)
print("anticipated allocation inside the final pool:", len(poolLD), "pairs for", N, "viewers: moves 0, ledger records", N)

# ======================================================= Study 3: measured passage, correction to its own record
print("\n== STUDY 3: the measured passage, correction to the dialogue reference")
d = pd.read_csv("data/seconds.csv"); oc = json.load(open("data/occupation.json"))
level = d.level_db.values; aud = d.audible.values.astype(bool); sub = d.dialogue_sub.values.astype(bool)
n = len(d); P0, P1 = 3639, 4851
def runs(mask):
    out = []; i = 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]: j += 1
            out.append((i, j + 1)); i = j + 1
        else: i += 1
    return out
def analyse(ref):
    rel = level - ref
    occ = rel > 10
    r = runs(occ); mb = []
    for a, b in r:
        if mb and a - mb[-1][1] <= 5: mb[-1] = (mb[-1][0], b)
        else: mb.append((a, b))
    blocks = [(a, b) for a, b in mb if b - a >= 60]
    low = (rel <= 0) | (~aud)
    win = [w for w in runs(low) if w[1] - w[0] >= 5]
    pw = [w for w in win if w[0] >= P0 and w[1] <= P1]
    pb = [b for b in blocks if b[0] >= P0 and b[1] <= P1]
    return dict(blocks=len(blocks), block_s=sum(b - a for a, b in blocks), windows=len(win), win_s=sum(b - a for a, b in win),
                slack=sum(b - a - 5 for a, b in win), pwin=[b - a for a, b in pw], pslack=sum(b - a - 5 for a, b in pw), pblocks=len(pb))
ref0 = float(np.median(level[sub]))
print("reference (median level over", int(sub.sum()), "subtitle-defined seconds)", round(ref0, 3), "recorded", round(oc["dialogue_reference"], 3))
base = analyse(ref0)
print("recorded:", base)
assert base["blocks"] == 9 and base["windows"] == 105 and base["win_s"] == 1526
print("-- shifted by a uniform offset in dB")
for dB in (-2.33, -1.0, -0.44, 0.44, 1.0, 2.33):
    r = analyse(ref0 + dB)
    print("reference shift %+.2f dB" % dB, {k: r[k] for k in ("blocks", "block_s", "windows", "win_s", "pwin", "pslack", "pblocks")})
print("-- subtitle offset error: dialogue seconds shifted by k seconds, reference recomputed")
for k in (-3, -1, 1, 3, 10):
    sh = np.roll(sub, k)
    ref = float(np.median(level[sh]))
    r = analyse(ref)
    print("offset %+d s" % k, "reference %.3f (shift %+.3f dB)" % (ref, ref - ref0),
          {kk: r[kk] for kk in ("blocks", "block_s", "windows", "win_s", "pwin", "pslack", "pblocks")})
proxy = analyse(oc["dialogue_reference_proxy"])
print("proxy reference %.3f (shift %+.3f dB)" % (oc["dialogue_reference_proxy"], oc["dialogue_reference_proxy"] - ref0),
      {kk: proxy[kk] for kk in ("blocks", "block_s", "windows", "win_s", "pwin", "pslack", "pblocks")})
cen = analyse(oc["dialogue_center_dbfs"])
print("centre-channel reference %.3f (shift %+.3f dB)" % (oc["dialogue_center_dbfs"], oc["dialogue_center_dbfs"] - ref0),
      {kk: cen[kk] for kk in ("blocks", "block_s", "windows", "win_s", "pwin", "pslack", "pblocks")})
