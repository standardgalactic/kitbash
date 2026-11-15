#!/usr/bin/env python3
"""Shared discussion in the engine scene (Chapter 17, Study One): what two viewers of faithful editions can
jointly say about the third bolt before and after a reveal film. Uses the engine scene of Chapter 3.

Run with:  python3 verify_ch17_shared.py
"""
import itertools
from collections import Counter

H = []
for t in itertools.product("TS", repeat=3):
    if "S" not in t:
        H.append(t + ("N", "none"))
    else:
        H.append(t + ("N", "none")); H.append(t + ("Y", "honest")); H.append(t + ("Y", "concealed"))
def reading(h):
    t1, t2, t3, n, r = h
    if "S" not in (t1, t2, t3): return "diligence"
    if n == "N": return "negligence"
    return "disclosure" if r == "honest" else "concealment"
hstar = ("T", "T", "S", "Y", "concealed")
A = lambda h: True
slots = [[("wide-1", A), ("wide-2", A)],
         [("bench", A)] + [x for i in range(3) for x in ((f"close{i+1}-tight", lambda h, i=i: h[i] == "T"), (f"close{i+1}-loose", lambda h, i=i: h[i] == "S"))],
         [("glance-yes", lambda h: h[3] == "Y"), ("glance-no", lambda h: h[3] == "N"), ("cutaway-3", A)],
         [("handoff-clean", lambda h: h[4] in ("none", "concealed")), ("handoff-honest", lambda h: h[4] == "honest"), ("cutaway-4", A)]]
def C(e): return frozenset(h for h in H if all(slots[j][e[j]][1](h) for j in range(4)))
eds = [e for e in itertools.product(*[range(len(s)) for s in slots]) if hstar in C(e)]
assert len(eds) == 32
name = lambda e, j: slots[j][e[j]][0]

Q3 = frozenset(h for h in H if h[2] == "S")            # claim: the third bolt was left loose
Qc = frozenset(h for h in H if reading(h) == "concealment")   # the reveal film commits to the concealment reading
def warrants(K, Q): return K <= Q
def direct(e): return name(e, 1) == "close3-loose"      # the viewer was shown the loose third bolt

print("faithful editions:", len(eds))
st = Counter()
for e in eds:
    w = warrants(C(e), Q3)
    st["direct" if direct(e) else ("inferred" if w else "open")] += 1
print("before the reveal: claim 'the third bolt was left loose' is  shown directly:", st["direct"], " warranted by inference:", st["inferred"], " left open:", st["open"])
assert all(warrants(C(e), Q3) for e in eds if direct(e))

def after(e): return C(e) & Qc
st2 = Counter()
for e in eds:
    st2["warranted" if warrants(after(e), Q3) else "open"] += 1
print("after the reveal film: claim warranted for", st2["warranted"], "of 32, left open for", st2["open"])
print("settled reading after the reveal:", Counter(frozenset(reading(h) for h in after(e)) == {"concealment"} for e in eds))

pairs = list(itertools.combinations(eds, 2))
kind = lambda e: "direct" if direct(e) else ("inferred" if warrants(C(e), Q3) else "open")
pc = Counter(tuple(sorted((kind(a), kind(b)))) for a, b in pairs)
print("\npairs of faithful editions (", len(pairs), ") by how each viewer holds the claim before the reveal:")
for k, v in sorted(pc.items()): print("  ", k, v)
same_state = sum(1 for a, b in pairs if C(a) == C(b))
same_read = sum(1 for a, b in pairs if {reading(h) for h in C(a)} == {reading(h) for h in C(b)})
print("pairs with identical commitment sets:", same_state, "; identical sets of open readings:", same_read)
common = Counter(sum(1 for j in range(4) if a[j] == b[j]) for a, b in pairs)
print("pairs by number of slots at which both viewers saw the same class:", sorted(common.items()))
both = sum(1 for a, b in pairs if warrants(C(a), Q3) and warrants(C(b), Q3))
both_direct_same = sum(1 for a, b in pairs if direct(a) and direct(b))
print("pairs in which both are warranted:", both, "; both saw it directly (the same shot, within a locale):", both_direct_same)
after_both = sum(1 for a, b in pairs if warrants(after(a), Q3) and warrants(after(b), Q3))
print("after the reveal film, pairs in which both are warranted:", after_both)

print("\nthe reading claim 'someone skipped a bolt and concealed it':")
wb = [e for e in eds if warrants(C(e), Qc)]
print("  warranted before the reveal for", len(wb), "of 32; after the reveal film for", sum(1 for e in eds if warrants(after(e), Qc)), "of 32")
pb = sum(1 for a, b in pairs if warrants(C(a), Qc) and warrants(C(b), Qc))
print("  pairs in which both are warranted before:", pb, "; after:", len(pairs))
# pairs sharing the reading claim after the reveal but not the event claim
mixed = sum(1 for a, b in pairs if not (warrants(after(a), Q3) and warrants(after(b), Q3)))
print("after the reveal, pairs that share the reading and do not both warrant the third-bolt claim:", mixed)
# evidence that both can point to: classes in common that bear on the claim
bear = lambda e, j: C(e) != frozenset(H) and slots[j][e[j]][0] not in ("wide-1", "wide-2", "bench", "cutaway-3", "cutaway-4")
ev = Counter(sum(1 for j in range(4) if a[j] == b[j] and bear(a, j)) for a, b in pairs)
print("pairs by number of informative shots seen in common (close-ups, glance, handoff):", sorted(ev.items()))
