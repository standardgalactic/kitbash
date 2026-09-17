#!/usr/bin/env python3

"""
Soundtrack Structural Analysis v3.1
===================================

Changes from v3
---------------

1. Level gating.
   Onset strength, spectral centroid, flatness and zero-crossing rate
   are all (nearly) level-invariant. In v3 a click at -65 dBFS scored
   the same as a crash at -25 dBFS, and digital silence / dither
   produced the largest HARSH values in the film. Every shape or
   transient feature is now multiplied by an audibility weight
   derived from absolute level, and robust statistics are computed
   over audible frames only.

2. SWELL is an event detector, not a frame trace.
   In v3, more than half the positive-gradient frames were exactly 0,
   so the MAD was 0, robust_z() returned all zeros, and the swell
   score reduced to -0.25 * onset+. The swell plot was an inverted
   transient plot. v3.1 measures S(t, D) = L(t + D) - L(t) for several
   windows D over 0.25 s energy bins, and requires the rise to be
   sustained (mostly monotonic, not carried by one step).

3. Audition clips + annotation CSV.
   Top-N candidates per category are cut from the source with ffmpeg
   into audition/<category>/, with an .m3u playlist per category and
   a blank annotations.csv to fill in.

4. --from-frames reuses an existing frames.csv (v3 or v3.1), so the
   post-processing can be rerun without re-decoding the film.

5. --annotations reads a filled-in annotations.csv and reports
   per-category precision plus a labelled timeline.

These are still acoustic classifications, not semantic recognition.
"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import soundfile as sf

from scipy.ndimage import gaussian_filter1d, median_filter
from scipy.signal import find_peaks


LABELS = [
    "DRUM", "MUSIC_SWELL", "MUSIC_OTHER",
    "SIREN", "ALARM",
    "GUNSHOT", "EXPLOSION", "PUNCH", "CRASH", "GLASS",
    "ENGINE", "TIRES",
    "YELLING", "SCREAM", "CROWD",
    "DIALOGUE",
    "FALSE_POSITIVE", "UNSURE",
]


# ============================================================
# Utilities
# ============================================================

def timestamp(seconds):
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def file_stamp(seconds):
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}-{m:02d}-{s:02d}"


def robust_z(x, mask=None):
    """
    Median/MAD z-score, with statistics taken over `mask` if given.

    Falls back to IQR, then standard deviation, when the MAD is
    degenerate. (A zero MAD is what silently killed the v3 swell
    score.)
    """
    x = np.asarray(x, dtype=np.float64)
    ref = x
    if mask is not None and np.count_nonzero(mask) > 100:
        ref = x[mask]
    ref = ref[np.isfinite(ref)]
    if len(ref) == 0:
        return np.zeros_like(x)

    med = np.median(ref)
    scale = 1.4826 * np.median(np.abs(ref - med))

    if scale < 1e-12:
        q75, q25 = np.percentile(ref, [75, 25])
        scale = (q75 - q25) / 1.349
    if scale < 1e-12:
        scale = np.std(ref)
    if scale < 1e-12:
        return np.zeros_like(x)

    return (x - med) / scale


def normalize01(x, mask=None):
    x = np.asarray(x, dtype=np.float64)
    ref = x[mask] if mask is not None and np.count_nonzero(mask) > 100 else x
    ref = ref[np.isfinite(ref)]
    if len(ref) == 0:
        return np.zeros_like(x)
    lo, hi = np.percentile(ref, [5, 95])
    if hi <= lo:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def level_weight(db, floor, full):
    """0 at or below `floor` dBFS, 1 at or above `full`, linear between."""
    return np.clip((np.asarray(db) - floor) / (full - floor), 0.0, 1.0)


def run(cmd, quiet=False):
    if not quiet:
        print("+", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def require(program):
    if shutil.which(program) is None:
        raise SystemExit(f"Required program not found: {program}")


def contiguous_regions(mask, times, minimum_duration=1.0):
    mask = np.asarray(mask, dtype=bool)
    if len(mask) == 0 or not np.any(mask):
        return []

    changes = np.diff(mask.astype(np.int8))
    starts = list(np.where(changes == 1)[0] + 1)
    ends = list(np.where(changes == -1)[0] + 1)
    if mask[0]:
        starts.insert(0, 0)
    if mask[-1]:
        ends.append(len(mask))

    regions = []
    for start, end in zip(starts, ends):
        if end <= start:
            continue
        t0 = float(times[start])
        t1 = float(times[min(end - 1, len(times) - 1)])
        if t1 - t0 >= minimum_duration:
            regions.append((start, end, t0, t1))
    return regions


# ============================================================
# Arguments
# ============================================================

parser = argparse.ArgumentParser(
    description="Soundtrack structural analysis v3.1"
)
parser.add_argument("input", help="Movie/audio file (needed for audition clips)")
parser.add_argument("--out", default="sound-analysis-v3.1")
parser.add_argument("--title", default=None,
                    help="Plot title prefix (default: input file stem)")
parser.add_argument("--audio-stream", default="0:a:0",
                    help="ffmpeg stream selector; default: 0:a:0")
parser.add_argument("--chunk", type=float, default=60.0)
parser.add_argument("--sr", type=int, default=16000)
parser.add_argument("--hop", type=int, default=512)
parser.add_argument("--keep-stems", action="store_true")

parser.add_argument("--from-frames", default=None,
                    help="Reuse an existing frames.csv instead of decoding")

parser.add_argument("--gate-floor", type=float, default=-65.0,
                    help="Broadband dBFS at which features get zero weight")
parser.add_argument("--gate-full", type=float, default=-45.0,
                    help="Broadband dBFS at which features get full weight")
parser.add_argument("--low-gate-floor", type=float, default=-70.0)
parser.add_argument("--low-gate-full", type=float, default=-50.0)

parser.add_argument("--swell-windows", default="2,4,6,8",
                    help="Comma-separated swell windows in seconds")
parser.add_argument("--swell-min-rise", type=float, default=6.0,
                    help="Minimum sustained rise in dB")

parser.add_argument("--audition", type=int, default=20,
                    help="Clips per category (0 disables)")
parser.add_argument("--pre", type=float, default=12.0,
                    help="Seconds before a point event")
parser.add_argument("--post", type=float, default=8.0,
                    help="Seconds after a point event")

parser.add_argument("--annotations", default=None,
                    help="Filled-in annotations.csv to summarize/plot")

args = parser.parse_args()

source = Path(args.input)
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
title = args.title or source.stem

require("ffmpeg")
require("ffprobe")


# ============================================================
# Feature extraction (unchanged from v3 apart from refactoring)
# ============================================================

def probe_channels(path):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=channels,channel_layout,sample_rate",
         "-of", "default=noprint_wrappers=1:nokey=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    print("\nSOURCE AUDIO\n------------")
    print(probe.stdout.strip(), "\n")
    for line in probe.stdout.splitlines():
        if line.startswith("channels="):
            try:
                return int(line.split("=", 1)[1])
            except ValueError:
                pass
    print("Warning: could not determine channel count.")
    return None


def extract_frames(path, channels):
    if args.keep_stems:
        stem_dir = out / "analysis-stems"
        stem_dir.mkdir(exist_ok=True)
        temp = None
    else:
        temp = tempfile.TemporaryDirectory()
        stem_dir = Path(temp.name)

    broadband_path = stem_dir / "broadband.wav"
    low_path = stem_dir / "low.wav"
    center_path = stem_dir / "center.wav"
    noncenter_path = stem_dir / "noncenter.wav"

    base = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(path), "-map", args.audio_stream, "-vn"]

    print("Creating lightweight analysis stems...\n")
    run(base + ["-ac", "1", "-ar", str(args.sr), "-c:a", "pcm_s16le",
                str(broadband_path)])
    run(base + ["-af", "lowpass=f=250", "-ac", "1", "-ar", "8000",
                "-c:a", "pcm_s16le", str(low_path)])

    has_center = channels is not None and channels >= 3
    if has_center:
        run(base + ["-af", "pan=mono|c0=FC", "-ar", str(args.sr),
                    "-c:a", "pcm_s16le", str(center_path)])
        pan = ("pan=mono|c0=0.25*FL+0.25*FR+0.25*SL+0.25*SR"
               if channels >= 6 else "pan=mono|c0=0.5*FL+0.5*FR")
        run(base + ["-af", pan, "-ar", str(args.sr),
                    "-c:a", "pcm_s16le", str(noncenter_path)])
    else:
        print("\nNo discrete center channel; using broadband mono.")
        shutil.copyfile(broadband_path, center_path)
        shutil.copyfile(broadband_path, noncenter_path)

    broad_file = sf.SoundFile(broadband_path)
    low_file = sf.SoundFile(low_path)
    center_file = sf.SoundFile(center_path)
    noncenter_file = sf.SoundFile(noncenter_path)

    broad_sr = broad_file.samplerate
    low_sr = low_file.samplerate
    duration = len(broad_file) / broad_sr

    print(f"\nDuration: {timestamp(duration)}\n")

    columns = {k: [] for k in [
        "time", "loudness_db", "onset", "centroid_hz", "flatness", "zcr",
        "low_db", "low_onset", "center_db", "noncenter_db"]}

    chunk_start = 0.0
    chunk_number = 0
    low_hop = max(1, int(args.hop * low_sr / broad_sr))

    while chunk_start < duration:
        chunk_number += 1
        chunk_duration = min(args.chunk, duration - chunk_start)
        print(f"\rChunk {chunk_number:03d}  {timestamp(chunk_start)}",
              end="", flush=True)

        for f in (broad_file, center_file, noncenter_file):
            f.seek(int(chunk_start * broad_sr))
        low_file.seek(int(chunk_start * low_sr))

        nb = int(chunk_duration * broad_sr)
        nl = int(chunk_duration * low_sr)

        y = broad_file.read(nb, dtype="float32", always_2d=False)
        center = center_file.read(nb, dtype="float32", always_2d=False)
        noncenter = noncenter_file.read(nb, dtype="float32", always_2d=False)
        low = low_file.read(nl, dtype="float32", always_2d=False)

        if len(y) < 2048:
            break

        def db_rms(sig, frame, hop):
            r = librosa.feature.rms(y=sig, frame_length=frame, hop_length=hop)[0]
            return librosa.amplitude_to_db(np.maximum(r, 1e-10), ref=1.0)

        feats = [
            db_rms(y, 2048, args.hop),
            librosa.onset.onset_strength(y=y, sr=broad_sr, hop_length=args.hop),
            librosa.feature.spectral_centroid(
                y=y, sr=broad_sr, n_fft=2048, hop_length=args.hop)[0],
            librosa.feature.spectral_flatness(
                y=y, n_fft=2048, hop_length=args.hop)[0],
            librosa.feature.zero_crossing_rate(
                y, frame_length=2048, hop_length=args.hop)[0],
            db_rms(low, 1024, low_hop),
            librosa.onset.onset_strength(y=low, sr=low_sr, hop_length=low_hop),
            db_rms(center, 2048, args.hop),
            db_rms(noncenter, 2048, args.hop),
        ]

        n = min(len(f) for f in feats)
        if n == 0:
            chunk_start += chunk_duration
            continue

        # Drop the final frame of each chunk: with centred framing it
        # sits exactly on the next chunk's first frame.
        if chunk_start + chunk_duration < duration and n > 1:
            n -= 1

        t = chunk_start + librosa.frames_to_time(
            np.arange(n), sr=broad_sr, hop_length=args.hop)

        columns["time"].append(t)
        for key, f in zip(list(columns)[1:], feats):
            columns[key].append(np.asarray(f[:n], dtype=np.float64))

        chunk_start += chunk_duration

    print("\n")

    for f in (broad_file, low_file, center_file, noncenter_file):
        f.close()

    if args.keep_stems:
        print("Analysis stems retained in:", stem_dir)
    else:
        temp.cleanup()

    return pd.DataFrame({k: np.concatenate(v) for k, v in columns.items()}), duration


channels = probe_channels(source)

if args.from_frames:
    raw_cols = ["time", "loudness_db", "onset", "centroid_hz", "flatness",
                "zcr", "low_db", "low_onset", "center_db", "noncenter_db"]
    df = pd.read_csv(args.from_frames, usecols=raw_cols)
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    duration = float(df["time"].iloc[-1])
    print(f"Reusing {args.from_frames}: {len(df)} frames, "
          f"{timestamp(duration)}\n")
else:
    df, duration = extract_frames(source, channels)

if len(df) == 0:
    raise SystemExit("No analysis frames generated.")

times = df["time"].to_numpy()
loud_db = df["loudness_db"].to_numpy()
onset = df["onset"].to_numpy()
centroid = df["centroid_hz"].to_numpy()
flatness = df["flatness"].to_numpy()
zcr = df["zcr"].to_numpy()
low_db = df["low_db"].to_numpy()
low_onset = df["low_onset"].to_numpy()
center_db = df["center_db"].to_numpy()
noncenter_db = df["noncenter_db"].to_numpy()

frame_rate = 1.0 / float(np.median(np.diff(times)))


# ============================================================
# Audibility gating
# ============================================================

w = level_weight(loud_db, args.gate_floor, args.gate_full)
w_low = level_weight(low_db, args.low_gate_floor, args.low_gate_full)

audible = w > 0.5
audible_low = w_low > 0.5

silent_fraction = 1.0 - np.mean(w > 0)
print(f"Frames below gate floor ({args.gate_floor:.0f} dBFS): "
      f"{100 * silent_fraction:.1f}%")

# Statistics are taken over audible frames, then the result is
# multiplied by the audibility weight so quiet material cannot score
# as harsh or percussive merely because its spectrum is flat.

z_loud = robust_z(loud_db, audible)
z_onset = w * robust_z(onset, audible)
z_centroid = w * robust_z(centroid, audible)
z_flatness = w * robust_z(flatness, audible)
z_zcr = w * robust_z(zcr, audible)
z_low = robust_z(low_db, audible_low)
z_low_onset = w_low * robust_z(low_onset, audible_low)

onset_gated = w * onset

# Center advantage is meaningless when both sides are near silence.
center_advantage = center_db - noncenter_db
center_advantage = np.where(
    np.maximum(center_db, noncenter_db) > args.gate_floor,
    center_advantage, np.nan)


# ============================================================
# IMPACT / HARSH / DRUM / BARRAGE (gated)
# ============================================================

impact_score = (0.50 * z_onset + 0.20 * w * z_loud + 0.15 * z_centroid
                + 0.10 * z_flatness + 0.05 * z_zcr)

harsh_score = (0.30 * z_centroid + 0.30 * z_flatness + 0.20 * z_zcr
               + 0.20 * w * z_loud)


def moving_mean(x, seconds):
    k = max(1, int(seconds * frame_rate))
    return np.convolve(x, np.ones(k) / k, mode="same")


drum_density = moving_mean(np.maximum(z_low_onset, 0), 4.0)
drum_score = 0.60 * robust_z(drum_density, audible_low) + 0.40 * w_low * z_low

barrage_density = moving_mean(np.maximum(z_onset, 0), 5.0)
barrage_score = (0.60 * robust_z(barrage_density, audible)
                 + 0.25 * w * z_loud + 0.15 * z_centroid)


# ============================================================
# ACOUSTIC BURDEN (gated)
# ============================================================

burden = (0.25 * normalize01(loud_db, audible)
          + 0.20 * normalize01(onset_gated, audible)
          + 0.20 * normalize01(drum_density, audible_low)
          + 0.15 * w * normalize01(centroid, audible)
          + 0.10 * w * normalize01(flatness, audible)
          + 0.10 * normalize01(barrage_density, audible))

burden_smooth = gaussian_filter1d(burden, sigma=max(1, 0.5 * frame_rate))


# ============================================================
# SWELL events
#
#   S(t, D) = L(t + D) - L(t)
#
# over 0.25 s energy-averaged bins, median-filtered across 1 s so a
# single transient cannot carry the rise. A candidate must:
#
#   rise       >= --swell-min-rise dB
#   up-steps   >= 60% of steps in the window
#   top two steps together <= 50% of the total rise
#   end level  above the gate floor
#
# The top-two rule stops a hard cut from silence, smeared across two
# bins by the analysis window, from registering as a swell.
# ============================================================

BIN = 0.25
bin_index = np.floor(times / BIN).astype(int)
n_bins = bin_index.max() + 1

power = 10.0 ** (loud_db / 10.0)
bin_power = np.bincount(bin_index, weights=power, minlength=n_bins)
bin_count = np.bincount(bin_index, minlength=n_bins)
bin_db = 10.0 * np.log10(np.maximum(bin_power / np.maximum(bin_count, 1), 1e-12))
bin_db = median_filter(bin_db, size=5, mode="nearest")
bin_times = np.arange(n_bins) * BIN

steps = np.diff(bin_db, prepend=bin_db[0])
windows = [float(x) for x in args.swell_windows.split(",") if x.strip()]

best_rise = np.zeros(n_bins)
best_window = np.zeros(n_bins)

for D in windows:
    k = int(round(D / BIN))
    if k < 2 or k >= n_bins:
        continue

    rise = np.full(n_bins, -np.inf)
    rise[:-k] = bin_db[k:] - bin_db[:-k]

    step_windows = np.lib.stride_tricks.sliding_window_view(steps[1:], k)
    frac_up = np.zeros(n_bins)
    top_two = np.full(n_bins, np.inf)
    m = len(step_windows)
    frac_up[:m] = np.mean(step_windows > 0, axis=1)
    top_two[:m] = np.sum(np.sort(step_windows, axis=1)[:, -2:], axis=1)

    end_level = np.full(n_bins, -np.inf)
    end_level[:-k] = bin_db[k:]

    ok = ((rise >= args.swell_min_rise)
          & (frac_up >= 0.60)
          & (top_two <= 0.50 * rise)
          & (end_level > args.gate_floor))

    better = ok & (rise > best_rise)
    best_rise[better] = rise[better]
    best_window[better] = D

swell_peaks, _ = find_peaks(best_rise, height=args.swell_min_rise,
                            distance=max(1, int(4.0 / BIN)))

swell_events = []
taken_until = -np.inf
for p in sorted(swell_peaks, key=lambda i: -best_rise[i]):
    t0 = bin_times[p]
    t1 = t0 + best_window[p]
    if any(not (t1 <= e["start_seconds"] or t0 >= e["end_seconds"])
           for e in swell_events):
        continue
    swell_events.append({"start_seconds": t0, "end_seconds": t1,
                         "rise_db": best_rise[p], "window": best_window[p]})
swell_events.sort(key=lambda e: e["start_seconds"])

# Frame-level trace for frames.csv: best rise beginning in this bin.
swell_trace = best_rise[np.minimum(bin_index, n_bins - 1)]


# ============================================================
# Point peaks and regions
# ============================================================

def get_peaks(score, percentile, min_gap_s, mask):
    threshold = np.nanpercentile(score[mask] if mask.any() else score,
                                 percentile)
    peaks, _ = find_peaks(np.nan_to_num(score, nan=-np.inf),
                          height=threshold,
                          distance=max(1, int(min_gap_s * frame_rate)))
    return peaks[mask[peaks]]


impact_peaks = get_peaks(impact_score, 98.5, 0.75, audible)
drum_peaks = get_peaks(drum_score, 97.5, 4.0, audible_low)
harsh_peaks = get_peaks(harsh_score, 98.0, 3.0, audible)

barrage_regions = contiguous_regions(
    barrage_score > np.percentile(barrage_score[audible], 85),
    times, minimum_duration=3.0)
high_load_regions = contiguous_regions(
    burden_smooth > np.percentile(burden_smooth, 80),
    times, minimum_duration=4.0)
recovery_regions = contiguous_regions(
    burden_smooth < np.percentile(burden_smooth, 25),
    times, minimum_duration=5.0)


# ============================================================
# Event table
# ============================================================

events = []


def nanmean(x):
    x = x[np.isfinite(x)]
    return float(np.mean(x)) if len(x) else float("nan")


def add_event(label, t0, t1, score, section):
    events.append({
        "type": label,
        "start_seconds": float(t0),
        "end_seconds": float(t1),
        "start": timestamp(t0),
        "end": timestamp(t1),
        "duration": float(t1 - t0),
        "score": float(score),
        "loudness_db": nanmean(loud_db[section]),
        "low_db": nanmean(low_db[section]),
        "center_advantage_db": nanmean(center_advantage[section]),
    })


for label, score, peaks in [("IMPACT", impact_score, impact_peaks),
                            ("DRUM_RUN", drum_score, drum_peaks),
                            ("HARSH", harsh_score, harsh_peaks)]:
    for p in peaks:
        add_event(label, times[p], times[p], score[p], slice(p, p + 1))

for e in swell_events:
    i0 = np.searchsorted(times, e["start_seconds"])
    i1 = np.searchsorted(times, e["end_seconds"])
    add_event("SWELL", e["start_seconds"], e["end_seconds"],
              e["rise_db"], slice(i0, max(i1, i0 + 1)))

for label, score, regions in [("BARRAGE", barrage_score, barrage_regions),
                              ("HIGH_LOAD", burden_smooth, high_load_regions),
                              ("RECOVERY", -burden_smooth, recovery_regions)]:
    for start, end, t0, t1 in regions:
        add_event(label, t0, t1, np.mean(score[start:end]),
                  slice(start, end))

events_df = pd.DataFrame(events).sort_values(["start_seconds", "type"])
events_df.to_csv(out / "events.csv", index=False)


# ============================================================
# Frame and per-second tables
# ============================================================

df["audibility"] = w
df["impact_score"] = impact_score
df["drum_score"] = drum_score
df["swell_rise_db"] = swell_trace
df["harsh_score"] = harsh_score
df["barrage_score"] = barrage_score
df["burden"] = burden_smooth
df["center_advantage_db"] = center_advantage
df.to_csv(out / "frames.csv", index=False)

df["second"] = np.floor(df["time"]).astype(int)
timeline = df.groupby("second").mean(numeric_only=True).reset_index()
timeline["timestamp"] = timeline["second"].map(timestamp)
timeline.to_csv(out / "timeline.csv", index=False)


# ============================================================
# Summary
# ============================================================

def total(regions):
    return sum(t1 - t0 for _, _, t0, t1 in regions)


recovery_gaps = []
previous_end = 0.0
for _, _, t0, t1 in recovery_regions:
    if t0 > previous_end:
        recovery_gaps.append(t0 - previous_end)
    previous_end = t1
if previous_end < duration:
    recovery_gaps.append(duration - previous_end)

summary_lines = [
    f"Source: {source}",
    f"Duration: {timestamp(duration)}",
    f"Source channels: {channels}",
    f"Gate: {args.gate_floor:.0f} -> {args.gate_full:.0f} dBFS "
    f"(low: {args.low_gate_floor:.0f} -> {args.low_gate_full:.0f})",
    f"Frames below gate floor: {100 * silent_fraction:.1f}%",
    "",
    f"Impact candidates: {len(impact_peaks)}",
    f"Drum-run candidates: {len(drum_peaks)}",
    f"Swell events: {len(swell_events)}",
    f"Harsh candidates: {len(harsh_peaks)}",
    "",
    f"Barrage regions: {len(barrage_regions)}",
    f"High-load regions: {len(high_load_regions)}",
    f"Recovery regions: {len(recovery_regions)}",
    "",
    f"Barrage time: {total(barrage_regions):.1f} s "
    f"({100 * total(barrage_regions) / duration:.1f}%)",
    f"High-load time: {total(high_load_regions):.1f} s "
    f"({100 * total(high_load_regions) / duration:.1f}%)",
    f"Recovery time: {total(recovery_regions):.1f} s "
    f"({100 * total(recovery_regions) / duration:.1f}%)",
]
if recovery_gaps:
    summary_lines += [
        "",
        f"Median interval without qualifying recovery: "
        f"{np.median(recovery_gaps):.1f} s",
        f"Longest interval without qualifying recovery: "
        f"{np.max(recovery_gaps):.1f} s",
    ]

summary = "\n".join(summary_lines) + "\n"
(out / "summary.txt").write_text(summary)
print(summary)


# ============================================================
# Plots
# ============================================================

minutes = times / 60.0


def save_plot(values, name, ylabel, filename, spans=None, shade_silence=True):
    plt.figure(figsize=(18, 5))
    if shade_silence:
        for _, _, t0, t1 in contiguous_regions(w == 0, times, 0.5):
            plt.axvspan(t0 / 60, t1 / 60, color="0.85", zorder=0)
    if spans:
        for t0, t1 in spans:
            plt.axvspan(t0 / 60, t1 / 60, color="tab:orange", alpha=0.35)
    plt.plot(minutes, values, linewidth=0.8)
    plt.xlabel("Movie time (minutes)")
    plt.ylabel(ylabel)
    plt.title(f"{title} — {name}")
    plt.tight_layout()
    plt.savefig(out / filename, dpi=160)
    plt.close()


swell_spans = [(e["start_seconds"], e["end_seconds"]) for e in swell_events]

save_plot(loud_db, "Loudness (orange: swell events, grey: below gate)",
          "dBFS", "01-loudness.png", spans=swell_spans)
save_plot(onset_gated, "Acoustic Transients (level-gated)",
          "Onset strength x audibility", "02-transients.png")
save_plot(drum_score, "Low-Frequency Onset Activity",
          "Drum-run score", "03-drum-runs.png")

plt.figure(figsize=(18, 5))
if swell_events:
    starts = np.array([e["start_seconds"] for e in swell_events]) / 60
    rises = np.array([e["rise_db"] for e in swell_events])
    wins = np.array([e["window"] for e in swell_events]) / 60
    plt.bar(starts, rises, width=wins, align="edge", alpha=0.7)
plt.xlim(0, duration / 60)
plt.xlabel("Movie time (minutes)")
plt.ylabel("Sustained rise (dB)")
plt.title(f"{title} — Swell Events (bar width = rise window)")
plt.tight_layout()
plt.savefig(out / "04-swells.png", dpi=160)
plt.close()

save_plot(barrage_score, "Transient Barrage (level-gated)",
          "Barrage score", "05-barrage.png")
save_plot(harsh_score, "Spectral Harshness (level-gated)",
          "Harshness score", "06-harshness.png")
save_plot(burden_smooth, "Acoustic Burden (level-gated)",
          "Burden", "07-burden.png")
save_plot(center_advantage, "Center-Channel Advantage (NaN below gate)",
          "Center minus non-center (dB)", "08-center-advantage.png")
save_plot(burden_smooth, "Recovery Windows", "Acoustic burden",
          "09-recovery.png",
          spans=[(t0, t1) for _, _, t0, t1 in recovery_regions])

plt.figure(figsize=(18, 6))
plt.plot(minutes, normalize01(drum_score) + 3, linewidth=0.8, color="tab:blue")
for t0, t1 in swell_spans:
    plt.axvspan(t0 / 60, t1 / 60, ymin=0.5, ymax=0.75,
                color="tab:orange", alpha=0.8)
plt.plot(minutes, normalize01(barrage_score) + 1, linewidth=0.8, color="tab:green")
plt.plot(minutes, normalize01(burden_smooth), linewidth=0.8, color="tab:red")
plt.yticks([0.5, 1.5, 2.5, 3.5], ["Burden", "Barrage", "Swells", "Drums"])
plt.ylim(0, 4)
plt.xlabel("Movie time (minutes)")
plt.title(f"{title} — Sound Grammar")
plt.tight_layout()
plt.savefig(out / "10-sound-grammar.png", dpi=160)
plt.close()


# ============================================================
# Top candidates
# ============================================================

report = []
for event_type in ["DRUM_RUN", "SWELL", "IMPACT", "HARSH", "BARRAGE"]:
    subset = (events_df[events_df["type"] == event_type]
              .sort_values("score", ascending=False).head(20))
    report.append(f"\n{event_type}\n" + "=" * len(event_type))
    for _, row in subset.iterrows():
        report.append(
            f"{row['start']}  score={row['score']:.2f}  "
            f"dur={row['duration']:.1f}s  level={row['loudness_db']:.1f} dB  "
            f"low={row['low_db']:.1f} dB  "
            f"centerΔ={row['center_advantage_db']:.1f} dB")
(out / "top-candidates.txt").write_text("\n".join(report) + "\n")


# ============================================================
# Audition clips
# ============================================================

def clip_window(row):
    t0, t1 = row["start_seconds"], row["end_seconds"]
    if row["type"] == "SWELL":
        a, b = t0 - 4.0, t1 + 6.0
    elif row["type"] in ("BARRAGE", "HIGH_LOAD"):
        a, b = t0 - 5.0, min(t1, t0 + 20.0) + 5.0
    else:
        a, b = t0 - args.pre, t0 + args.post
    a = max(0.0, a)
    b = min(duration, b, a + 30.0)
    return a, b


if args.audition > 0:
    print("Cutting audition clips...")
    aud = out / "audition"
    aud.mkdir(exist_ok=True)
    rows = []

    for event_type in ["DRUM_RUN", "SWELL", "IMPACT", "HARSH", "BARRAGE"]:
        subset = (events_df[events_df["type"] == event_type]
                  .sort_values("score", ascending=False)
                  .head(args.audition))
        folder = aud / event_type.lower().replace("_run", "")
        folder.mkdir(exist_ok=True)
        playlist = []

        for rank, (_, row) in enumerate(subset.iterrows(), start=1):
            a, b = clip_window(row)
            name = (f"{rank:02d}_{file_stamp(row['start_seconds'])}"
                    f"_score-{row['score']:.2f}.mp3")
            target = folder / name
            if not target.exists():
                run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                     "-ss", f"{a:.3f}", "-i", str(source),
                     "-t", f"{b - a:.3f}", "-map", args.audio_stream,
                     "-vn", "-ac", "2", "-c:a", "libmp3lame", "-q:a", "4",
                     str(target)], quiet=True)
            playlist.append(name)
            rows.append({
                "clip": f"{folder.name}/{name}",
                "category": event_type,
                "rank": rank,
                "event_time": timestamp(row["start_seconds"]),
                "event_seconds": round(float(row["start_seconds"]), 2),
                "event_offset_in_clip": round(row["start_seconds"] - a, 2),
                "score": round(float(row["score"]), 3),
                "level_db": round(float(row["loudness_db"]), 1),
                "label": "",
                "notes": "",
            })
        (folder / "playlist.m3u").write_text("\n".join(playlist) + "\n")
        print(f"  {event_type:9s} {len(playlist)} clips")

    ann = aud / "annotations.csv"
    target = ann if not ann.exists() else aud / "annotations.new.csv"
    pd.DataFrame(rows).to_csv(target, index=False)
    (aud / "LABELS.txt").write_text(
        "Fill the `label` column with one of (or several joined by '+'):\n\n"
        + "\n".join(LABELS) + "\n")
    if target != ann:
        print(f"  {ann} exists; new template written to {target.name}")


# ============================================================
# Annotation summary
# ============================================================

if args.annotations:
    ann = pd.read_csv(args.annotations).fillna("")
    ann = ann[ann["label"].str.strip() != ""]
    if len(ann) == 0:
        print("No labelled rows in", args.annotations)
    else:
        ann["labels"] = ann["label"].str.upper().str.split("+")
        exploded = ann.explode("labels").reset_index(drop=True)
        exploded["labels"] = exploded["labels"].str.strip()

        lines = ["DETECTOR PRECISION (share not FALSE_POSITIVE)", ""]
        for cat, g in ann.groupby("category"):
            fp = g["labels"].apply(lambda L: "FALSE_POSITIVE" in L).sum()
            lines.append(f"{cat:9s} {len(g) - fp:3d}/{len(g):3d} "
                         f"= {(len(g) - fp) / len(g):.0%}")
        lines += ["", "WHAT EACH DETECTOR ACTUALLY FOUND", ""]
        table = pd.crosstab(exploded["category"], exploded["labels"])
        lines.append(table.to_string())
        text = "\n".join(lines) + "\n"
        (out / "annotation-summary.txt").write_text(text)
        print(text)

        kinds = sorted(set(exploded["labels"]) - {"FALSE_POSITIVE"})
        plt.figure(figsize=(18, 0.5 * len(kinds) + 2))
        for i, k in enumerate(kinds):
            ts = exploded.loc[exploded["labels"] == k, "event_seconds"] / 60
            plt.scatter(ts, np.full(len(ts), i), marker="|", s=300)
        plt.yticks(range(len(kinds)), kinds)
        plt.xlim(0, duration / 60)
        plt.xlabel("Movie time (minutes)")
        plt.title(f"{title} — Labelled Events")
        plt.tight_layout()
        plt.savefig(out / "11-labelled-events.png", dpi=160)
        plt.close()


print("\nWritten to", out)
print("Done.")
