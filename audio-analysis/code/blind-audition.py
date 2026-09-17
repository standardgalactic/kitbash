#!/usr/bin/env python3
"""
blind-audition.py
=================

Prepares a blinded annotation set from the audition clips written by
analyze-soundtrack-v3.1.

  * copies every detector clip under a random identifier
  * cuts N random control clips from audible parts of the film
  * shuffles everything into one folder with one playlist
  * writes sheet.csv (what the annotator sees) and key.csv (what the
    annotator must not see until labelling is finished)

After labelling, join sheet.csv to key.csv on `clip` and pass the
result to analyze-soundtrack-v3.1 with --annotations, or analyse it
directly. The key has a `category` column in which controls appear as
RANDOM_CONTROL.
"""

import argparse
import random
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("input", help="the film (needed to cut control clips)")
p.add_argument("--audition", required=True, help="audition/ folder from v3.1")
p.add_argument("--frames", required=True, help="frames.csv from v3.1")
p.add_argument("--out", default="blind")
p.add_argument("--controls", type=int, default=40)
p.add_argument("--length", type=float, default=20.0)
p.add_argument("--gate-floor", type=float, default=-65.0)
p.add_argument("--audio-stream", default="0:a:0")
p.add_argument("--seed", type=int, default=None)
args = p.parse_args()

rng = random.Random(args.seed)
aud = Path(args.audition)
out = Path(args.out)
(out / "clips").mkdir(parents=True, exist_ok=True)

ann = pd.read_csv(aud / "annotations.csv")
f = pd.read_csv(args.frames, usecols=["time", "loudness_db"])
duration = float(f["time"].max())

# Control windows: uniformly placed, centre second audible, not
# overlapping any detector clip window by more than half its length.
f["second"] = np.floor(f["time"]).astype(int)
audible = set(f.loc[f["loudness_db"] > args.gate_floor, "second"])
taken = [(r["event_seconds"] - r["event_offset_in_clip"],
          r["event_seconds"] - r["event_offset_in_clip"] + args.length)
         for _, r in ann.iterrows()]

controls = []
tries = 0
while len(controls) < args.controls and tries < 100000:
    tries += 1
    a = rng.uniform(0, max(0.0, duration - args.length))
    if int(a + args.length / 2) not in audible:
        continue
    if any(min(b, a + args.length) - max(x, a) > args.length / 2
           for x, b in taken + controls):
        continue
    controls.append((a, a + args.length))

ids = rng.sample(range(10000, 100000), len(ann) + len(controls))
sheet, key = [], []

for (_, r), cid in zip(ann.iterrows(), ids):
    name = f"{cid}.mp3"
    shutil.copyfile(aud / r["clip"], out / "clips" / name)
    key.append({"clip": name, "category": r["category"], "rank": r["rank"],
                "event_seconds": r["event_seconds"], "score": r["score"]})

for (a, b), cid in zip(controls, ids[len(ann):]):
    name = f"{cid}.mp3"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", f"{a:.3f}", "-i", args.input, "-t", f"{b - a:.3f}",
                    "-map", args.audio_stream, "-vn", "-ac", "2",
                    "-c:a", "libmp3lame", "-q:a", "4",
                    str(out / "clips" / name)], check=True)
    key.append({"clip": name, "category": "RANDOM_CONTROL", "rank": "",
                "event_seconds": round(a + args.length / 2, 2), "score": ""})

rng.shuffle(key)
for k in key:
    sheet.append({"clip": k["clip"], "label": "", "role": "", "intensity": "",
                  "would_reduce": "", "notes": ""})

pd.DataFrame(sheet).to_csv(out / "sheet.csv", index=False)
pd.DataFrame(key).to_csv(out / "key.csv", index=False)
(out / "playlist.m3u").write_text(
    "\n".join(f"clips/{s['clip']}" for s in sheet) + "\n")

print(f"{len(ann)} detector clips + {len(controls)} controls -> {out}")
print("Give the annotator sheet.csv, playlist.m3u and clips/. Keep key.csv aside.")
