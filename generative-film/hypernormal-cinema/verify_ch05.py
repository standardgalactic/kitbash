#!/usr/bin/env python3
"""Reproduces every count in Chapter 5 (continuity beyond neighbours)."""
import itertools
from lawnmodel import *

# ---------------------------------------------------------------- story structure
# slots 1..5 with times and visible strips
times = {1: 0, 2: 1, 3: 2, 4: 2, 5: 3}
vis = {1: {"a", "b", "c"}, 2: {"a"}, 3: {"a", "b"}, 4: {"c"}, 5: {"a", "b", "c"}}
# script events: mow a at 0->1, b at 1->2, c at 2->3 ; event e_s occurs between time t_s-1 and t_s
event_time = {"a": 1, "b": 2, "c": 3}      # strip s is mown from time event_time[s] on
glass_vis = {1, 2, 5}                       # slots that show the glass
print("== showings, persistence intervals, footprints ==")
foot, late, early = {}, {}, {}
for s in "abc":
    sh = sorted(j for j in vis if s in vis[j])
    foot[s] = sh
    late[s] = [j for j in sh if times[j] >= event_time[s]]
    early[s] = [j for j in sh if times[j] < event_time[s]]
    print(s, "showings", sh, "before event", early[s], "after event", late[s])
assert late["a"] == [2, 3, 5] and late["b"] == [3, 5] and late["c"] == [5]
assert foot["a"] == [1, 2, 3, 5] and foot["b"] == [1, 3, 5] and foot["c"] == [1, 4, 5]

# defects: (strip, slot, kind) kind: 'reappear' (shown unmown after its event) or 'premature' (shown mown before)
def touched(strip, slot):
    """slots touched by an amendment answering a defect on this strip at this slot"""
    if times[slot] >= event_time[strip]:
        return late[strip]                      # post-event persistence interval
    return early[strip]                         # pre-event persistence interval

print("\n== slot sets derived from the stale classes of the pools ==")
derived = {"a": set(), "b": set(), "c": set()}
for prod in "ABC":
    cl = classes(prod)
    for j in range(m):
        for c in cl[j]:
            if c["stale"]:
                derived[c["wrong"]] |= set(touched(c["wrong"], j + 1))
                print(prod, "slot", j + 1, "strip", c["wrong"], "->", "post" if times[j+1] >= event_time[c["wrong"]] else "pre", sorted(touched(c["wrong"], j + 1)))
print("derived:", {k: sorted(v) for k, v in derived.items()})
assert derived["a"] == {2, 3, 5} and derived["b"] == {3, 5} and derived["c"] == {1, 4, 5}
print("matches the slot sets of Chapter 9")

# ---------------------------------------------------------------- nested levels
print("\n== nested levels: interval, entity, type (c: the interval of the premature defect) ==")
base = {p: State(p) for p in "ABC"}
levels = {
    "a": {"local": [2, 3, 5], "entity": [1, 2, 3, 5]},
    "b": {"local": [3, 5], "entity": [1, 3, 5]},
    "c": {"local": [1, 4], "entity": [1, 4, 5]},
}
for p in "ABC":
    N0 = base[p].capacity()
    row = {}
    for s in "abc":
        for lv in ("local", "entity"):
            row[(s, lv)] = alpha(base[p], {s}, set(levels[s][lv])).capacity()
    typ = alpha(base[p], {"a", "b", "c"}, {1, 2, 3, 4, 5}).capacity()
    row[("c", "late interval")] = alpha(base[p], {"c"}, {5}).capacity()
    print(p, "premiere", N0, row, "type", typ)
# which stale classes escape a local amendment but are caught by the entity amendment
for p in "ABC":
    cl = classes(p)
    for s in "abc":
        loc = set(levels[s]["local"]); ent = set(levels[s]["entity"])
        esc = [(j + 1, c["dir"]) for j in range(m) for c in cl[j] if c["stale"] and c["wrong"] == s and (j + 1) in ent - loc]
        if esc:
            print(p, "strip", s, "stale classes caught only by entity level:", esc)

# soundness/completeness: amendment answering the full defect set for each strip equals the derived one
for p in "ABC":
    full = base[p]
    for s in "abc":
        full = alpha(full, {s}, derived[s])
    assert full.capacity() == alpha(base[p], {"a", "b", "c"}, {1, 2, 3, 4, 5}).capacity()
print("derived amendments together equal the type-level rule on every pool")

# ---------------------------------------------------------------- relative continuity: glass
print("\n== relative continuity: the glass ==")
def hand(j1, k):
    return "l" if k % 2 == 0 else "r"

def count(prod, rule_G, scopes):
    """class tuples admissible under direction rule, optional G, plus hand relations given as scopes: list of (slotlist, relation)"""
    S = base[prod]
    if rule_G:
        S = alpha(S, {"a", "b", "c"}, {1, 2, 3, 4, 5})
    n = 0
    for tup in S.tuples():
        if all(rel([hand(j, tup[j - 1]) for j in sl]) for sl, rel in scopes):
            n += 1
    return n

eq = lambda hs: len(set(hs)) == 1
print("slots {2,5} equality (Chapter 4 glass):")
for p in "ABC":
    print(p, count(p, False, [([2, 5], eq)]), "->", count(p, True, [([2, 5], eq)]))
assert (count("A", False, [([2, 5], eq)]), count("A", True, [([2, 5], eq)])) == (241, 119)
assert (count("B", False, [([2, 5], eq)]), count("B", True, [([2, 5], eq)])) == (160, 48)
assert (count("C", False, [([2, 5], eq)]), count("C", True, [([2, 5], eq)])) == (1, 1)
print("reproduces the Chapter 4 glass counts")

print("\nglass shown at slots 1,2,5, no event on the glass (equality):")
path = [([1, 2], eq), ([2, 5], eq)]
clique = path + [([1, 5], eq)]
for p in "ABC":
    cp, cc = count(p, False, path), count(p, False, clique)
    print(p, "path", cp, "clique", cc, "equal:", cp == cc, "| with G:", count(p, True, path), count(p, True, clique))
    assert cp == cc and count(p, True, path) == count(p, True, clique)

print("\nglass with a pass-over event between slots 2 and 5 (hand at 5 opposite to hand at 2):")
opp = lambda hs: hs[0] != hs[1]
ev = [([1, 2], eq), ([2, 5], opp)]
ev_clique = ev + [([1, 5], opp)]
for p in "ABC":
    cp = count(p, False, ev); cc = count(p, False, ev_clique)
    print(p, "with event", cp, "clique form", cc, "equal:", cp == cc, "| with G:", count(p, True, ev), count(p, True, ev_clique))
    assert cp == cc

# ---------------------------------------------------------------- frontier widths
def frontier_width(n, edges):
    """max over cuts l of number of vertices <= l with a neighbour > l (vertex sets 1..n)"""
    best = 0
    for l in range(1, n):
        live = {u for (u, v) in edges for u2, v2 in [(min(u, v), max(u, v))] if u2 <= l < v2 for u in [u2]}
        best = max(best, len(live))
    return best

chain = [(j, j + 1) for j in range(1, 5)]
def fw(edges):
    return frontier_width(5, edges)
print("\n== frontier width of the lawn structures ==")
print("chain only:", fw(chain))
print("chain + glass path (1-2, 2-5):", fw(chain + [(1, 2), (2, 5)]))
print("chain + glass clique (adds 1-5):", fw(chain + [(1, 2), (2, 5), (1, 5)]))
print("chain + glass {2,5} only:", fw(chain + [(2, 5)]))

print("\n== one entity shown at every slot of an n-slot chain, q classes per slot ==")
print("n, path width, clique width, path table q=4, clique table q=4")
for n in range(3, 9):
    ch = [(j, j + 1) for j in range(1, n)]
    pe = ch
    ce = ch + [(i, j) for i in range(1, n + 1) for j in range(i + 2, n + 1)]
    w_p = frontier_width(n, pe); w_c = frontier_width(n, ce)
    print(n, w_p, w_c, 4 ** w_p, 4 ** w_c)

# ---------------------------------------------------------------- footprint of an event with a coupled entity
print("\n== footprint of an event whose effect set couples two entities ==")
glass_foot = sorted(glass_vis)
fe = sorted(set(foot["b"]) | set(glass_foot))
print("event e_b alone:", foot["b"], "| glass:", glass_foot, "| e_b passing the glass:", fe)
for p in "ABC":
    N0 = base[p].capacity()
    print(p, "capacity after entity-level amendment of b:", alpha(base[p], {"b"}, set(foot["b"])).capacity(),
          "| coupled event amendment (b at event footprint):", alpha(base[p], {"b"}, set(fe)).capacity())
