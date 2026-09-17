#!/usr/bin/env python3
"""
occupation-extras.py
====================

Supplementary statistics for Chapter 7 and Chapter 8, computed from the
per-second table (seconds.csv) and occupation.json that occupation.py
writes. Produces results/extras.tex (LaTeX macros) and
results/fig-segments.png.

    python3 code/occupation-extras.py --results results
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--results", default="results")
p.add_argument("--segment", type=float, default=600.0,
               help="segment length in seconds for the timeline table")
args = p.parse_args()

R = Path(args.results)
s = pd.read_csv(R / "seconds.csv")
j = json.loads((R / "occupation.json").read_text())
delta = j["delta_db"]

a = s[s["audible"]].copy()
exc = a["rel_db"] >= delta
dlg = a[a["dialogue_sub"]] if a["dialogue_sub"].any() else a[a["dialogue_proxy"]]
inb = a["in_block"]


def f1(x, spec="+.1f"):
    return format(float(x), spec) if np.isfinite(x) else "--"


def pc(x):
    return f"{100 * float(x):.1f}\\%" if np.isfinite(x) else "--"


def ts(sec):
    sec = int(round(sec))
    return f"{sec // 3600:d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


m = {}
thr = [b["implied_throttle_db"] for b in j["occupation_blocks"]]
m["xThrottleMin"] = f1(min(thr), ".1f") if thr else "--"

# Dialogue spread and dialogue inside blocks
q = dlg["rel_db"].quantile([0.1, 0.25, 0.75, 0.9])
m["xDlgPTen"], m["xDlgPTwentyFive"] = f1(q[0.1]), f1(q[0.25])
m["xDlgPSeventyFive"], m["xDlgPNinety"] = f1(q[0.75]), f1(q[0.9])
m["xDlgInBlockMedian"] = f1(dlg.loc[dlg["in_block"], "rel_db"].median())
m["xDlgOutBlockMedian"] = f1(dlg.loc[~dlg["in_block"], "rel_db"].median())
m["xCenterAdvDlg"] = f1(dlg["center_adv"].median(), ".1f")
m["xCenterAdvOther"] = f1(a.loc[~a["dialogue_sub"], "center_adv"].median(), ".1f")

# Shape of the occupied range
o = a.loc[exc, "rel_db"]
qo = o.quantile([0.5, 0.9, 0.99])
m["xOccMedian"], m["xOccPNinety"], m["xOccPNinetyNine"] = f1(qo[0.5]), f1(qo[0.9]), f1(qo[0.99])
m["xOccPlateauShare"] = pc(((o >= 12) & (o < 19)).mean())
m["xRelMax"] = f1(a["rel_db"].max())
m["xLevelMax"] = f1(a["level_db"].max(), ".1f")
m["xOccSeconds"] = str(int(exc.sum()))
m["xOccInBlocks"] = str(int((exc & inb).sum()))
m["xOccInBlocksShare"] = pc((exc & inb).sum() / max(1, exc.sum()))
I = j.get("loudness", {}).get("integrated_lufs", float("nan"))
m["xDialogueBelowIntegrated"] = f1(I - j["dialogue_reference"], ".1f")

# Overdetermination without the exceedance term
other_raw = a["omega"] - exc.astype(int)
other_res = a["omega_resid"] - exc.astype(int)
m["xOtherRawIn"], m["xOtherRawOut"] = f1(other_raw[inb].mean(), ".2f"), f1(other_raw[~inb].mean(), ".2f")
m["xOtherResIn"], m["xOtherResOut"] = f1(other_res[inb].mean(), ".2f"), f1(other_res[~inb].mean(), ".2f")
for col, key in (("barrage", "Barrage"), ("drum", "Drum"), ("harsh", "Harsh")):
    m[f"x{key}In"] = f1(a.loc[inb, col].mean(), ".2f")
    m[f"x{key}Out"] = f1(a.loc[~inb, col].mean(), ".2f")

# Recovery inside the span of the longest absolute gap and its neighbours
gaps = sorted(j["abs_gaps_top5"], key=lambda g: g["start"])
# Contiguous cluster containing the longest gap: gaps separated by short windows
longest = max(j["abs_gaps_top5"], key=lambda g: g["end"] - g["start"])
cluster = [longest]
changed = True
while changed:
    changed = False
    for g in gaps:
        if g in cluster:
            continue
        lo = min(c["start"] for c in cluster)
        hi = max(c["end"] for c in cluster)
        if 0 <= lo - g["end"] <= 30 or 0 <= g["start"] - hi <= 30:
            cluster.append(g)
            changed = True
c0 = min(c["start"] for c in cluster)
c1 = max(c["end"] for c in cluster)
span = a[(a["second"] >= c0) & (a["second"] < c1)]
m["xSpanStart"], m["xSpanEnd"] = ts(c0), ts(c1)
m["xSpanMin"] = f1((c1 - c0) / 60, ".1f")
m["xSpanRecoverySeconds"] = str(int(round((c1 - c0) - sum(c["end"] - c["start"] for c in cluster))))
m["xSpanExceedShare"] = pc((span["rel_db"] >= delta).mean())
m["xSpanAtOrBelowShare"] = pc((span["rel_db"] <= 0).mean())
m["xSpanMedianRel"] = f1(span["rel_db"].median())
before = a[a["second"] < c0]
m["xBeforeExceedShare"] = pc((before["rel_db"] >= delta).mean())
m["xBeforeAtOrBelowShare"] = pc((before["rel_db"] <= 0).mean())
m["xBeforeInBlockShare"] = pc(before["in_block"].mean())
m["xSpanInBlockShare"] = pc(span["in_block"].mean())

# Segment table
rows = []
seg = args.segment
for k in range(int(np.ceil(s["second"].max() / seg))):
    t0, t1 = k * seg, min((k + 1) * seg, s["second"].max() + 1)
    x = a[(a["second"] >= t0) & (a["second"] < t1)]
    if len(x) == 0:
        continue
    rows.append((t0, t1, (x["rel_db"] >= delta).mean(), (x["rel_db"] <= 0).mean(),
                 x["in_block"].mean(), x["dialogue_sub"].mean(), x["rel_db"].median()))
m["xSegmentRows"] = " \\\\\n".join(
    f"{ts(t0)}--{ts(t1)} & {100 * e:.0f} & {100 * r:.0f} & {100 * b:.0f} & {100 * d:.0f} & {md:+.1f}"
    for t0, t1, e, r, b, d, md in rows)

fig, ax = plt.subplots(figsize=(10, 3.2))
mid = [(r[0] + r[1]) / 120 for r in rows]
ax.plot(mid, [100 * r[2] for r in rows], marker="o", color="tab:red", label=f"at least +{delta:.0f} dB")
ax.plot(mid, [100 * r[3] for r in rows], marker="o", color="tab:blue", label="at or below dialogue")
ax.plot(mid, [100 * r[5] for r in rows], marker="o", color="0.5", ls="--", label="subtitled speech")
ax.set_xlabel("Film time (minutes, segment midpoints)")
ax.set_ylabel("Share of audible seconds (%)")
ax.set_ylim(0, 100)
ax.legend(fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(R / "fig-segments.png", dpi=200)
plt.close(fig)

with open(R / "extras.tex", "w") as fh:
    fh.write("% Generated by occupation-extras.py. Do not edit by hand.\n")
    for k, v in m.items():
        fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")

for k, v in m.items():
    if k != "xSegmentRows":
        print(f"{k:28s} {v}")
print(m["xSegmentRows"].replace("\\\\", ""))
