#!/usr/bin/env python3
"""
occupation.py  (v2)
===================

Dialogue-referenced occupation analysis for Acoustic Occupation.

Inputs
    --frames     frames.csv from analyze-soundtrack-v3.1
    --events     events.csv from analyze-soundtrack-v3.1
    --film       the film itself (optional; enables BS.1770 loudness)
    --subtitles  an .srt aligned with the film (optional; enables a
                 subtitle-defined dialogue reference and validation of
                 the centre-channel proxy)

Outputs (in --out)
    results.tex          LaTeX macros consumed by the manuscript
    occupation.json      the same numbers, machine readable
    seconds.csv          per-second table used for everything below
    loudness.csv         cached BS.1770 momentary loudness (if --film)
    fig-occupation.png   level, dialogue reference, blocks, subtitle rug
    fig-exceedance.png   distribution of level relative to dialogue
    fig-blocks.png       level-defined vs transient-defined blocks

Changes from v1
    * Level can be BS.1770 loudness (ffmpeg ebur128, momentary values
      energy-averaged per second) instead of unweighted RMS of a mono
      downmix. Integrated loudness and loudness range are reported.
    * Subtitle cue timings define a second dialogue reference. SDH cues
      that describe sound rather than speech ([GUNFIRE], (sighs),
      music notes (U+266A, U+266B)) are removed. The centre-channel proxy is validated
      against subtitle coverage (precision and recall).
    * Subtitle offset can be estimated automatically by lagging cue
      coverage against centre-channel dominance.
    * The overdetermination index is computed both raw and with each
      channel residualised on level, so co-elevation that level alone
      explains is not counted.
    * Reports how much subtitled dialogue falls inside occupation
      blocks, i.e. dialogue exposed to being turned down or off.
"""

import argparse
import html
import json
import re
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


p = argparse.ArgumentParser()
p.add_argument("--frames", required=True)
p.add_argument("--events", required=True)
p.add_argument("--out", default="results")
p.add_argument("--film", default=None,
               help="film file; enables BS.1770 loudness via ffmpeg ebur128")
p.add_argument("--audio-stream", default="0:a:0")
p.add_argument("--level", choices=["auto", "lufs", "rms"], default="auto",
               help="auto = lufs when --film is given, else rms")
p.add_argument("--subtitles", default=None, help=".srt file")
p.add_argument("--sub-offset", default="auto",
               help="seconds to ADD to subtitle times, or 'auto', or '0'")
p.add_argument("--reference", choices=["auto", "subtitles", "proxy"],
               default="auto",
               help="auto = subtitles when available, else proxy")
p.add_argument("--delta", type=float, default=10.0)
p.add_argument("--merge-gap", type=float, default=5.0)
p.add_argument("--min-block", type=float, default=60.0)
p.add_argument("--center-adv", type=float, default=6.0)
p.add_argument("--dialogue-barrage-pct", type=float, default=75.0)
p.add_argument("--gate-floor", type=float, default=-65.0,
               help="audibility floor for RMS level (dBFS)")
p.add_argument("--lufs-floor", type=float, default=-60.0,
               help="audibility floor for BS.1770 level (LUFS)")
p.add_argument("--recovery-margin", type=float, default=0.0)
p.add_argument("--recovery-width", type=float, default=5.0)
p.add_argument("--channel-z", type=float, default=1.5)
args = p.parse_args()

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)


# ============================================================
# Helpers
# ============================================================

def ts(sec):
    sec = max(0, int(round(sec)))
    return f"{sec // 3600:d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


def energy_mean_db(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return np.nan
    return 10 * np.log10(np.mean(10 ** (x / 10)))


def runs(mask):
    mask = np.asarray(mask, dtype=bool)
    if not mask.any():
        return []
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def merge(intervals, gap):
    merged = []
    for a, b in sorted(intervals):
        if merged and a - merged[-1][1] <= gap:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]


def pct(x):
    return f"{100 * x:.1f}\\%" if np.isfinite(x) else "--"


def robust_scale(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return 1.0
    s = 1.4826 * np.median(np.abs(x - np.median(x)))
    if s < 1e-12:
        s = np.std(x)
    return s if s > 1e-12 else 1.0


# ============================================================
# BS.1770 loudness via ffmpeg ebur128
# ============================================================

EBU_LINE = re.compile(r"t:\s*([\d.]+).*?M:\s*(-?[\d.]+|-?inf|nan)\s+"
                      r"S:\s*(-?[\d.]+|-?inf|nan)")


def bs1770(film):
    cache = out / "loudness.csv"
    summ = out / "loudness-summary.json"
    if cache.exists() and summ.exists():
        print("Reusing", cache)
        return pd.read_csv(cache), json.loads(summ.read_text())

    print("Measuring BS.1770 loudness (one decode pass)...")
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", film,
           "-map", args.audio_stream, "-vn",
           "-af", "ebur128=framelog=info", "-f", "null", "-"]
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True,
                            errors="replace")
    t, m, s = [], [], []
    tail = []
    for line in proc.stderr:
        mm = EBU_LINE.search(line)
        if mm:
            t.append(float(mm.group(1)))
            m.append(-120.0 if "inf" in mm.group(2) else float(mm.group(2)))
            s.append(float(mm.group(3)) if "inf" not in mm.group(3) else -120.0)
        else:
            tail.append(line)
            tail = tail[-40:]
    proc.wait()
    if proc.returncode != 0 or not t:
        raise SystemExit("ebur128 measurement failed:\n" + "".join(tail))

    text = "".join(tail)

    def grab(label):
        r = re.search(label + r":\s*(-?[\d.]+)", text)
        return float(r.group(1)) if r else float("nan")

    summary = {"integrated_lufs": grab("I"), "lra_lu": grab("LRA"),
               "lra_low": grab("LRA low"), "lra_high": grab("LRA high")}
    df = pd.DataFrame({"time": t, "momentary": m, "short_term": s})
    df["momentary"] = df["momentary"].clip(lower=-120)
    df.to_csv(cache, index=False)
    summ.write_text(json.dumps(summary, indent=2))
    return df, summary


# ============================================================
# Subtitles
# ============================================================

SRT_TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")
TAG = re.compile(r"<[^>]+>|\{[^}]+\}")
NONSPEECH = re.compile(r"^\s*(\[[^\]]*\]|\([^)]*\)|[\u266a\u266b#*\s-]+)+\s*$")


def parse_srt(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    cues = []
    for block in re.split(r"\r?\n\s*\r?\n", text.strip()):
        lines = block.strip().splitlines()
        for i, line in enumerate(lines):
            mt = SRT_TIME.search(line)
            if mt:
                g = [int(x) for x in mt.groups()]
                a = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
                b = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
                body = " ".join(lines[i + 1:])
                body = html.unescape(TAG.sub("", body)).strip()
                cues.append((a, b, body))
                break
    return cues


def is_speech(body):
    if not body:
        return False
    if NONSPEECH.match(body):
        return False
    # Strip bracketed sound descriptions and speaker labels, then see
    # whether any words remain.
    rest = re.sub(r"\[[^\]]*\]|\([^)]*\)|\u266a[^\u266a]*\u266a|^[A-Z .'-]+:\s*", "", body)
    return bool(re.search(r"[A-Za-z]{2,}", rest))


def coverage(cues, n_sec, offset):
    cov = np.zeros(n_sec)
    for a, b, _ in cues:
        a, b = a + offset, b + offset
        if b <= 0 or a >= n_sec:
            continue
        a, b = max(0.0, a), min(float(n_sec), b)
        i0, i1 = int(np.floor(a)), int(np.ceil(b))
        for i in range(i0, min(i1, n_sec)):
            cov[i] += max(0.0, min(b, i + 1) - max(a, i))
    return np.clip(cov, 0, 1)


# ============================================================
# Per-second table
# ============================================================

f = pd.read_csv(args.frames)
e = pd.read_csv(args.events)
f["second"] = np.floor(f["time"]).astype(int)
g = f.groupby("second")

sec = pd.DataFrame({
    "rms_db": g["loudness_db"].apply(energy_mean_db),
    "center_db": g["center_db"].apply(energy_mean_db),
    "noncenter_db": g["noncenter_db"].apply(energy_mean_db),
    "barrage": g["barrage_score"].mean(),
    "drum": g["drum_score"].mean(),
    "harsh": g["harsh_score"].max(),
    "burden": g["burden"].mean(),
}).reset_index()
sec = sec.set_index("second").reindex(
    range(int(sec["second"].max()) + 1)).rename_axis("second").reset_index()
sec["center_adv"] = sec["center_db"] - sec["noncenter_db"]
n_sec = len(sec)
duration = float(f["time"].max())

level_mode = args.level
if level_mode == "auto":
    level_mode = "lufs" if args.film else "rms"

loud_summary = {}
if level_mode == "lufs":
    if not args.film:
        raise SystemExit("--level lufs needs --film")
    ldf, loud_summary = bs1770(args.film)
    ldf["second"] = np.floor(ldf["time"] - 1e-6).astype(int)
    lufs_sec = ldf.groupby("second")["momentary"].apply(energy_mean_db)
    sec["lufs"] = sec["second"].map(lufs_sec)
    sec["level_db"] = sec["lufs"]
    floor = args.lufs_floor
    unit = "LUFS"
else:
    sec["level_db"] = sec["rms_db"]
    floor = args.gate_floor
    unit = "dBFS"

sec["audible"] = sec["level_db"] > floor


# ============================================================
# Dialogue references
# ============================================================

candidate = sec["audible"] & (sec["center_adv"] >= args.center_adv)
cap = (np.percentile(sec.loc[candidate, "barrage"], args.dialogue_barrage_pct)
       if candidate.any() else -np.inf)
proxy = candidate & (sec["barrage"] <= cap)
sec["dialogue_proxy"] = proxy
D_proxy = float(sec.loc[proxy, "level_db"].median()) if proxy.sum() >= 30 else float("nan")

sub = {"available": False}
if args.subtitles and Path(args.subtitles).exists():
    cues_all = parse_srt(args.subtitles)
    cues = [c for c in cues_all if is_speech(c[2])]

    centre_dom = (sec["audible"] & (sec["center_adv"] >= args.center_adv)
                  ).to_numpy().astype(float)

    def corr_at(off):
        c = coverage(cues, n_sec, off)
        if c.std() == 0 or centre_dom.std() == 0:
            return 0.0
        return float(np.corrcoef(c, centre_dom)[0, 1])

    r0 = corr_at(0.0)
    if args.sub_offset == "auto":
        lags = np.arange(-30.0, 30.5, 0.5)
        rs = [corr_at(x) for x in lags]
        best = float(lags[int(np.argmax(rs))])
        rbest = float(max(rs))
        offset = best if (rbest - r0) > 0.1 * max(abs(r0), 1e-3) and abs(best) >= 0.5 else 0.0
    else:
        offset = float(args.sub_offset)
        rbest = corr_at(offset)
    cov = coverage(cues, n_sec, offset)
    sec["sub_coverage"] = cov
    sub_sec = sec["audible"] & (cov >= 0.5)
    sec["dialogue_sub"] = sub_sec

    D_sub = float(sec.loc[sub_sec, "level_db"].median()) if sub_sec.sum() >= 30 else float("nan")
    capped = sub_sec & (sec["barrage"] <= np.percentile(
        sec.loc[sub_sec, "barrage"], 75)) if sub_sec.any() else sub_sec
    D_sub_capped = float(sec.loc[capped, "level_db"].median()) if capped.sum() >= 30 else float("nan")

    tp = int((proxy & sub_sec).sum())
    sub.update({
        "available": True,
        "cues_total": len(cues_all),
        "cues_speech": len(cues),
        "cues_nonspeech": len(cues_all) - len(cues),
        "offset_s": offset,
        "corr_at_zero": r0,
        "corr_at_offset": rbest if args.sub_offset == "auto" else corr_at(offset),
        "seconds": int(sub_sec.sum()),
        "D": D_sub,
        "D_capped": D_sub_capped,
        "proxy_precision": tp / max(1, int(proxy.sum())),
        "proxy_recall": tp / max(1, int(sub_sec.sum())),
    })
else:
    sec["sub_coverage"] = 0.0
    sec["dialogue_sub"] = False

ref = args.reference
if ref == "auto":
    ref = "subtitles" if sub["available"] and np.isfinite(sub.get("D", np.nan)) else "proxy"
if ref == "subtitles":
    D = sub["D"]
    D_source = "subtitle-defined dialogue seconds"
    dialogue = sec["dialogue_sub"]
else:
    D = D_proxy
    D_source = "centre-channel proxy"
    dialogue = sec["dialogue_proxy"]
fallback = not np.isfinite(D)
if fallback:
    D = float(sec.loc[sec["audible"], "level_db"].median())
    D_source = "all audible seconds (too few dialogue seconds)"

D_center = float(sec.loc[dialogue, "center_db"].median()) if dialogue.any() else float("nan")

rel = sec["level_db"] - D
sec["rel_db"] = rel
aud_rel = rel[sec["audible"]].dropna()
exceed = {k: float(np.mean(aud_rel >= k)) for k in (5, 10, 15, 20)}
p95 = float(np.percentile(aud_rel, 95))
p99 = float(np.percentile(aud_rel, 99))


# ============================================================
# Occupation blocks
# ============================================================

occ = (rel >= args.delta).fillna(False).to_numpy()
sec["occupied"] = occ
occ_runs = [(int(sec["second"][a]), int(sec["second"][b - 1]) + 1) for a, b in runs(occ)]
occ_merged = merge(occ_runs, args.merge_gap)
occ_blocks = [(a, b) for a, b in occ_merged if b - a >= args.min_block]

in_block = np.zeros(n_sec, dtype=bool)
for a, b in occ_blocks:
    in_block[a:b] = True
sec["in_block"] = in_block

block_rows = []
for a, b in occ_blocks:
    r = rel.iloc[a:b].dropna()
    block_rows.append({
        "start": float(a), "end": float(b), "duration": float(b - a),
        "occupied_share": float(np.mean(r >= args.delta)),
        "median_rel": float(np.median(r)),
        "p95_rel": float(np.percentile(r, 95)),
        "implied_throttle_db": float(max(0.0, np.percentile(r, 95) - args.delta)),
        "sub_seconds": int(sec["dialogue_sub"].iloc[a:b].sum()),
    })

# Dialogue exposed to throttling: subtitled speech inside blocks.
sub_in_blocks = int((sec["dialogue_sub"] & in_block).sum())
sub_share_in_blocks = (sub_in_blocks / max(1, sub.get("seconds", 0))
                       if sub["available"] else float("nan"))


# ============================================================
# Transient-defined blocks
# ============================================================

bar = e[e["type"] == "BARRAGE"]
bar_merged = merge(list(zip(bar["start_seconds"], bar["end_seconds"])), args.merge_gap)
bar_blocks = [(a, b) for a, b in bar_merged if b - a >= args.min_block]


# ============================================================
# Recovery
# ============================================================

rec = e[e["type"] == "RECOVERY"].sort_values("start_seconds")
gaps, prev = [], 0.0
for _, r in rec.iterrows():
    if r["start_seconds"] > prev:
        gaps.append((prev, r["start_seconds"]))
    prev = r["end_seconds"]
if prev < duration:
    gaps.append((prev, duration))
gaps.sort(key=lambda x: x[1] - x[0], reverse=True)

calm = ((rel <= args.recovery_margin) | ~sec["audible"]).fillna(True).to_numpy()
abs_windows = [(int(sec["second"][a]), int(sec["second"][b - 1]) + 1)
               for a, b in runs(calm) if b - a >= args.recovery_width]
abs_gaps, prev = [], 0.0
for a, b in abs_windows:
    if a > prev:
        abs_gaps.append((prev, a))
    prev = b
if prev < duration:
    abs_gaps.append((prev, duration))
abs_gaps.sort(key=lambda x: x[1] - x[0], reverse=True)
abs_share = sum(b - a for a, b in abs_windows) / max(1.0, duration)

in_window = np.zeros(n_sec, dtype=bool)
for a, b in abs_windows:
    in_window[a:b] = True
excess = np.nan_to_num(np.maximum(0.0, rel.to_numpy() - args.delta))
debt, k = np.zeros(n_sec), 0.0
for i in range(n_sec):
    k = 0.0 if in_window[i] else k + excess[i]
    debt[i] = k
sec["recovery_debt"] = debt


# ============================================================
# Swells
# ============================================================

sw = e[e["type"] == "SWELL"].copy()
lvl = sec.set_index("second")["level_db"]
sw["start_level"] = sw["start_seconds"].map(lambda t: float(lvl.get(int(t), np.nan)))
sw["end_level"] = sw["end_seconds"].map(lambda t: float(lvl.get(int(t), np.nan)))
quiet_start = floor + 5
swell_n = len(sw)
swell_from_quiet = int((sw["start_level"] < quiet_start).sum())
swell_into_occ = int((sw["end_level"] >= D + args.delta).sum())
swell_large = int((sw["score"] >= 20).sum())

swell_active = np.zeros(n_sec, dtype=bool)
for _, r in sw.iterrows():
    swell_active[int(r["start_seconds"]):int(r["end_seconds"]) + 1] = True


# ============================================================
# Overdetermination: raw and residualised on level
# ============================================================

aud = sec["audible"].fillna(False).to_numpy()
z = args.channel_z
chan = {"barrage": sec["barrage"].to_numpy(),
        "drum": sec["drum"].to_numpy(),
        "harsh": sec["harsh"].to_numpy()}

raw_elev = {c: np.nan_to_num(v) > z for c, v in chan.items()}

resid_elev = {}
L = sec["level_db"].to_numpy()
for c, v in chan.items():
    ok = aud & np.isfinite(v) & np.isfinite(L)
    coef = np.polyfit(L[ok], v[ok], 2) if ok.sum() > 10 else np.zeros(3)
    res = v - np.polyval(coef, L)
    # Scale by the channel's own spread, not the residual's, so that
    # "elevated beyond what level predicts" is measured in the same
    # units as the raw threshold.
    # A channel counts in the residualised index only if it is elevated
    # on the raw scale AND at least half that elevation remains after
    # removing what level predicts. This keeps omega_resid <= omega.
    s = robust_scale(v[ok])
    resid_elev[c] = raw_elev[c] & (np.nan_to_num(res / s) > z / 2)

exc = np.nan_to_num(rel.to_numpy(), nan=-99) >= args.delta
omega = exc.astype(int) + swell_active.astype(int) + sum(x.astype(int) for x in raw_elev.values())
omega_r = exc.astype(int) + swell_active.astype(int) + sum(x.astype(int) for x in resid_elev.values())
sec["omega"] = omega
sec["omega_resid"] = omega_r


def mean_on(x, m):
    return float(x[m].mean()) if m.any() else float("nan")


def share_on(x, m, k=3):
    return float(np.mean(x[m] >= k)) if m.any() else float("nan")


om = {
    "raw_in": mean_on(omega, in_block & aud), "raw_out": mean_on(omega, ~in_block & aud),
    "raw_three": share_on(omega, aud), "raw_three_in": share_on(omega, in_block & aud),
    "res_in": mean_on(omega_r, in_block & aud), "res_out": mean_on(omega_r, ~in_block & aud),
    "res_three": share_on(omega_r, aud), "res_three_in": share_on(omega_r, in_block & aud),
}


# ============================================================
# Figures
# ============================================================

minutes = sec["second"] / 60

fig, ax = plt.subplots(figsize=(12, 4.4))
for a, b in occ_blocks:
    ax.axvspan(a / 60, b / 60, color="tab:red", alpha=0.18, lw=0)
ax.plot(minutes, sec["level_db"], lw=0.6, color="0.25")
ax.axhline(D, color="tab:blue", lw=1, label=f"dialogue reference {D:.1f} {unit}")
ax.axhline(D + args.delta, color="tab:red", lw=1, ls="--",
           label=f"reference + {args.delta:.0f} dB")
lo = np.nanmax([np.nanmin(sec["level_db"]) - 2, floor - 15])
hi = np.nanmax(sec["level_db"]) + 3
if sub["available"]:
    subm = sec["dialogue_sub"].to_numpy()
    ax.vlines(minutes[subm], lo, lo + 0.04 * (hi - lo), color="tab:blue",
              lw=0.3, label="subtitled speech")
ax.set_ylim(lo, hi)
ax.set_xlabel("Film time (minutes)")
ax.set_ylabel(f"Per-second level ({unit})")
ax.legend(loc="upper left", fontsize=7, ncol=3)
fig.tight_layout()
fig.savefig(out / "fig-occupation.png", dpi=200)
plt.close(fig)

plt.figure(figsize=(7, 3.5))
plt.hist(aud_rel, bins=np.arange(-40, 31, 1), color="0.45")
plt.axvline(0, color="tab:blue", lw=1)
plt.axvline(args.delta, color="tab:red", lw=1)
plt.xlabel("Per-second level minus dialogue reference (dB)")
plt.ylabel("Seconds")
plt.tight_layout()
plt.savefig(out / "fig-exceedance.png", dpi=200)
plt.close()

plt.figure(figsize=(12, 2.4))
for a, b in occ_merged:
    plt.plot([a / 60, b / 60], [1, 1], lw=8, solid_capstyle="butt",
             color="tab:red" if b - a >= args.min_block else "tab:pink")
for a, b in bar_merged:
    plt.plot([a / 60, b / 60], [0, 0], lw=8, solid_capstyle="butt",
             color="tab:green" if b - a >= args.min_block else "tab:olive")
plt.yticks([0, 1], ["transient-defined", "level-defined"])
plt.ylim(-0.7, 1.7)
plt.xlim(0, duration / 60)
plt.xlabel("Film time (minutes)")
plt.tight_layout()
plt.savefig(out / "fig-blocks.png", dpi=200)
plt.close()

sec.to_csv(out / "seconds.csv", index=False)


# ============================================================
# Results
# ============================================================

res = {
    "level_measure": level_mode, "unit": unit, "loudness": loud_summary,
    "dialogue_reference": D, "dialogue_reference_source": D_source,
    "dialogue_reference_proxy": D_proxy, "dialogue_proxy_seconds": int(proxy.sum()),
    "subtitles": sub, "dialogue_center_dbfs": D_center,
    "delta_db": args.delta, "exceed": exceed, "p95_rel": p95, "p99_rel": p99,
    "occupation_blocks": block_rows,
    "barrage_blocks": [{"start": a, "end": b} for a, b in bar_blocks],
    "recovery_gaps_top5": [{"start": a, "end": b} for a, b in gaps[:5]],
    "abs_recovery_windows": len(abs_windows), "abs_recovery_share": abs_share,
    "abs_gaps_top5": [{"start": a, "end": b} for a, b in abs_gaps[:5]],
    "max_recovery_debt": float(debt.max()),
    "subtitled_seconds_in_blocks": sub_in_blocks,
    "subtitled_share_in_blocks": sub_share_in_blocks,
    "swell": {"n": swell_n, "from_quiet": swell_from_quiet,
              "into_occupied": swell_into_occ, "large": swell_large},
    "omega": om,
}
(out / "occupation.json").write_text(json.dumps(res, indent=2, default=float))


def fmt(x, spec=".1f", none="--"):
    return format(x, spec) if isinstance(x, (int, float)) and np.isfinite(x) else none


occ_rows = " \\\\\n".join(
    f"{ts(r['start'])} & {ts(r['end'])} & {r['duration'] / 60:.1f} & "
    f"{r['median_rel']:+.1f} & {r['p95_rel']:+.1f} & {r['implied_throttle_db']:.1f}"
    + (f" & {r['sub_seconds']}" if sub["available"] else " & --")
    for r in block_rows) or "\\multicolumn{7}{c}{none at these settings}"
abs_rows = " \\\\\n".join(f"{ts(a)} & {ts(b)} & {(b - a) / 60:.1f}"
                         for a, b in abs_gaps[:5]) or "\\multicolumn{3}{c}{none}"
gap_rows = " \\\\\n".join(f"{ts(a)} & {ts(b)} & {(b - a) / 60:.1f}"
                         for a, b in gaps[:5]) or "\\multicolumn{3}{c}{none}"
longest = max(block_rows, key=lambda r: r["duration"]) if block_rows else None
thr = [r["implied_throttle_db"] for r in block_rows]

macros = {
    "resRun": "yes",
    "resLevelUnit": unit,
    "resLevelMeasure": ("BS.1770 momentary loudness, energy-averaged per second"
                        if level_mode == "lufs" else
                        "unweighted RMS of the mono downmix, energy-averaged per second"),
    "resLoudnessRun": "yes" if level_mode == "lufs" else "no",
    "resIntegrated": fmt(loud_summary.get("integrated_lufs", float("nan"))),
    "resLRA": fmt(loud_summary.get("lra_lu", float("nan"))),
    "resLRALow": fmt(loud_summary.get("lra_low", float("nan"))),
    "resLRAHigh": fmt(loud_summary.get("lra_high", float("nan"))),
    "resSubRun": "yes" if sub["available"] else "no",
    "resSubCues": str(sub.get("cues_total", "--")),
    "resSubSpeechCues": str(sub.get("cues_speech", "--")),
    "resSubNonspeechCues": str(sub.get("cues_nonspeech", "--")),
    "resSubOffset": fmt(sub.get("offset_s", float("nan")), "+.1f"),
    "resSubSeconds": str(sub.get("seconds", "--")),
    "resSubCorrZero": fmt(sub.get("corr_at_zero", float("nan")), ".2f"),
    "resSubCorrOffset": fmt(sub.get("corr_at_offset", float("nan")), ".2f"),
    "resDialogueRefSub": fmt(sub.get("D", float("nan"))),
    "resDialogueRefSubCapped": fmt(sub.get("D_capped", float("nan"))),
    "resDialogueRefProxy": fmt(D_proxy),
    "resProxySeconds": str(int(proxy.sum())),
    "resProxyPrecision": pct(sub.get("proxy_precision", float("nan"))),
    "resProxyRecall": pct(sub.get("proxy_recall", float("nan"))),
    "resDialogueSource": D_source,
    "resDialogueRef": fmt(D),
    "resDialogueFallback": "yes" if fallback else "no",
    "resDialogueCenter": fmt(D_center),
    "resDialogueSeconds": str(int(dialogue.sum())),
    "resDialogueShare": pct(dialogue.sum() / n_sec),
    "resDelta": f"{args.delta:.0f}",
    "resMergeGap": f"{args.merge_gap:.0f}",
    "resMinBlock": f"{args.min_block:.0f}",
    "resExceedFive": pct(exceed[5]),
    "resExceedTen": pct(exceed[10]),
    "resExceedFifteen": pct(exceed[15]),
    "resExceedTwenty": pct(exceed[20]),
    "resPNinetyFive": f"{p95:+.1f}",
    "resPNinetyNine": f"{p99:+.1f}",
    "resOccBlocksN": str(len(block_rows)),
    "resOccTotalMin": f"{sum(r['duration'] for r in block_rows) / 60:.1f}",
    "resOccLongestMin": f"{longest['duration'] / 60:.1f}" if longest else "0",
    "resOccLongestStart": ts(longest["start"]) if longest else "--",
    "resThrottleMedian": f"{np.median(thr):.1f}" if thr else "0",
    "resThrottleMax": f"{max(thr):.1f}" if thr else "0",
    "resSubInBlocks": str(sub_in_blocks) if sub["available"] else "--",
    "resSubInBlocksShare": pct(sub_share_in_blocks),
    "resBarrageBlocksN": str(len(bar_blocks)),
    "resBarrageLongestMin": f"{max(b - a for a, b in bar_blocks) / 60:.1f}" if bar_blocks else "0",
    "resRecoveryGapLongestMin": f"{(gaps[0][1] - gaps[0][0]) / 60:.1f}" if gaps else "0",
    "resRecoveryGapLongestStart": ts(gaps[0][0]) if gaps else "--",
    "resAbsRecoveryN": str(len(abs_windows)),
    "resAbsRecoveryShare": pct(abs_share),
    "resAbsGapLongestMin": f"{(abs_gaps[0][1] - abs_gaps[0][0]) / 60:.1f}" if abs_gaps else "0",
    "resAbsGapLongestStart": ts(abs_gaps[0][0]) if abs_gaps else "--",
    "resDebtMax": f"{debt.max():.0f}",
    "resSwellN": str(swell_n),
    "resSwellFromQuiet": str(swell_from_quiet),
    "resSwellQuietLevel": f"{quiet_start:.0f}",
    "resSwellIntoOcc": str(swell_into_occ),
    "resSwellLarge": str(swell_large),
    "resOmegaIn": fmt(om["raw_in"], ".2f"),
    "resOmegaOut": fmt(om["raw_out"], ".2f"),
    "resOmegaThreeShare": pct(om["raw_three"]),
    "resOmegaThreeShareIn": pct(om["raw_three_in"]),
    "resOmegaResIn": fmt(om["res_in"], ".2f"),
    "resOmegaResOut": fmt(om["res_out"], ".2f"),
    "resOmegaResThreeShare": pct(om["res_three"]),
    "resOmegaResThreeShareIn": pct(om["res_three_in"]),
    "resOccRows": occ_rows,
    "resAbsGapRows": abs_rows,
    "resGapRows": gap_rows,
}

with open(out / "results.tex", "w") as fh:
    fh.write("% Generated by occupation.py v2. Do not edit by hand.\n")
    for k, v in macros.items():
        fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")

print(f"Level: {macros['resLevelMeasure']}")
if loud_summary:
    print(f"Integrated {macros['resIntegrated']} LUFS, LRA {macros['resLRA']} LU")
if sub["available"]:
    print(f"Subtitles: {sub['cues_speech']} speech cues of {sub['cues_total']}, "
          f"offset {sub['offset_s']:+.1f} s, {sub['seconds']} subtitled seconds")
    print(f"Proxy vs subtitles: precision {macros['resProxyPrecision']}, "
          f"recall {macros['resProxyRecall']}; D proxy {macros['resDialogueRefProxy']}, "
          f"D subtitles {macros['resDialogueRefSub']}")
print(f"Dialogue reference: {D:.1f} {unit} from {D_source}")
print(f"Audible seconds >= reference + {args.delta:.0f} dB: {macros['resExceedTen']}")
print(f"Occupation blocks >= {args.min_block:.0f} s: {len(block_rows)}")
for r in block_rows:
    print(f"  {ts(r['start'])}-{ts(r['end'])}  {r['duration'] / 60:.1f} min  "
          f"p95 {r['p95_rel']:+.1f} dB  throttle {r['implied_throttle_db']:.1f} dB  "
          f"subtitled s {r['sub_seconds']}")
if sub["available"]:
    print(f"Subtitled speech inside blocks: {sub_in_blocks} s ({macros['resSubInBlocksShare']})")
print(f"Longest absolute recovery gap: {macros['resAbsGapLongestMin']} min "
      f"from {macros['resAbsGapLongestStart']}")
print(f"Omega in/out blocks: raw {macros['resOmegaIn']}/{macros['resOmegaOut']}, "
      f"residualised {macros['resOmegaResIn']}/{macros['resOmegaResOut']}")
print("Wrote", out)
