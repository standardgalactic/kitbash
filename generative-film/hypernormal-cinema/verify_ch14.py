#!/usr/bin/env python3
"""Reproduces every count in Chapter 14 (sequence and reinterpretation), on the engine scene of Chapter 3."""
import itertools, math
from collections import Counter

H = []
for t in itertools.product("TS", repeat=3):
    H.append(t + ("N", "none"))
    if "S" in t:
        H.append(t + ("Y", "honest")); H.append(t + ("Y", "concealed"))
assert len(H) == 22

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

def committed(tup):
    return frozenset(h for h in H if all(slots[j][tup[j]][1](h) for j in range(4)))

eds = list(itertools.product(*[range(len(s)) for s in slots]))
faithful = [e for e in eds if hstar in committed(e)]
print("class tuples", len(eds), "faithful", len(faithful))
def R(K): return frozenset(reading(h) for h in K)

print("== A. openness of faithful editions (number of readings left open)")
op = Counter(len(R(committed(e))) for e in faithful)
print("openness distribution (readings: editions):", dict(sorted(op.items())))
print("mean openness %.3f" % (sum(len(R(committed(e))) for e in faithful) / len(faithful)))

later = {
    "notice": frozenset(h for h in H if h[3] == "Y"),
    "conceal": frozenset(h for h in H if h[3] == "Y" and h[4] == "concealed"),
    "bolt3": frozenset(h for h in H if h[2] == "S"),
    "unrelated": frozenset(H),
    "contra": frozenset(h for h in H if h[2] == "T"),
}
print("later films, histories committed:", {k: len(v) for k, v in later.items()})

print("== B. retrospective reading by intersection (earlier film, then later film)")
for g, L in later.items():
    shrink = 0; before = 0; after = 0; empty = 0; widen = 0
    for e in faithful:
        C = committed(e); K2 = C & L
        before += len(R(C))
        if not K2:
            empty += 1; continue
        after += len(R(K2))
        if len(R(K2)) < len(R(C)): shrink += 1
    n = len(faithful) - empty
    print(g, "editions where reading set shrinks", shrink, "of", len(faithful), "inconsistent (empty)", empty,
          "mean openness before %.3f after %.3f (consistent only)" % (sum(len(R(committed(e))) for e in faithful if committed(e) & L) / max(n, 1), after / max(n, 1)))

print("== C. monotonicity: more prior knowledge never widens a reading under intersection")
viol = 0; tot = 0
Ls = list(later.values())
for e in faithful:
    C = committed(e)
    for L1 in Ls:
        for L2 in Ls:
            K1 = C & L1; K12 = C & L1 & L2
            if K1 and K12:
                tot += 1
                if not R(K12) <= R(K1): viol += 1
print("pairs checked", tot, "violations", viol)

print("== D. first-viewing openness and release order (one open edition, two reveals)")
def seq_open(order, films):
    K = frozenset(H); tot = 0; prof = []
    for f in order:
        C = films[f]
        Kn = K & C
        if not Kn:
            Kn = C           # revision: the latest film takes priority
        o = len(R(Kn)); prof.append(o); tot += o; K = Kn
    return tot, tuple(prof)
cnt_diff = Counter(); best_orders = Counter()
for e in faithful:
    films = {"e": committed(e), "notice": later["notice"], "conceal": later["conceal"]}
    res = {o: seq_open(o, films) for o in itertools.permutations(films)}
    totals = {o: r[0] for o, r in res.items()}
    spread = max(totals.values()) - min(totals.values())
    cnt_diff[spread] += 1
    mx = max(totals.values())
    for o, t in totals.items():
        if t == mx: best_orders[o] += 1
print("spread of total first-viewing openness across 6 orders (spread: editions):", dict(sorted(cnt_diff.items())))
print("orders attaining the maximum (count over editions, ties counted):", dict(best_orders))
# the open editions specifically
openeds = [e for e in faithful if len(R(committed(e))) == 4]
print("fully open faithful editions:", len(openeds))
for e in openeds[:1]:
    films = {"e": committed(e), "notice": later["notice"], "conceal": later["conceal"]}
    for o in itertools.permutations(films):
        print("   order", o, "profile", seq_open(o, films)[1], "total", seq_open(o, films)[0])

print("== E. non-commutativity when a later film contradicts (revision, latest first)")
def final(order, films):
    K = frozenset(H)
    for f in order:
        Kn = K & films[f]
        K = Kn if Kn else films[f]
    return K
for g in ("contra", "bolt3", "conceal"):
    diff = 0; incons = 0
    for e in faithful:
        films = {"e": committed(e), g: later[g]}
        a = final(("e", g), films); b = final((g, "e"), films)
        if a != b: diff += 1
        if not (films["e"] & films[g]): incons += 1
    print(g, "faithful editions whose final state depends on order", diff, "of", len(faithful), "inconsistent pairs", incons)

print("== F. orderings of a repertoire")
for n in (5, 10, 80):
    print(n, "films: orderings", math.factorial(n) if n <= 10 else "log10 = %.1f" % (math.log10(math.factorial(n))))
def linear_extensions(n, prec):
    c = 0
    for p in itertools.permutations(range(n)):
        pos = {x: i for i, x in enumerate(p)}
        if all(pos[a] < pos[b] for a, b in prec): c += 1
    return c
print("5 films, 0 constraints", linear_extensions(5, []))
print("5 films, 3 before 4 (reveal after setup)", linear_extensions(5, [(3, 4)]))
print("5 films, chain 0<1<2", linear_extensions(5, [(0, 1), (1, 2)]))
print("5 films, chain 0<1<2 and 3<4", linear_extensions(5, [(0, 1), (1, 2), (3, 4)]))
print("5 films, chain of five", linear_extensions(5, [(0, 1), (1, 2), (2, 3), (3, 4)]))
