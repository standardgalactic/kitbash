#!/usr/bin/env python3
"""Reproduces every count in Chapter 3 (histories, folds, and what a scene commits to): the engine scene."""
import itertools
from collections import Counter

# ---------------------------------------------------------------- histories
H = []
for t in itertools.product("TS", repeat=3):
    if "S" not in t:
        H.append(t + ("N", "none"))
    else:
        H.append(t + ("N", "none"))
        H.append(t + ("Y", "honest"))
        H.append(t + ("Y", "concealed"))
print("histories:", len(H))
assert len(H) == 22

def reading(h):
    t1, t2, t3, notice, rep = h
    if "S" not in (t1, t2, t3): return "diligence"
    if notice == "N": return "negligence"
    return "disclosure" if rep == "honest" else "concealment"

READ = ["diligence", "negligence", "disclosure", "concealment"]
print("readings:", Counter(reading(h) for h in H))
hstar = ("T", "T", "S", "Y", "concealed")
assert hstar in H and reading(hstar) == "concealment"

# ---------------------------------------------------------------- shot classes: what each commits to
def A_all(h): return True
slots = []
slots.append([("wide-1", A_all), ("wide-2", A_all)])
s2 = [("bench", A_all)]
for i in range(3):
    s2.append((f"close{i+1}-tight", lambda h, i=i: h[i] == "T"))
    s2.append((f"close{i+1}-loose", lambda h, i=i: h[i] == "S"))
slots.append(s2)
slots.append([("glance-yes", lambda h: h[3] == "Y"), ("glance-no", lambda h: h[3] == "N"), ("cutaway-3", A_all)])
slots.append([("handoff-clean", lambda h: h[4] in ("none", "concealed")), ("handoff-honest", lambda h: h[4] == "honest"), ("cutaway-4", A_all)])

def committed(tup):
    return [h for h in H if all(slots[j][tup[j]][1](h) for j in range(4))]

eds = list(itertools.product(*[range(len(s)) for s in slots]))
print("class tuples:", len(eds), "(slots have", [len(s) for s in slots], "classes)")

cons = [e for e in eds if committed(e)]
true_ = [e for e in eds if hstar in committed(e)]
print("\n== editions by what they commit to ==")
print("consistent with some history:", len(cons))
print("consistent with the script history h* (agreement with the story):", len(true_))
def rec(e, R): 
    C = committed(e); return bool(C) and all(reading(h) == R for h in C)
for R in READ:
    print("  recoverable as", R, ":", sum(1 for e in true_ if rec(e, R)), "of the", len(true_), "editions consistent with h*")
openall = [e for e in true_ if all(any(reading(h) == R for h in committed(e)) for R in READ)]
print("open to all four readings among those consistent with h*:", len(openall))
# editions that leave open the three readings that share a skip: negligence, disclosure, concealment
open3 = [e for e in true_ if all(any(reading(h) == R for h in committed(e)) for R in ("negligence", "disclosure", "concealment"))]
print("open to negligence, disclosure and concealment:", len(open3))

print("\n== the verdict and the annotation ==")
def displayed_loose(i):
    return "S"
# report: 'bolt 3 is shown loose in the close shot of slot 2'
cls = [k for k, (n, f) in enumerate(slots[1]) if n == "close3-loose"][0]
print("report on class close3-loose: history h* has t3 =", hstar[2])
print("  with the departure annotated as intended: displayed S matches h*; verdict rejected (act by a character)")
print("  with the script history all-tight and no annotation: displayed S differs; verdict upheld (error)")
# removing close3-loose as if it were an error
slots_backup = [list(s) for s in slots]
keep = [k for k, (n, f) in enumerate(slots[1]) if n != "close3-loose"]
def count_with(slot2_keep):
    n_true = 0; n_conc = 0
    for e in true_:
        if e[1] in slot2_keep:
            n_true += 1
            if rec(e, "concealment"): n_conc += 1
    return n_true, n_conc
print("editions consistent with h*:", len(true_), "-> after wrongly removing close3-loose:", count_with(set(keep))[0])
# classes inconsistent with h* (stale): which are they
stale = [(j, n) for j in range(4) for k, (n, f) in enumerate(slots[j]) if not f(hstar)]
print("classes that contradict h* (the errors):", stale)

print("\n== what a correction must not delete: evidence for the reading ==")
def minimal_evidence(R):
    """minimal sets of (slot,class) such that every edition consistent with h* using a superset of... brute: classes that appear in every recoverable edition"""
    recs = [e for e in true_ if rec(e, R)]
    common = [(j, slots[j][c][0]) for j in range(4) for c in range(len(slots[j])) if recs and all(e[j] == c for e in recs)]
    return recs, common
for R in ("concealment", "negligence", "diligence", "disclosure"):
    recs, common = minimal_evidence(R)
    print(R, "recoverable editions", len(recs))
# necessary classes for concealment: classes without which no edition is recoverable
recs, _ = minimal_evidence("concealment")
used = {j: Counter(e[j] for e in recs) for j in range(4)}
print("concealment-recoverable editions use these classes:", {j: {slots[j][c][0]: n for c, n in used[j].items()} for j in range(4)})
# amendment: rights withdrawn for glance-yes (slot 3)
gy = [k for k, (n, f) in enumerate(slots[2]) if n == "glance-yes"][0]
after = [e for e in recs if e[2] != gy]
print("after withdrawing glance-yes: concealment-recoverable editions", len(after), "of", len(recs))
hc = [k for k, (n, f) in enumerate(slots[3]) if n == "handoff-clean"][0]
after2 = [e for e in recs if e[3] != hc]
print("after withdrawing handoff-clean: concealment-recoverable editions", len(after2), "of", len(recs))
# a withdrawal that spares evidence: any slot-1 class
print("after withdrawing wide-1: concealment-recoverable editions", len([e for e in recs if e[0] != 0]), "of", len(recs))
# take-level: withdrawing one of two wide variants keeps classes
print("editions consistent with h* overall after withdrawing glance-yes:", len([e for e in true_ if e[2] != gy]), "of", len(true_))

print("\n== noise overcapture: tracking only what the future refers to ==")
noise_vars = 4        # four plates, wet or dry
cores = len(H)
print("histories without noise:", cores)
print("raw histories if every plate is tracked:", cores * 2 ** noise_vars)
for refs in range(0, 5):
    print("later references to", refs, "plates -> future-equivalence classes:", cores * 2 ** refs)
print("kinds of reference: an action that depends on the plate, a later shot that shows it, an inference that uses it")

print("\n== open versus recoverable ==")
rc = [e for e in true_ if rec(e, "concealment")]
print("editions that are both open to all four readings and recoverable as concealment:", len(set(openall) & set(rc)))
