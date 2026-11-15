#!/usr/bin/env python3
"""Reproduces every count in Chapter 4 (constraint structures, frontier tables, carry width, unranking).

Run with:  python3 -I verify_ch04.py
"""
import itertools
import random
from collections import defaultdict

# ------------------------------------------------------------------ lawn pools
# entries: (direction, status, number of classes q, take variants per class mu)
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
m = 5


def class_lists(prod):
    out = []
    for entries in pools[prod]:
        cl = []
        for (d, st, q, mu) in entries:
            for _ in range(q):
                cl.append({"dir": d, "stale": st == "stale", "mu": mu})
        out.append(cl)
    return out


def with_hands(cl):
    """hand label at slots 2 and 5 (indices 1 and 4): alternate l, r in listing order"""
    for j in (1, 4):
        for idx, c in enumerate(cl[j]):
            c["hand"] = "l" if idx % 2 == 0 else "r"
    return cl


def compat(d1, d2):
    return d1 == d2 or d1 == "N" or d2 == "N"


# ---------------------------------------------------- constraint structures
class Structure:
    """domains[j] = list of class ids available at slot j (ints index into attrs[j]);
    constraints = list of (scope tuple, predicate(values tuple) -> bool)."""

    def __init__(self, domains, constraints, weights=None):
        self.D = domains
        self.C = constraints
        self.m = len(domains)
        self.W = weights  # W[j][k] weight of class k at slot j (default 1)

    def w(self, j, k):
        return 1 if self.W is None else self.W[j][k]

    def frontier(self):
        """F[j] for j=0..m (0-based): slots i<j that share a scope with some slot >= j"""
        m = self.m
        edges = set()
        for scope, _ in self.C:
            for a in scope:
                for b in scope:
                    if a < b:
                        edges.add((a, b))
        F = []
        for j in range(m + 1):
            F.append(tuple(sorted({a for (a, b) in edges if a < j <= b})))
        return F


def frontier_count(S, return_tables=False):
    """Left to right frontier tables. Returns (count, operations, table sizes)."""
    F = S.frontier()
    m = S.m
    ops = 0
    T = {(): 1}  # table over assignments to F[0] = ()
    sizes = [1]
    by_max = defaultdict(list)
    for scope, pred in S.C:
        by_max[max(scope)].append((scope, pred))
    for j in range(m):
        Fj = F[j]
        Fn = F[j + 1]
        newT = defaultdict(int)
        for z, cnt in T.items():
            zmap = dict(zip(Fj, z))
            for k in S.D[j]:
                ops += 1
                zmap[j] = k
                ok = True
                for scope, pred in by_max.get(j, []):
                    if not pred(tuple(zmap[i] for i in scope)):
                        ok = False
                        break
                if ok:
                    key = tuple(zmap[i] for i in Fn)
                    newT[key] += cnt * S.w(j, k)
        T = dict(newT)
        sizes.append(len(T))
    return T.get((), 0), ops, sizes


def brute_count(S):
    tot = 0
    for tup in itertools.product(*S.D):
        if all(pred(tuple(tup[i] for i in scope)) for scope, pred in S.C):
            w = 1
            for j, k in enumerate(tup):
                w *= S.w(j, k)
            tot += w
    return tot


def lawn_structure(prod, grass, glass):
    cl = class_lists(prod)
    if glass:
        with_hands(cl)
    D = []
    for j in range(m):
        D.append([k for k, c in enumerate(cl[j]) if not (grass and c["stale"])])
    cons = []
    for j in range(m - 1):
        cons.append(((j, j + 1), (lambda a, b, j=j: compat(cl[j][a[0]]["dir"], cl[j + 1][a[1]]["dir"]) if False else None)))
    cons = []
    for j in range(m - 1):
        def pred(vals, j=j):
            return compat(cl[j][vals[0]]["dir"], cl[j + 1][vals[1]]["dir"])
        cons.append(((j, j + 1), pred))
    if glass:
        def hand_pred(vals):
            return cl[1][vals[0]]["hand"] == cl[4][vals[1]]["hand"]
        cons.append(((1, 4), hand_pred))
    W = [[c["mu"] for c in cl[j]] for j in range(m)]
    return Structure(D, cons, W), cl


# ------------------------------------------------ chain recovers Chapter 1
expected = {"A": (494, 238, 120042, 57834), "B": (320, 96, 10240, 3072), "C": (2, 1, 204800000, 102400000)}
print("== chain only: frontier tables against Chapter 1 totals ==")
for prod in "ABC":
    S0, _ = lawn_structure(prod, grass=False, glass=False)
    S1, _ = lawn_structure(prod, grass=True, glass=False)
    n0, ops0, _ = frontier_count(S0)
    n1, ops1, _ = frontier_count(S1)
    S0w = Structure(S0.D, S0.C, S0.W)
    t0, _, _ = frontier_count(S0w)
    t1, _, _ = frontier_count(Structure(S1.D, S1.C, S1.W))
    # unweighted
    u0, _, _ = frontier_count(Structure(S0.D, S0.C, None))
    u1, _, _ = frontier_count(Structure(S1.D, S1.C, None))
    print(prod, "perceptual", u0, u1, " take tuples", t0, t1, " ops", ops0, ops1)
    assert (u0, u1, t0, t1) == (expected[prod][0], expected[prod][1], expected[prod][2], expected[prod][3])
    assert u0 == brute_count(Structure(S0.D, S0.C, None))
    assert u1 == brute_count(Structure(S1.D, S1.C, None))

# ---------------------------------------------------- glass constraint
print("\n== chain plus glass constraint between slots 2 and 5 ==")
for prod in "ABC":
    cl = with_hands(class_lists(prod))
    hands = {j + 1: (sum(1 for c in cl[j] if c["hand"] == "l"), sum(1 for c in cl[j] if c["hand"] == "r")) for j in (1, 4)}
    hands_ok = {j + 1: (sum(1 for c in cl[j] if c["hand"] == "l" and not c["stale"]), sum(1 for c in cl[j] if c["hand"] == "r" and not c["stale"])) for j in (1, 4)}
    S0, _ = lawn_structure(prod, False, True)
    S1, _ = lawn_structure(prod, True, True)
    S0u = Structure(S0.D, S0.C, None)
    S1u = Structure(S1.D, S1.C, None)
    n0, ops0, sz0 = frontier_count(S0u)
    n1, ops1, sz1 = frontier_count(S1u)
    assert n0 == brute_count(S0u) and n1 == brute_count(S1u)
    tw0, _, _ = frontier_count(S0)
    tw1, _, _ = frontier_count(S1)
    assert tw0 == brute_count(S0) and tw1 == brute_count(S1)
    print(prod, "hands l/r by slot (all classes)", hands, " (non-stale)", hands_ok)
    print("   perceptual editions before/after", n0, n1, " take tuples", tw0, tw1)
    print("   frontier sets", S0.frontier(), " width", max(len(f) for f in S0.frontier()))
    print("   table updates (ops) before/after", ops0, ops1, " table sizes after", sz1)

# ------------------------------------------------ carry width by future equivalence
print("\n== carry width (future-equivalence classes of viable prefixes) ==")


def admissible_tuples(S):
    out = []
    for tup in itertools.product(*S.D):
        if all(pred(tuple(tup[i] for i in scope)) for scope, pred in S.C):
            out.append(tup)
    return out


def carry_widths(S):
    tuples = admissible_tuples(S)
    widths = []
    for j in range(S.m + 1):  # prefix length j
        groups = defaultdict(set)
        for t in tuples:
            groups[t[:j]].add(t[j:])
        classes = {frozenset(v) for v in groups.values()}
        widths.append(len(classes))
    return widths


for prod in "ABC":
    for glass in (False, True):
        S1, cl = lawn_structure(prod, True, glass)
        S1u = Structure(S1.D, S1.C, None)
        w = carry_widths(S1u)
        F = S1u.frontier()
        fsz = []
        for j in range(S1u.m + 1):
            p_ = 1
            for i in F[j]:
                p_ *= len(S1u.D[i])
            fsz.append(p_)
        print(prod, "glass" if glass else "chain", "carry widths by prefix length 0..5:", w, " frontier table sizes:", fsz)

# --------------------------------------------------------- unranking
print("\n== ranking and unranking by frontier tables ==")


def build_completion_tables(S):
    """C_j(z): number of completions of slots j..m-1 given frontier assignment z at j"""
    F = S.frontier()
    m = S.m
    by_max = defaultdict(list)
    for scope, pred in S.C:
        by_max[max(scope)].append((scope, pred))
    memo = {}

    def comp(j, z):
        if j == m:
            return 1
        key = (j, z)
        if key in memo:
            return memo[key]
        total = 0
        zmap = dict(zip(F[j], z))
        for k in S.D[j]:
            zmap[j] = k
            if all(pred(tuple(zmap[i] for i in scope)) for scope, pred in by_max.get(j, [])):
                total += comp(j + 1, tuple(zmap[i] for i in F[j + 1]))
        memo[key] = total
        return total

    comp(0, ())
    return comp, F, by_max


def unrank(S, comp, F, by_max, r):
    m = S.m
    chosen = []
    zmap = {}
    z = ()
    for j in range(m):
        zmap = dict(zip(F[j], z))
        for k in S.D[j]:  # fixed order = increasing class id, giving lexicographic order
            zmap[j] = k
            if all(pred(tuple(zmap[i] for i in scope)) for scope, pred in by_max.get(j, [])):
                zn = tuple(zmap[i] for i in F[j + 1])
                c = comp(j + 1, zn)
                if r < c:
                    chosen.append(k)
                    z = zn
                    break
                r -= c
        else:
            raise ValueError("rank out of range")
    return tuple(chosen)


for prod in "AB":
    for glass in (False, True):
        S1, cl = lawn_structure(prod, True, glass)
        S1u = Structure(S1.D, S1.C, None)
        comp, F, by_max = build_completion_tables(S1u)
        N = comp(0, ())
        listing = sorted(admissible_tuples(S1u))
        assert N == len(listing)
        got = [unrank(S1u, comp, F, by_max, r) for r in range(N)]
        assert got == listing
        print(prod, "glass" if glass else "chain", ": N =", N, " unrank(r) enumerates all admissible tuples in order: OK")

# ---------------------------------------- hardness: independent sets as editions
print("\n== independent sets as editions ==")
rng = random.Random(3)
for _ in range(5):
    n = 7
    edges = [(a, b) for a in range(n) for b in range(a + 1, n) if rng.random() < 0.35]
    S = Structure([[0, 1]] * n, [((a, b), (lambda v: not (v[0] == 1 and v[1] == 1))) for a, b in edges])
    cnt, _, _ = frontier_count(S)
    ind = 0
    for mask in range(1 << n):
        if all(not ((mask >> a) & 1 and (mask >> b) & 1) for a, b in edges):
            ind += 1
    assert cnt == ind
print("frontier DP counts independent sets correctly on 5 random graphs")

# ------------------------------- synthetic: several long-range constraints
print("\n== synthetic scene, nested long-range constraints (carry width against frontier table) ==")
rng = random.Random(11)
M = 10
Q = 4


def synthetic(c):
    dirs = [[rng.choice("LRN") for _ in range(Q)] for _ in range(M)]
    attrs = [[tuple(rng.randint(0, 1) for _ in range(3)) for _ in range(Q)] for _ in range(M)]
    D = [list(range(Q)) for _ in range(M)]
    cons = []
    for j in range(M - 1):
        cons.append(((j, j + 1), (lambda v, j=j: compat(dirs[j][v[0]], dirs[j + 1][v[1]]))))
    pairs = [(t, M - 1 - t) for t in range(c)]
    for t, (a, b) in enumerate(pairs):
        cons.append(((a, b), (lambda v, a=a, b=b, t=t: attrs[a][v[0]][t] == attrs[b][v[1]][t])))
    return Structure(D, cons), dirs, attrs, pairs


for c in (0, 1, 2, 3):
    S, dirs, attrs, pairs = synthetic(c)
    n_f, ops_f, sizes_f = frontier_count(S)
    n_b = brute_count(S)
    assert n_f == n_b
    # attribute fold: state = (direction of last take, attribute bits of the left endpoints)
    states_per_pos = []
    cur = {(None, ()): 1}
    for j in range(M):
        new = defaultdict(int)
        for (ld, held), cnt in cur.items():
            for k in range(Q):
                d = dirs[j][k]
                if ld is not None and not compat(ld, d):
                    continue
                # held = tuple of attribute bits of left endpoints t (slot t, attribute t)
                ok = True
                for t, (a, b) in enumerate(pairs):
                    if j == b and attrs[j][k][t] != held[t]:
                        ok = False
                if not ok:
                    continue
                new_held = list(held) if len(held) == c else [None] * c
                for t, (a, b) in enumerate(pairs):
                    if j == a:
                        new_held[t] = attrs[j][k][t]
                new[(d, tuple(new_held))] += cnt
        # collapse direction memory: after N, any next direction allowed, but keep separate for simplicity
        cur = dict(new)
        states_per_pos.append(len(cur))
    n_a = sum(cur.values())
    assert n_a == n_b
    F = S.frontier()
    fmax = max(len(f) for f in F)
    fsize = max(Q ** len(f) for f in F)
    print(f"c={c}: count {n_b}, frontier width {fmax}, largest frontier table over classes {fsize}, "
          f"largest attribute-fold state set {max(states_per_pos)}, table updates {ops_f}")
