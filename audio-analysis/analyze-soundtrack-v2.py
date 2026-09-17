#!/usr/bin/env python3

"""
Soundtrack structural analysis v2

Designed for detecting:
  - broadband impacts
  - transient barrages
  - low-frequency rhythmic/drum activity
  - gradual dramatic swells
  - sustained harsh/noisy passages
  - acoustic recovery intervals
  - multichannel center-vs-surround activity

This is an acoustic candidate detector, not a semantic classifier.
It does NOT claim that a transient is specifically a gunshot, punch, etc.
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

import librosa
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import soundfile as sf

from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks


# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def timestamp(seconds):
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def robust_z(x):
    x = np.asarray(x, dtype=float)

    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med))

    if mad < 1e-9:
        return np.zeros_like(x)

    return (x - med) / (1.4826 * mad)


def normalize01(x):
    x = np.asarray(x, dtype=float)
    lo = np.nanpercentile(x, 5)
    hi = np.nanpercentile(x, 95)

    if hi <= lo:
        return np.zeros_like(x)

    return np.clip((x - lo) / (hi - lo), 0, 1)


def contiguous_regions(mask, times, minimum_duration=1.0):
    """
    Convert a boolean frame mask into start/end regions.
    """
    mask = np.asarray(mask, dtype=bool)

    if not np.any(mask):
        return []

    changes = np.diff(mask.astype(int))

    starts = list(np.where(changes == 1)[0] + 1)
    ends = list(np.where(changes == -1)[0] + 1)

    if mask[0]:
        starts.insert(0, 0)

    if mask[-1]:
        ends.append(len(mask))

    regions = []

    for start, end in zip(starts, ends):
        t0 = times[start]
        t1 = times[min(end - 1, len(times) - 1)]

        if t1 - t0 >= minimum_duration:
            regions.append((start, end, t0, t1))

    return regions


# ------------------------------------------------------------
# Arguments
# ------------------------------------------------------------

parser = argparse.ArgumentParser()

parser.add_argument("input")
parser.add_argument("--out", default="sound-analysis-v2")
parser.add_argument("--sr", type=int, default=24000)
parser.add_argument("--hop", type=int, default=512)
parser.add_argument(
    "--audio-stream",
    default="0:a:0",
    help="ffmpeg audio stream selector, default 0:a:0"
)

args = parser.parse_args()

source = Path(args.input)
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)

sr = args.sr
hop = args.hop


# ------------------------------------------------------------
# Extract multichannel PCM from the source
# ------------------------------------------------------------

print("Extracting multichannel audio...")

with tempfile.TemporaryDirectory() as td:
    wav = Path(td) / "analysis.wav"

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(source),
        "-map", args.audio_stream,
        "-vn",
        "-acodec", "pcm_f32le",
        "-ar", str(sr),
        str(wav),
    ]

    subprocess.run(cmd, check=True)

    audio, file_sr = sf.read(
        wav,
        dtype="float32",
        always_2d=True
    )

sr = file_sr

samples, channels = audio.shape
duration = samples / sr

print(f"Duration: {timestamp(duration)}")
print(f"Channels: {channels}")
print(f"Rate:     {sr} Hz")


# ------------------------------------------------------------
# Channel assumptions
#
# Typical 5.1 WAV order:
#
#   0 FL
#   1 FR
#   2 FC
#   3 LFE
#   4 SL/BL
#   5 SR/BR
#
# For stereo or other layouts we degrade gracefully.
# ------------------------------------------------------------

channel_names = []

if channels == 1:
    channel_names = ["M"]

elif channels == 2:
    channel_names = ["FL", "FR"]

elif channels == 6:
    channel_names = ["FL", "FR", "FC", "LFE", "SL", "SR"]

else:
    channel_names = [f"CH{i}" for i in range(channels)]

print("Channel interpretation:", ", ".join(channel_names))


# ------------------------------------------------------------
# Derived signals
# ------------------------------------------------------------

mono = np.mean(audio, axis=1)

if channels >= 3:
    center = audio[:, 2]
else:
    center = mono

if channels >= 6:
    front = np.mean(audio[:, [0, 1]], axis=1)
    lfe = audio[:, 3]
    surround = np.mean(audio[:, [4, 5]], axis=1)
else:
    front = mono
    lfe = mono
    surround = np.zeros_like(mono)


# ------------------------------------------------------------
# Frequency-separated signals
# ------------------------------------------------------------

def band_signal(y, low, high):
    """
    Reconstruct approximate frequency band using STFT masking.
    """
    D = librosa.stft(y, n_fft=2048, hop_length=hop)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    mask = (freqs >= low) & (freqs <= high)

    filtered = np.zeros_like(D)
    filtered[mask, :] = D[mask, :]

    return librosa.istft(
        filtered,
        hop_length=hop,
        length=len(y)
    )


print("Separating frequency bands...")

low_band = band_signal(front, 35, 250)
mid_band = band_signal(mono, 250, 3000)
high_band = band_signal(mono, 3000, 10000)


# ------------------------------------------------------------
# Feature extraction
# ------------------------------------------------------------

def rms_db(y):
    r = librosa.feature.rms(
        y=y,
        frame_length=2048,
        hop_length=hop
    )[0]

    return librosa.amplitude_to_db(
        np.maximum(r, 1e-10),
        ref=1.0
    )


mono_db = rms_db(mono)
center_db = rms_db(center)
front_db = rms_db(front)
low_db = rms_db(low_band)
mid_db = rms_db(mid_band)
high_db = rms_db(high_band)

if channels >= 6:
    lfe_db = rms_db(lfe)
    surround_db = rms_db(surround)
else:
    lfe_db = low_db.copy()
    surround_db = np.full_like(mono_db, -80.0)


onset_full = librosa.onset.onset_strength(
    y=mono,
    sr=sr,
    hop_length=hop
)

onset_low = librosa.onset.onset_strength(
    y=low_band,
    sr=sr,
    hop_length=hop
)

centroid = librosa.feature.spectral_centroid(
    y=mono,
    sr=sr,
    hop_length=hop
)[0]

flatness = librosa.feature.spectral_flatness(
    y=mono,
    hop_length=hop
)[0]

zcr = librosa.feature.zero_crossing_rate(
    mono,
    hop_length=hop
)[0]


# ------------------------------------------------------------
# Align everything
# ------------------------------------------------------------

features = [
    mono_db,
    center_db,
    front_db,
    low_db,
    mid_db,
    high_db,
    lfe_db,
    surround_db,
    onset_full,
    onset_low,
    centroid,
    flatness,
    zcr,
]

n = min(map(len, features))

features = [x[:n] for x in features]

(
    mono_db,
    center_db,
    front_db,
    low_db,
    mid_db,
    high_db,
    lfe_db,
    surround_db,
    onset_full,
    onset_low,
    centroid,
    flatness,
    zcr,
) = features

times = librosa.frames_to_time(
    np.arange(n),
    sr=sr,
    hop_length=hop
)


# ------------------------------------------------------------
# Activity measures
# ------------------------------------------------------------

z_loud = robust_z(mono_db)
z_low = robust_z(low_db)
z_lfe = robust_z(lfe_db)
z_high = robust_z(high_db)

z_onset = robust_z(onset_full)
z_low_onset = robust_z(onset_low)

z_centroid = robust_z(centroid)
z_flatness = robust_z(flatness)
z_zcr = robust_z(zcr)

center_advantage = center_db - (
    (front_db + surround_db) / 2
)

surround_advantage = surround_db - center_db


# ------------------------------------------------------------
# 1. Broadband impact score
# ------------------------------------------------------------

impact_score = (
    0.45 * z_onset +
    0.20 * z_loud +
    0.15 * z_centroid +
    0.10 * z_high +
    0.10 * z_flatness
)


# ------------------------------------------------------------
# 2. Harsh/noisy score
# ------------------------------------------------------------

harsh_score = (
    0.30 * z_high +
    0.25 * z_centroid +
    0.20 * z_flatness +
    0.15 * z_zcr +
    0.10 * z_loud
)


# ------------------------------------------------------------
# 3. Low-frequency percussion / drum score
#
# We want repeated LF onsets rather than one isolated explosion.
# ------------------------------------------------------------

frames_per_second = sr / hop

low_onset_positive = np.maximum(
    robust_z(onset_low),
    0
)

window_seconds = 4.0
window_frames = max(
    1,
    int(window_seconds * frames_per_second)
)

kernel = np.ones(window_frames) / window_frames

low_onset_density = np.convolve(
    low_onset_positive,
    kernel,
    mode="same"
)

drum_score = (
    0.45 * robust_z(low_onset_density) +
    0.30 * z_low +
    0.25 * z_lfe
)


# ------------------------------------------------------------
# 4. Gradual swell score
#
# Much slower than v1.
# Detect approximately 2-10 second energy ramps.
# ------------------------------------------------------------

smooth_sigma_seconds = 1.5
sigma_frames = smooth_sigma_seconds * frames_per_second

smooth_loud = gaussian_filter1d(
    mono_db,
    sigma=sigma_frames
)

swell_gradient = np.gradient(smooth_loud)

positive_gradient = np.maximum(
    swell_gradient,
    0
)

swell_score = gaussian_filter1d(
    robust_z(positive_gradient),
    sigma=frames_per_second * 0.75
)

# Penalize instantaneous transients.
swell_score -= 0.20 * np.maximum(z_onset, 0)


# ------------------------------------------------------------
# 5. Barrage / event-density score
# ------------------------------------------------------------

onset_positive = np.maximum(z_onset, 0)

barrage_window = max(
    1,
    int(5 * frames_per_second)
)

barrage_density = np.convolve(
    onset_positive,
    np.ones(barrage_window) / barrage_window,
    mode="same"
)

barrage_score = (
    0.50 * robust_z(barrage_density) +
    0.30 * z_loud +
    0.20 * z_high
)


# ------------------------------------------------------------
# 6. General acoustic burden
# ------------------------------------------------------------

burden = (
    0.25 * normalize01(mono_db) +
    0.20 * normalize01(onset_full) +
    0.15 * normalize01(low_onset_density) +
    0.15 * normalize01(high_db) +
    0.10 * normalize01(flatness) +
    0.15 * normalize01(barrage_density)
)


# ------------------------------------------------------------
# Candidate peak extraction
# ------------------------------------------------------------

def get_peaks(score, percentile=98, distance_seconds=2):
    threshold = np.percentile(score, percentile)

    peaks, _ = find_peaks(
        score,
        height=threshold,
        distance=max(
            1,
            int(distance_seconds * frames_per_second)
        )
    )

    return peaks


impact_peaks = get_peaks(
    impact_score,
    percentile=98.5,
    distance_seconds=0.75
)

swell_peaks = get_peaks(
    swell_score,
    percentile=97.5,
    distance_seconds=5
)

drum_peaks = get_peaks(
    drum_score,
    percentile=97.5,
    distance_seconds=4
)

harsh_peaks = get_peaks(
    harsh_score,
    percentile=98,
    distance_seconds=3
)


# ------------------------------------------------------------
# Sustained regions
# ------------------------------------------------------------

barrage_threshold = np.percentile(
    barrage_score,
    85
)

burden_threshold = np.percentile(
    burden,
    80
)

quiet_threshold = np.percentile(
    burden,
    25
)

barrage_regions = contiguous_regions(
    barrage_score > barrage_threshold,
    times,
    minimum_duration=3.0
)

high_load_regions = contiguous_regions(
    burden > burden_threshold,
    times,
    minimum_duration=4.0
)

recovery_regions = contiguous_regions(
    burden < quiet_threshold,
    times,
    minimum_duration=5.0
)


# ------------------------------------------------------------
# Event table
# ------------------------------------------------------------

events = []


def add_peak_events(label, score, peaks):
    for p in peaks:
        events.append({
            "type": label,
            "start_seconds": times[p],
            "end_seconds": times[p],
            "start": timestamp(times[p]),
            "end": timestamp(times[p]),
            "duration": 0.0,
            "score": float(score[p]),
            "loudness_db": float(mono_db[p]),
            "low_db": float(low_db[p]),
            "high_db": float(high_db[p]),
            "center_db": float(center_db[p]),
            "surround_db": float(surround_db[p]),
        })


def add_regions(label, score, regions):
    for start, end, t0, t1 in regions:
        section = score[start:end]

        events.append({
            "type": label,
            "start_seconds": t0,
            "end_seconds": t1,
            "start": timestamp(t0),
            "end": timestamp(t1),
            "duration": float(t1 - t0),
            "score": float(np.mean(section)),
            "loudness_db": float(
                np.mean(mono_db[start:end])
            ),
            "low_db": float(
                np.mean(low_db[start:end])
            ),
            "high_db": float(
                np.mean(high_db[start:end])
            ),
            "center_db": float(
                np.mean(center_db[start:end])
            ),
            "surround_db": float(
                np.mean(surround_db[start:end])
            ),
        })


add_peak_events(
    "IMPACT",
    impact_score,
    impact_peaks
)

add_peak_events(
    "SWELL",
    swell_score,
    swell_peaks
)

add_peak_events(
    "DRUM_RUN",
    drum_score,
    drum_peaks
)

add_peak_events(
    "HARSH",
    harsh_score,
    harsh_peaks
)

add_regions(
    "BARRAGE",
    barrage_score,
    barrage_regions
)

add_regions(
    "HIGH_LOAD",
    burden,
    high_load_regions
)

add_regions(
    "RECOVERY",
    -burden,
    recovery_regions
)


events_df = pd.DataFrame(events)

events_df = events_df.sort_values(
    ["start_seconds", "type"]
)

events_df.to_csv(
    out / "events.csv",
    index=False
)


# ------------------------------------------------------------
# Per-second structural data
# ------------------------------------------------------------

frame_df = pd.DataFrame({
    "time": times,
    "second": np.floor(times).astype(int),
    "loudness_db": mono_db,
    "center_db": center_db,
    "front_db": front_db,
    "surround_db": surround_db,
    "lfe_db": lfe_db,
    "low_db": low_db,
    "mid_db": mid_db,
    "high_db": high_db,
    "onset": onset_full,
    "low_onset": onset_low,
    "drum_score": drum_score,
    "impact_score": impact_score,
    "swell_score": swell_score,
    "harsh_score": harsh_score,
    "barrage_score": barrage_score,
    "burden": burden,
    "center_advantage": center_advantage,
    "surround_advantage": surround_advantage,
})

seconds_df = frame_df.groupby(
    "second"
).mean().reset_index()

seconds_df["timestamp"] = seconds_df[
    "second"
].map(timestamp)

seconds_df.to_csv(
    out / "timeline.csv",
    index=False
)


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

summary = []

summary.append(
    f"Duration: {timestamp(duration)}"
)

summary.append(
    f"Channels: {channels}"
)

summary.append(
    f"Impact candidates: {len(impact_peaks)}"
)

summary.append(
    f"Swell candidates: {len(swell_peaks)}"
)

summary.append(
    f"Drum-run candidates: {len(drum_peaks)}"
)

summary.append(
    f"Harsh candidates: {len(harsh_peaks)}"
)

summary.append(
    f"Barrage regions: {len(barrage_regions)}"
)

summary.append(
    f"High-load regions: {len(high_load_regions)}"
)

summary.append(
    f"Recovery regions: {len(recovery_regions)}"
)

recovery_seconds = sum(
    t1 - t0
    for _, _, t0, t1 in recovery_regions
)

summary.append(
    "Recovery fraction: "
    f"{100 * recovery_seconds / duration:.1f}%"
)

(out / "summary.txt").write_text(
    "\n".join(summary) + "\n"
)

print()
print("\n".join(summary))


# ------------------------------------------------------------
# Plot helper
# ------------------------------------------------------------

minutes = times / 60


def save_plot(
    values,
    title,
    ylabel,
    filename,
):
    plt.figure(figsize=(18, 5))
    plt.plot(minutes, values)
    plt.xlabel("Movie time (minutes)")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(
        out / filename,
        dpi=160
    )
    plt.close()


save_plot(
    mono_db,
    "Drive Through Fire — Loudness",
    "dBFS",
    "01-loudness.png"
)

save_plot(
    onset_full,
    "Drive Through Fire — Broadband Transients",
    "Onset strength",
    "02-transients.png"
)

save_plot(
    drum_score,
    "Drive Through Fire — Low-Frequency Rhythmic Activity",
    "Drum score",
    "03-drum-runs.png"
)

save_plot(
    swell_score,
    "Drive Through Fire — Gradual Swell Candidates",
    "Swell score",
    "04-swells.png"
)

save_plot(
    barrage_score,
    "Drive Through Fire — Transient Barrage",
    "Barrage score",
    "05-barrage.png"
)

save_plot(
    harsh_score,
    "Drive Through Fire — Spectral Harshness",
    "Harshness score",
    "06-harshness.png"
)

save_plot(
    burden,
    "Drive Through Fire — Acoustic Burden",
    "Burden",
    "07-burden.png"
)

save_plot(
    center_advantage,
    "Drive Through Fire — Center Channel Advantage",
    "Center advantage (dB)",
    "08-center-channel.png"
)

save_plot(
    surround_advantage,
    "Drive Through Fire — Surround Advantage",
    "Surround advantage (dB)",
    "09-surround-channel.png"
)


# ------------------------------------------------------------
# Recovery map
# ------------------------------------------------------------

plt.figure(figsize=(18, 3))

plt.plot(
    minutes,
    burden
)

for _, _, t0, t1 in recovery_regions:
    plt.axvspan(
        t0 / 60,
        t1 / 60,
        alpha=0.2
    )

plt.xlabel("Movie time (minutes)")
plt.ylabel("Burden")
plt.title(
    "Drive Through Fire — Acoustic Recovery Windows"
)

plt.tight_layout()
plt.savefig(
    out / "10-recovery.png",
    dpi=160
)
plt.close()


# ------------------------------------------------------------
# Event-density map
# ------------------------------------------------------------

plt.figure(figsize=(18, 5))

plt.plot(
    minutes,
    barrage_density
)

plt.xlabel("Movie time (minutes)")
plt.ylabel("Transient density")

plt.title(
    "Drive Through Fire — Five-Second Event Density"
)

plt.tight_layout()
plt.savefig(
    out / "11-event-density.png",
    dpi=160
)

plt.close()


print()
print("Output:", out)
