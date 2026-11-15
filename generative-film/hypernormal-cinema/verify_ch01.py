#!/usr/bin/env python3
"""Reproduces every count used in Chapter 1 of the monograph.

Run with:  python3 -I verify_ch01.py
"""
import itertools
import random
from decimal import Decimal, getcontext
from fractions import Fraction

import numpy as np
from scipy.optimize import linear_sum_assignment

# ---------------------------------------------------------------- bit count
frames = 90 * 60 * 24
pixels = 1920 * 1080
bits_pixel = 24
bits_frame = pixels * bits_pixel
N_bits = frames * bits_frame
assert frames == 129_600
assert pixels == 2_073_600
assert bits_frame == 49_766_400
assert N_bits == 6_449_725_440_000
getcontext().prec = 60
digits = int((Decimal(N_bits) * Decimal(2).ln() / Decimal(10).ln()).to_integral_value(rounding="ROUND_FLOOR")) + 1
print("bits per film:", f"{N_bits:,}")
print("decimal digits of 2^N:", f"{digits:,}")
log10_total = Decimal(N_bits) * Decimal(2).log10()
print("log10(2^N) =", log10_total)

# one second, one frame, tiny cases used in the text
print("2^8 =", 2**8)

# ------------------------------------------------------ hash and audience
n_view = 10**9
expected_pairs = Fraction(n_view * (n_view - 1), 2 * 2**64)
print("expected colliding pairs, 64-bit keys, 10^9 viewers:", float(expected_pairs))
print("2^30 =", 2**30, " 2^33 =", 2**33)

# ------------------------------------------------------- lifetime budget
hours = 2 * 52 * 60
films_once = hours / 1.5
print("viewing hours:", hours, " films once:", films_once)
for r in (0, 0.5, 1, 2):
    print("mean revisits", r, "-> distinct films", hours / (1.5 * (1 + r)))

# ------------------------------------------------------------ mowing model
# strips a,b,c ; script history p_a p_b p_c
strips = ["a", "b", "c"]
script = ["a", "b", "c"]
# slots: (time t_j = number of passes completed, visible strips)
slots = [(0, ("a", "b", "c")), (1, ("a",)), (2, ("a", "b")), (2, ("c",)), (3, ("a", "b", "c"))]
m = len(slots)


def required(j):
    t, V = slots[j]
    done = set(script[:t])
    return {s: (s in done) for s in V}


for j in range(m):
    print("slot", j + 1, "t =", slots[j][0], "required", required(j))

# pool entries: (direction, status, number of classes q, byte variants per class mu)
pools = {
    "A": [
        [("L", "ok", 2, 3), ("R", "ok", 2, 3), ("N", "ok", 1, 3)],
        [("L", "ok", 2, 3), ("R", "ok", 1, 3), ("N", "ok", 1, 3), ("L", "stale", 1, 3)],
        [("L", "ok", 1, 3), ("R", "ok", 2, 3), ("R", "stale", 1, 3)],
        [("N", "ok", 2, 3), ("L", "ok", 1, 3), ("R", "stale", 1, 3)],
        [("L", "ok", 1, 3), ("R", "ok", 2, 3), ("N", "ok", 1, 3), ("L", "stale", 1, 3)],
    ],
    "B": [
        [("L", "ok", 2, 2), ("R", "ok", 3, 2)],
        [("L", "ok", 2, 2), ("R", "ok", 2, 2), ("R", "stale", 2, 2)],
        [("L", "ok", 3, 2), ("R", "ok", 2, 2), ("L", "stale", 2, 2)],
        [("L", "ok", 2, 2), ("R", "ok", 2, 2)],
        [("L", "ok", 2, 2), ("R", "ok", 2, 2), ("R", "stale", 3, 2)],
    ],
    "C": [
        [("L", "ok", 1, 40), ("R", "ok", 1, 40)],
        [("L", "ok", 1, 40), ("L", "stale", 1, 40)],
        [("L", "ok", 1, 40), ("R", "ok", 1, 40)],
        [("L", "ok", 1, 40), ("R", "ok", 1, 40)],
        [("L", "ok", 1, 40), ("R", "stale", 1, 40)],
    ],
}


def classes(prod):
    """list per slot of (direction, status, byte_variants)"""
    out = []
    for slot_entries in pools[prod]:
        cl = []
        for (d, st, q, mu) in slot_entries:
            for _ in range(q):
                cl.append((d, st, mu))
        out.append(cl)
    return out


def compat(d1, d2):
    return d1 == d2 or d1 == "N" or d2 == "N"


def admissible_paths(prod, with_grass):
    cl = classes(prod)
    pools_ = []
    for j in range(m):
        idx = [k for k, c in enumerate(cl[j]) if (not with_grass or c[1] == "ok")]
        pools_.append(idx)
    paths = []
    for p in itertools.product(*pools_):
        if all(compat(cl[j][p[j]][0], cl[j + 1][p[j + 1]][0]) for j in range(m - 1)):
            paths.append(p)
    return paths, cl


def count_dp(prod, with_grass, weighted):
    cl = classes(prod)
    vec = None
    for j in range(m):
        idx = [k for k, c in enumerate(cl[j]) if (not with_grass or c[1] == "ok")]
        w = {k: (cl[j][k][2] if weighted else 1) for k in idx}
        if vec is None:
            vec = dict(w)
        else:
            new = {}
            for k in idx:
                s = sum(v for kk, v in vec.items() if compat(cl[j - 1][kk][0], cl[j][k][0]))
                new[k] = s * w[k]
            vec = new
    return sum(vec.values())


results = {}
for prod in "ABC":
    cl = classes(prod)
    sizes = [len(c) for c in cl]
    ok_sizes = [sum(1 for x in c if x[1] == "ok") for c in cl]
    P0, _ = admissible_paths(prod, False)
    P1, _ = admissible_paths(prod, True)
    assert len(P0) == count_dp(prod, False, False)
    assert len(P1) == count_dp(prod, True, False)
    B0 = count_dp(prod, False, True)
    B1 = count_dp(prod, True, True)
    # brute force take tuples
    assert B0 == sum(np.prod([cl[j][p[j]][2] for j in range(m)]) for p in P0)
    assert B1 == sum(np.prod([cl[j][p[j]][2] for j in range(m)]) for p in P1)
    results[prod] = (P0, P1, cl)
    print(f"production {prod}: classes per slot {sizes}, ok classes {ok_sizes}")
    print(f"   perceptual editions before {len(P0)}, after {len(P1)}, removed {len(P0)-len(P1)}")
    print(f"   take tuples before {B0:,}, after {B1:,}")

# naive pool sizes without adjacency, to show effect of adjacency rule alone
for prod in "ABC":
    cl = classes(prod)
    prod_all = 1
    prod_ok = 1
    for c in cl:
        prod_all *= len(c)
        prod_ok *= sum(1 for x in c if x[1] == "ok")
    print(prod, "unconstrained class tuples:", prod_all, " with grass rule only:", prod_ok)

# footprint of the strip rules
for s in strips:
    k = script.index(s) + 1
    fp = [j + 1 for j, (t, V) in enumerate(slots) if s in V]
    late = [j + 1 for j, (t, V) in enumerate(slots) if s in V and t >= k]
    print("strip", s, "cut time", k, "footprint slots", fp, "late slots", late)

# ---------------------------------------------- containment lemma check (A)
P0, P1, cl = results["A"]
Pset = set(P0)
viol = 0
checked = 0
for p in P0:
    for a in range(m):
        for b in range(a + 2, m):
            if cl[a][p[a]][0] == "N" and cl[b][p[b]][0] == "N":
                inner = [range(len(cl[j])) for j in range(a + 1, b)]
                for q in itertools.product(*inner):
                    cand = list(p)
                    cand[a + 1:b] = list(q)
                    ok_inside = all(compat(cl[j][cand[j]][0], cl[j + 1][cand[j + 1]][0]) for j in range(a, b))
                    if ok_inside:
                        checked += 1
                        if tuple(cand) not in Pset:
                            viol += 1
print("containment lemma: checked", checked, "violations", viol)

# ---------------------------------------------------------- audience model
audience = {"A": 60, "B": 30, "C": 2}


def hamming(p, q):
    return sum(1 for x, y in zip(p, q) if x != y)


for prod in "ABC":
    P0, P1, cl = results[prod]
    U = audience[prod]
    if U > len(P1):
        print(f"audience {prod}: U={U} exceeds {len(P1)} perceptual editions after the amendment: uniqueness cannot be kept")
        continue
    rng = random.Random(2026 + ord(prod))
    chosen = rng.sample(range(len(P0)), U)  # stands in for a keyed permutation
    assign = {u: P0[i] for u, i in enumerate(chosen)}
    S1 = set(P1)
    invalid = [u for u, p in assign.items() if p not in S1]
    valid = [u for u in assign if u not in invalid]
    occupied = {assign[u] for u in valid}
    # naive repair: nearest admissible edition, ties lexicographic
    naive = {}
    for u in invalid:
        best = min(P1, key=lambda q: (hamming(assign[u], q), q))
        naive[u] = best
    final_naive = {u: (naive[u] if u in naive else assign[u]) for u in assign}
    from collections import Counter
    cnt = Counter(final_naive.values())
    colliding_viewers = sum(1 for u, p in final_naive.items() if cnt[p] > 1)
    slots_naive = sum(hamming(assign[u], naive[u]) for u in invalid)
    # matched repair: min total Hamming distance to unoccupied admissible editions
    free = [q for q in P1 if q not in occupied]
    cost = np.array([[hamming(assign[u], q) for q in free] for u in invalid])
    if invalid:
        r, c = linear_sum_assignment(cost)
        slots_match = int(cost[r, c].sum())
        moved_far = int(max(cost[r, c]))
        assert len({free[j] for j in c}) == len(invalid)
    else:
        slots_match = 0
        moved_far = 0
    # greedy first-come repair (process in viewer order, take nearest free)
    taken = set(occupied)
    slots_greedy = 0
    greedy_fail = 0
    for u in invalid:
        cands = sorted((q for q in P1 if q not in taken), key=lambda q: (hamming(assign[u], q), q))
        if not cands:
            greedy_fail += 1
            continue
        taken.add(cands[0])
        slots_greedy += hamming(assign[u], cands[0])
    print(f"audience {prod}: U={U}, editions before {len(P0)}, after {len(P1)}")
    print(f"   viewers with invalid edition: {len(invalid)}; occupied by valid viewers: {len(occupied)}")
    print(f"   naive nearest repair: viewers sharing an edition {colliding_viewers}, slots changed {slots_naive}")
    print(f"   greedy distinct repair: slots changed {slots_greedy}, failures {greedy_fail}")
    print(f"   matched repair: slots changed {slots_match}, max slots changed for one viewer {moved_far}")

# Hall example
C1 = {"x", "y"}
C2 = {"x"}
print("Hall example: greedy assigns u1->x leaving u2 empty; matching u1->y,u2->x exists")

# packing versus classes (toy): four versions on a line at spacing 0.6 with eps = 0.5 and 1.0
pts = [0.0, 0.6, 1.2, 1.8]
eps = 1.0
best = 0
for r_ in range(len(pts) + 1):
    for sub in itertools.combinations(range(len(pts)), r_):
        if all(abs(pts[i] - pts[j]) > eps for i, j in itertools.combinations(sub, 2)):
            best = max(best, r_)
print("packing example: 4 exact classes, eps =", eps, "max separated subset", best)


# ----------------------------------------------------------- robustness
print("robustness to {R1}:", {prod: (len(results[prod][1]) >= audience[prod]) for prod in "ABC"})
print("ratios take tuples / perceptual (A, B):", 120042 / 494, 10240 / 320)

# ----------------------------------------------- worldwide Hall (Prop global)
def injective_exists(sets):
    """sets: list of frozensets, one per viewer; backtracking SDR search."""
    order = sorted(range(len(sets)), key=lambda i: len(sets[i]))
    used = set()

    def go(k):
        if k == len(order):
            return True
        for g in sets[order[k]]:
            if g not in used:
                used.add(g)
                if go(k + 1):
                    return True
                used.discard(g)
        return False

    return go(0)


rng = random.Random(7)
mismatch = 0
trials = 400
feasible_count = 0
for _ in range(trials):
    n_prod = rng.randint(1, 3)
    classes_universe = list(range(rng.randint(2, 6)))
    G = {p: frozenset(rng.sample(classes_universe, rng.randint(1, len(classes_universe)))) for p in range(n_prod)}
    Uc = {p: rng.randint(0, 3) for p in range(n_prod)}
    viewers = [G[p] for p in range(n_prod) for _ in range(Uc[p])]
    brute = injective_exists(viewers)
    cond = True
    for r_ in range(1, n_prod + 1):
        for P in itertools.combinations(range(n_prod), r_):
            if len(set().union(*[G[p] for p in P])) < sum(Uc[p] for p in P):
                cond = False
    if brute != cond:
        mismatch += 1
    feasible_count += brute
    # disjoint case reduces to per-locale
print(f"Prop global: {trials} random instances, {feasible_count} feasible, {mismatch} disagreements with the Hall condition")

# disjoint sets reduce to per-locale inequality
mm = 0
for _ in range(400):
    n_prod = rng.randint(1, 3)
    sizes = [rng.randint(1, 3) for _ in range(n_prod)]
    start = 0
    G = {}
    for p in range(n_prod):
        G[p] = frozenset(range(start, start + sizes[p]))
        start += sizes[p]
    Uc = {p: rng.randint(0, 4) for p in range(n_prod)}
    viewers = [G[p] for p in range(n_prod) for _ in range(Uc[p])]
    if injective_exists(viewers) != all(Uc[p] <= len(G[p]) for p in range(n_prod)):
        mm += 1
print("disjoint case: disagreements with per-locale condition:", mm)

# ---------------------------------------- survivors fixed versus survivors free
# invalid viewer u accepts {x}; survivor v holds x and accepts {x, y}
F_fixed = {"y"}              # admissible classes not held by survivors would be {y} only if x is held by v
C_u = {"x"}
print("fixed survivors: candidate set for u within free classes:", C_u & {"y"}, "(empty means failure)")
broad = injective_exists([frozenset({"x"}), frozenset({"x", "y"})])
print("survivors allowed to move: assignment exists:", broad)
