#!/usr/bin/env python3

import argparse
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d


def timestamp(seconds):
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"


parser = argparse.ArgumentParser()
parser.add_argument("audio")
parser.add_argument("--sr", type=int, default=22050)
parser.add_argument("--hop", type=int, default=512)
parser.add_argument("--out", default="sound-analysis")
args = parser.parse_args()

audio_path = Path(args.audio)
out = Path(args.out)
out.mkdir(exist_ok=True)

print("Loading:", audio_path)
y, sr = librosa.load(audio_path, sr=args.sr, mono=True)
duration = len(y) / sr

print(f"Duration: {timestamp(duration)}")
print(f"Samples:  {len(y):,}")
print(f"Rate:     {sr:,} Hz")

# ------------------------------------------------------------
# FRAME FEATURES
# ------------------------------------------------------------

hop = args.hop

rms = librosa.feature.rms(y=y, hop_length=hop)[0]
rms_db = librosa.amplitude_to_db(rms, ref=np.max)

centroid = librosa.feature.spectral_centroid(
    y=y, sr=sr, hop_length=hop
)[0]

bandwidth = librosa.feature.spectral_bandwidth(
    y=y, sr=sr, hop_length=hop
)[0]

zcr = librosa.feature.zero_crossing_rate(
    y, hop_length=hop
)[0]

onset = librosa.onset.onset_strength(
    y=y, sr=sr, hop_length=hop
)

times = librosa.frames_to_time(
    np.arange(len(rms)), sr=sr, hop_length=hop
)

# Align arrays.
n = min(
    len(times),
    len(rms_db),
    len(centroid),
    len(bandwidth),
    len(zcr),
    len(onset),
)

times = times[:n]
rms_db = rms_db[:n]
centroid = centroid[:n]
bandwidth = bandwidth[:n]
zcr = zcr[:n]
onset = onset[:n]

# ------------------------------------------------------------
# NORMALIZATION
# ------------------------------------------------------------

def robust_z(x):
    median = np.median(x)
    mad = np.median(np.abs(x - median)) + 1e-9
    return (x - median) / (1.4826 * mad)


z_loud = robust_z(rms_db)
z_onset = robust_z(onset)
z_centroid = robust_z(centroid)
z_bw = robust_z(bandwidth)
z_zcr = robust_z(zcr)

# ------------------------------------------------------------
# EVENT SCORES
#
# These are candidate detectors, NOT semantic classifiers.
# ------------------------------------------------------------

# Sharp impacts: gunshots, punches, crashes, slammed objects, etc.
impact_score = (
    0.50 * z_onset +
    0.25 * z_loud +
    0.15 * z_centroid +
    0.10 * z_bw
)

# Harsh/noisy sustained material: screaming, crashes, sirens,
# distorted effects, dense action sequences.
harsh_score = (
    0.35 * z_loud +
    0.25 * z_centroid +
    0.20 * z_bw +
    0.20 * z_zcr
)

# Musical / dramatic build candidate:
# smoothed rise in loudness plus onset density.
smooth_loud = gaussian_filter1d(rms_db, sigma=20)
smooth_onset = gaussian_filter1d(onset, sigma=20)

rise = np.gradient(smooth_loud)
z_rise = robust_z(rise)
z_smooth_onset = robust_z(smooth_onset)

swell_score = (
    0.55 * z_rise +
    0.25 * robust_z(smooth_loud) +
    0.20 * z_smooth_onset
)

# General acoustic-load score.
load_score = (
    0.30 * z_loud +
    0.30 * z_onset +
    0.15 * z_centroid +
    0.15 * z_bw +
    0.10 * z_zcr
)

# ------------------------------------------------------------
# FIND PEAK CANDIDATES
# ------------------------------------------------------------

def candidate_peaks(score, percentile, min_gap_seconds):
    threshold = np.percentile(score, percentile)

    peaks = librosa.util.peak_pick(
        score,
        pre_max=max(1, int(0.25 * sr / hop)),
        post_max=max(1, int(0.25 * sr / hop)),
        pre_avg=max(1, int(0.5 * sr / hop)),
        post_avg=max(1, int(0.5 * sr / hop)),
        delta=0.0,
        wait=max(1, int(min_gap_seconds * sr / hop)),
    )

    return [
        p for p in peaks
        if p < len(score) and score[p] >= threshold
    ]


impact_peaks = candidate_peaks(impact_score, 98.5, 1.0)
harsh_peaks = candidate_peaks(harsh_score, 99.0, 3.0)
swell_peaks = candidate_peaks(swell_score, 98.5, 5.0)
load_peaks = candidate_peaks(load_score, 99.0, 5.0)

events = []

def add_events(label, score, peaks):
    for p in peaks:
        events.append({
            "time_seconds": times[p],
            "timestamp": timestamp(times[p]),
            "candidate": label,
            "score": float(score[p]),
            "rms_db": float(rms_db[p]),
            "onset_strength": float(onset[p]),
            "spectral_centroid_hz": float(centroid[p]),
            "bandwidth_hz": float(bandwidth[p]),
            "zcr": float(zcr[p]),
        })


add_events("IMPACT", impact_score, impact_peaks)
add_events("HARSH", harsh_score, harsh_peaks)
add_events("SWELL", swell_score, swell_peaks)
add_events("HIGH_LOAD", load_score, load_peaks)

df = pd.DataFrame(events)
df = df.sort_values("time_seconds")
df.to_csv(out / "candidate-events.csv", index=False)

print()
print("Candidates:")
print(df["candidate"].value_counts().to_string())

# ------------------------------------------------------------
# SECOND-BY-SECOND LOAD
# ------------------------------------------------------------

seconds = np.floor(times).astype(int)

frame_df = pd.DataFrame({
    "second": seconds,
    "rms_db": rms_db,
    "onset": onset,
    "impact": impact_score,
    "harsh": harsh_score,
    "swell": swell_score,
    "load": load_score,
})

sec = frame_df.groupby("second").mean().reset_index()
sec["timestamp"] = sec["second"].map(timestamp)
sec.to_csv(out / "second-by-second.csv", index=False)

# ------------------------------------------------------------
# PLOTS
# ------------------------------------------------------------

plt.figure(figsize=(16, 5))
plt.plot(times / 60, rms_db)
plt.xlabel("Movie time (minutes)")
plt.ylabel("Relative loudness (dB)")
plt.title("Drive Through Fire — Loudness")
plt.tight_layout()
plt.savefig(out / "loudness.png", dpi=160)
plt.close()

plt.figure(figsize=(16, 5))
plt.plot(times / 60, onset)
plt.xlabel("Movie time (minutes)")
plt.ylabel("Onset strength")
plt.title("Drive Through Fire — Acoustic Transients")
plt.tight_layout()
plt.savefig(out / "transients.png", dpi=160)
plt.close()

plt.figure(figsize=(16, 5))
plt.plot(times / 60, load_score)
plt.xlabel("Movie time (minutes)")
plt.ylabel("Acoustic load")
plt.title("Drive Through Fire — Acoustic Load")
plt.tight_layout()
plt.savefig(out / "acoustic-load.png", dpi=160)
plt.close()

plt.figure(figsize=(16, 5))
plt.plot(times / 60, swell_score)
plt.xlabel("Movie time (minutes)")
plt.ylabel("Swell score")
plt.title("Drive Through Fire — Dramatic Swell Candidates")
plt.tight_layout()
plt.savefig(out / "swell-candidates.png", dpi=160)
plt.close()

print()
print("Written:")
for f in sorted(out.iterdir()):
    print(" ", f)
