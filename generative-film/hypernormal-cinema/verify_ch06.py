#!/usr/bin/env python3
"""Reproduces every count in Chapter 6 (sound, dialogue, and time).
Data: data/seconds.csv and data/occupation.json, the per-second table and block list of the acoustic occupation analysis."""
import json, itertools, math
import numpy as np
import pandas as pd

d = pd.read_csv("data/seconds.csv"); oc = json.load(open("data/occupation.json"))
rel = d.rel_db.values; audible = d.audible.values.astype(bool); occ = d.occupied.values.astype(bool)
n = len(d)
P0, P1 = 3639, 4851   # 1:00:39 to 1:20:51

def runs_of(mask):
    out = []; i = 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]: j += 1
            out.append((i, j + 1)); i = j + 1
        else: i += 1
    return out

fmt = lambda s: "%d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)

print("== measured quantities ==")
print("seconds in table", n, "| dialogue reference", oc["dialogue_reference"], "| delta", oc["delta_db"])
blocks = [(int(b["start"]), int(b["end"])) for b in oc["occupation_blocks"]]
print("occupation blocks", len(blocks), "total min", round(sum(b - a for a, b in blocks) / 60, 1), "longest min", round(max(b - a for a, b in blocks) / 60, 1))
assert len(blocks) == 9
low = (rel <= 0) | (~audible)
win = [r for r in runs_of(low) if r[1] - r[0] >= 5]
tot = sum(b - a for a, b in win)
print("recovery windows (>=5 s at or below D, or inaudible):", len(win), "total seconds", tot)
assert len(win) == 105 and tot == 1526

print("\n== tolerance of a cut to a shift: how much each structure can lose before it changes ==")
lens = np.array([b - a for a, b in win])
slack_w = lens - 5
print("windows: shortening slack total", int(slack_w.sum()), "s; median window", int(np.median(lens)), "s; windows of 5 or 6 s (within 1 s of ceasing to qualify):", int((lens <= 6).sum()), "of", len(lens))
bl = np.array([b - a for a, b in blocks])
print("blocks: durations", bl.tolist(), "| slack above the 60 s minimum", (bl - 60).tolist(), "| blocks within 5 s of ceasing to be blocks:", int(((bl - 60) <= 5).sum()))
gaps = [blocks[i + 1][0] - blocks[i][1] for i in range(len(blocks) - 1)]
print("gaps between consecutive blocks (s):", gaps)
print("gaps that a cut of at most 10 s would close to the merge gap of 5 s:", [(fmt(blocks[i][1]), g) for i, g in enumerate(gaps) if g - 5 <= 10])

print("\n== the passage 1:00:39 to 1:20:51 ==")
pw = [(a, b) for a, b in win if a >= P0 and b <= P1]
print("windows in passage", [(fmt(a), fmt(b), b - a) for a, b in pw], "total", sum(b - a for a, b in pw))
assert [b - a for a, b in pw] == [9, 7, 13]
print("shortening slack of the three windows:", [b - a - 5 for a, b in pw], "total", sum(b - a - 5 for a, b in pw))
print("gap between the last two windows:", pw[2][0] - pw[1][1], "s (a cut of that second merges them into one window of", pw[2][1] - pw[1][0], "s)")
print("blocks inside the passage:", sum(1 for a, b in blocks if a >= P0 and b <= P1))

print("\n== saturating response: the pause before the question (stipulated model of the earlier volume) ==")
q1 = lambda p1, p4=4.0: math.tanh((p1 + 0.5 * p4) / 6)
base = q1(7)
print("base q1", round(base, 4))
eps = 0.05
lo = 6 * math.atanh(base - eps) - 2
hi = 6 * math.atanh(base + eps) - 2
print("pause may be shortened to", round(lo, 2), "(by", round(7 - lo, 2), "s) and lengthened to", round(hi, 2), "(by", round(hi - 7, 2), "s)")
print("linearised symmetric tolerance +-", round(eps / (1 / 6 * (1 - base ** 2)), 2), "s")
print("reduction of 4 s: linearised cost", round(4 * (1 / 6) * (1 - base ** 2), 3), "model cost", round(base - q1(3), 3))
assert abs((7 - lo) - 1.35) < 0.01 and abs((hi - 7) - 2.32) < 0.01

print("\n== timed editions: timing variants per slot and under a total-duration constraint ==")
nominal = [4.0, 3.0, 5.0, 3.0, 6.0]
eps_t = 0.5
def grid_counts(lo_hi):
    per = [int(round((h - l) / eps_t)) + 1 for l, h in lo_hi]
    box = int(np.prod(per))
    # count grid vectors with sum equal to nominal sum
    T = int(round((sum(nominal) - sum(l for l, h in lo_hi)) / eps_t))
    dp = {0: 1}
    for (l, h) in lo_hi:
        k = int(round((h - l) / eps_t)); new = {}
        for s, c in dp.items():
            for t in range(k + 1): new[s + t] = new.get(s + t, 0) + c
        dp = new
    return per, box, dp.get(T, 0)
sym = [(x - 1, x + 1) for x in nominal]
per, box, fixed = grid_counts(sym)
print("handles of +-1 s on every slot, tolerance 0.5 s: grid points per slot", per, "box", box, "with total duration fixed", fixed)
# dialogue lines at slots 2 and 4 forbid trimming below nominal
dlg = [(x - 1, x + 1) if j not in (1, 3) else (x, x + 1) for j, x in enumerate(nominal)]
per2, box2, fixed2 = grid_counts(dlg)
print("slots 2 and 4 hold dialogue lines that cannot be trimmed below nominal: per slot", per2, "box", box2, "with total fixed", fixed2)
for name, K in (("A", 238), ("B", 96), ("C", 1)):
    print(name, "class bits", round(math.log2(K), 2), "| timing bits box", round(math.log2(box), 2), "fixed total", round(math.log2(fixed), 2),
          "| with dialogue box", round(math.log2(box2), 2), "fixed total", round(math.log2(fixed2), 2))
print("editions (class tuples x timing grid, total fixed, with dialogue):", {k: K * fixed2 for k, K in (("A", 238), ("B", 96), ("C", 1))})
