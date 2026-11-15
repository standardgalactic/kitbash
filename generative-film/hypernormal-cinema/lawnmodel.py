"""Shared model of the lawn scene for Chapters 5, 9, and 10 (same pools as Chapters 1 and 4)."""
import itertools
import random

m = 5
strips = ["a", "b", "c"]
script = ["a", "b", "c"]
slots = [(0, ("a", "b", "c")), (1, ("a",)), (2, ("a", "b")), (2, ("c",)), (3, ("a", "b", "c"))]

# entries: (direction, status, number of classes, takes per class, strip misdepicted if stale)
pools = {
    "A": [
        [("L", "ok", 2, 3, None), ("R", "ok", 2, 3, None), ("N", "ok", 1, 3, None)],
        [("L", "ok", 2, 3, None), ("R", "ok", 1, 3, None), ("N", "ok", 1, 3, None), ("L", "stale", 1, 3, "a")],
        [("L", "ok", 1, 3, None), ("R", "ok", 2, 3, None), ("R", "stale", 1, 3, "a")],
        [("N", "ok", 2, 3, None), ("L", "ok", 1, 3, None), ("R", "stale", 1, 3, "c")],
        [("L", "ok", 1, 3, None), ("R", "ok", 2, 3, None), ("N", "ok", 1, 3, None), ("L", "stale", 1, 3, "b")],
    ],
    "B": [
        [("L", "ok", 2, 2, None), ("R", "ok", 3, 2, None)],
        [("L", "ok", 2, 2, None), ("R", "ok", 2, 2, None), ("R", "stale", 2, 2, "a")],
        [("L", "ok", 3, 2, None), ("R", "ok", 2, 2, None), ("L", "stale", 2, 2, "b")],
        [("L", "ok", 2, 2, None), ("R", "ok", 2, 2, None)],
        [("L", "ok", 2, 2, None), ("R", "ok", 2, 2, None), ("R", "stale", 3, 2, "c")],
    ],
    "C": [
        [("L", "ok", 1, 40, None), ("R", "ok", 1, 40, None)],
        [("L", "ok", 1, 40, None), ("L", "stale", 1, 40, "a")],
        [("L", "ok", 1, 40, None), ("R", "ok", 1, 40, None)],
        [("L", "ok", 1, 40, None), ("R", "ok", 1, 40, None)],
        [("L", "ok", 1, 40, None), ("R", "stale", 1, 40, "c")],
    ],
}
audience = {"A": 60, "B": 30, "C": 2}


def classes(prod):
    out = []
    for entries in pools[prod]:
        cl = []
        for (d, st, q, mu, wrong) in entries:
            for _ in range(q):
                cl.append({"dir": d, "stale": st == "stale", "mu": mu, "wrong": wrong})
        out.append(cl)
    return out


def compat(d1, d2):
    return d1 == d2 or d1 == "N" or d2 == "N"


class State:
    """admissible domain per slot (set of class indices) and take counts per class"""

    def __init__(self, prod):
        self.prod = prod
        self.cl = classes(prod)
        self.dom = [set(range(len(c))) for c in self.cl]
        self.takes = [[c["mu"] for c in col] for col in self.cl]

    def copy(self):
        s = State.__new__(State)
        s.prod = self.prod
        s.cl = self.cl
        s.dom = [set(d) for d in self.dom]
        s.takes = [list(t) for t in self.takes]
        return s

    def live(self, j):
        """classes at slot j that are admissible and retain at least one take"""
        return sorted(k for k in self.dom[j] if self.takes[j][k] > 0)

    def tuples(self):
        out = []
        for tup in itertools.product(*[self.live(j) for j in range(m)]):
            if all(compat(self.cl[j][tup[j]]["dir"], self.cl[j + 1][tup[j + 1]]["dir"]) for j in range(m - 1)):
                out.append(tup)
        return out

    def capacity(self):
        return len(self.tuples())

    def take_tuples(self):
        tot = 0
        for tup in self.tuples():
            w = 1
            for j in range(m):
                w *= self.takes[j][tup[j]]
            tot += w
        return tot


def alpha(state, strip_set, slot_set):
    """agreement rule for the given strips at the given slots (1-based): drop stale classes that misdepict such a strip there"""
    s = state.copy()
    for j1 in slot_set:
        j = j1 - 1
        for k, c in enumerate(s.cl[j]):
            if c["stale"] and c["wrong"] in strip_set:
                s.dom[j].discard(k)
    return s


def omega(state, r=1):
    """withdraw r takes from every class at every slot (take-level amendment)"""
    s = state.copy()
    for j in range(m):
        for k in range(len(s.cl[j])):
            s.takes[j][k] = max(0, s.takes[j][k] - r)
    return s


def withdraw_class(state, j1, k):
    s = state.copy()
    s.dom[j1 - 1].discard(k)
    return s


def through_counts(state):
    """number of admissible class tuples through each (slot, class)"""
    cnt = {}
    for tup in state.tuples():
        for j in range(m):
            cnt[(j, tup[j])] = cnt.get((j, tup[j]), 0) + 1
    return cnt


def intersect(states):
    s = states[0].copy()
    for t in states[1:]:
        for j in range(m):
            s.dom[j] &= t.dom[j]
            for k in range(len(s.cl[j])):
                s.takes[j][k] = min(s.takes[j][k], t.takes[j][k])
    return s


def hamming(p, q):
    return sum(1 for x, y in zip(p, q) if x != y)
