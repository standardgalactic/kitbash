#!/usr/bin/env python3

"""
Soundtrack Structural Analysis v3
=================================

Memory-safe analysis for feature-length multichannel films.

Detects candidates for:

    IMPACT      abrupt broadband transient
    DRUM_RUN    sustained/repeated low-frequency percussion
    SWELL       gradual increase in acoustic energy
    HARSH       spectrally noisy / bright material
    BARRAGE     sustained high transient density
    HIGH_LOAD   sustained high acoustic burden
    RECOVERY    sustained low acoustic burden

Also measures center-channel dominance when the source contains
a conventional multichannel mix.

Important:
    These are acoustic classifications, not semantic recognition.
    IMPACT does not automatically mean "gunshot" or "punch".
    Manual annotation remains necessary for semantic labels.

Architecture:

    source MKV
        │
        ├── ffmpeg → broadband mono
        ├── ffmpeg → low-frequency mono
        ├── ffmpeg → center channel
        └── ffmpeg → non-center mix
                         │
                         ▼
                  chunked analysis
                         │
                         ▼
                  compact feature table

No full-film STFT is retained in memory.
"""

import argparse
import shutil
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


# ============================================================
# Configuration / utilities
# ============================================================

def timestamp(seconds):
    seconds = max(0.0, float(seconds))

    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60

    return f"{h:02d}:{m:02d}:{s:05.2f}"


def robust_z(x):
    x = np.asarray(x, dtype=np.float64)

    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med))

    if not np.isfinite(mad) or mad < 1e-12:
        return np.zeros_like(x)

    return (x - med) / (1.4826 * mad)


def normalize01(x):
    x = np.asarray(x, dtype=np.float64)

    lo = np.nanpercentile(x, 5)
    hi = np.nanpercentile(x, 95)

    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.zeros_like(x)

    return np.clip(
        (x - lo) / (hi - lo),
        0.0,
        1.0
    )


def run(cmd):
    print("+", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def require(program):
    if shutil.which(program) is None:
        raise SystemExit(
            f"Required program not found: {program}"
        )


def contiguous_regions(mask, times, minimum_duration=1.0):
    mask = np.asarray(mask, dtype=bool)

    if len(mask) == 0 or not np.any(mask):
        return []

    changes = np.diff(mask.astype(np.int8))

    starts = list(
        np.where(changes == 1)[0] + 1
    )

    ends = list(
        np.where(changes == -1)[0] + 1
    )

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
            regions.append(
                (start, end, t0, t1)
            )

    return regions


# ============================================================
# Arguments
# ============================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "input",
    help="Movie/audio file"
)

parser.add_argument(
    "--out",
    default="sound-analysis-v3"
)

parser.add_argument(
    "--audio-stream",
    default="0:a:0",
    help="ffmpeg stream selector; default: 0:a:0"
)

parser.add_argument(
    "--chunk",
    type=float,
    default=60.0,
    help="Analysis chunk length in seconds"
)

parser.add_argument(
    "--sr",
    type=int,
    default=16000,
    help="Broadband analysis sample rate"
)

parser.add_argument(
    "--hop",
    type=int,
    default=512
)

parser.add_argument(
    "--keep-stems",
    action="store_true",
    help="Keep temporary analysis WAV files"
)

args = parser.parse_args()

source = Path(args.input)

if not source.exists():
    raise SystemExit(
        f"Input does not exist: {source}"
    )

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)

require("ffmpeg")
require("ffprobe")


# ============================================================
# Determine channel count
# ============================================================

probe_cmd = [
    "ffprobe",
    "-v", "error",
    "-select_streams", "a:0",
    "-show_entries",
    "stream=channels,channel_layout,sample_rate",
    "-of",
    "default=noprint_wrappers=1:nokey=0",
    str(source),
]

probe = subprocess.run(
    probe_cmd,
    check=True,
    capture_output=True,
    text=True
)

print()
print("SOURCE AUDIO")
print("------------")
print(probe.stdout.strip())
print()


channels = None

for line in probe.stdout.splitlines():
    if line.startswith("channels="):
        try:
            channels = int(
                line.split("=", 1)[1]
            )
        except ValueError:
            pass

if channels is None:
    print(
        "Warning: could not determine channel count."
    )


# ============================================================
# Temporary stem directory
# ============================================================

if args.keep_stems:

    stem_dir = out / "analysis-stems"
    stem_dir.mkdir(exist_ok=True)

    cleanup = False

else:

    temp = tempfile.TemporaryDirectory()
    stem_dir = Path(temp.name)

    cleanup = True


broadband_path = stem_dir / "broadband.wav"
low_path = stem_dir / "low.wav"
center_path = stem_dir / "center.wav"
noncenter_path = stem_dir / "noncenter.wav"


# ============================================================
# Decode lightweight analysis stems
#
# PCM 16-bit keeps these substantially smaller than float WAV.
# ============================================================

print("Creating lightweight analysis stems...")
print()


# Broadband mono
run([
    "ffmpeg",
    "-y",
    "-hide_banner",
    "-loglevel", "error",
    "-i", str(source),
    "-map", args.audio_stream,
    "-vn",
    "-ac", "1",
    "-ar", str(args.sr),
    "-c:a", "pcm_s16le",
    str(broadband_path),
])


# Low-frequency mono.
#
# ffmpeg performs the filtering while streaming, so Python never
# creates a movie-length complex STFT.
run([
    "ffmpeg",
    "-y",
    "-hide_banner",
    "-loglevel", "error",
    "-i", str(source),
    "-map", args.audio_stream,
    "-vn",
    "-af", "lowpass=f=250",
    "-ac", "1",
    "-ar", "8000",
    "-c:a", "pcm_s16le",
    str(low_path),
])


# ============================================================
# Center / non-center stems
#
# For conventional 5.1:
#
#   FL FR FC LFE SL SR
#
# pan extracts FC directly.
#
# If the source isn't >= 3 channels, broadband is used as the
# center approximation.
# ============================================================

has_center = channels is not None and channels >= 3


if has_center:

    print()
    print("Extracting center channel...")

    run([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(source),
        "-map", args.audio_stream,
        "-vn",
        "-af", "pan=mono|c0=FC",
        "-ar", str(args.sr),
        "-c:a", "pcm_s16le",
        str(center_path),
    ])


    print()
    print("Creating non-center comparison stem...")

    if channels >= 6:

        pan_filter = (
            "pan=mono|"
            "c0=0.25*FL+0.25*FR+"
            "0.25*SL+0.25*SR"
        )

    else:

        pan_filter = (
            "pan=mono|"
            "c0=0.5*FL+0.5*FR"
        )

    run([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(source),
        "-map", args.audio_stream,
        "-vn",
        "-af", pan_filter,
        "-ar", str(args.sr),
        "-c:a", "pcm_s16le",
        str(noncenter_path),
    ])

else:

    print()
    print(
        "No discrete center channel detected; "
        "center analysis will use broadband mono."
    )

    shutil.copyfile(
        broadband_path,
        center_path
    )

    shutil.copyfile(
        broadband_path,
        noncenter_path
    )


# ============================================================
# Open stems without loading them into memory
# ============================================================

broad_file = sf.SoundFile(
    broadband_path
)

low_file = sf.SoundFile(
    low_path
)

center_file = sf.SoundFile(
    center_path
)

noncenter_file = sf.SoundFile(
    noncenter_path
)


duration = (
    len(broad_file) /
    broad_file.samplerate
)

print()
print("ANALYSIS")
print("--------")
print("Duration:", timestamp(duration))
print("Chunk:   ", args.chunk, "seconds")
print("Rate:    ", broad_file.samplerate, "Hz")
print()


# ============================================================
# Chunk feature extraction
# ============================================================

rows = []

chunk_start = 0.0

broad_sr = broad_file.samplerate
low_sr = low_file.samplerate

chunk_number = 0


while chunk_start < duration:

    chunk_number += 1

    chunk_duration = min(
        args.chunk,
        duration - chunk_start
    )

    print(
        f"\rChunk {chunk_number:03d}  "
        f"{timestamp(chunk_start)}",
        end="",
        flush=True
    )


    # --------------------------------------------------------
    # Seek
    # --------------------------------------------------------

    broad_file.seek(
        int(chunk_start * broad_sr)
    )

    center_file.seek(
        int(chunk_start * broad_sr)
    )

    noncenter_file.seek(
        int(chunk_start * broad_sr)
    )

    low_file.seek(
        int(chunk_start * low_sr)
    )


    # --------------------------------------------------------
    # Read only this chunk
    # --------------------------------------------------------

    count_broad = int(
        chunk_duration * broad_sr
    )

    count_low = int(
        chunk_duration * low_sr
    )


    y = broad_file.read(
        count_broad,
        dtype="float32",
        always_2d=False
    )

    center = center_file.read(
        count_broad,
        dtype="float32",
        always_2d=False
    )

    noncenter = noncenter_file.read(
        count_broad,
        dtype="float32",
        always_2d=False
    )

    low = low_file.read(
        count_low,
        dtype="float32",
        always_2d=False
    )


    if len(y) < 2048:
        break


    # --------------------------------------------------------
    # Broadband features
    # --------------------------------------------------------

    rms = librosa.feature.rms(
        y=y,
        frame_length=2048,
        hop_length=args.hop
    )[0]

    loud_db = librosa.amplitude_to_db(
        np.maximum(rms, 1e-10),
        ref=1.0
    )


    onset = librosa.onset.onset_strength(
        y=y,
        sr=broad_sr,
        hop_length=args.hop
    )


    centroid = librosa.feature.spectral_centroid(
        y=y,
        sr=broad_sr,
        n_fft=2048,
        hop_length=args.hop
    )[0]


    flatness = librosa.feature.spectral_flatness(
        y=y,
        n_fft=2048,
        hop_length=args.hop
    )[0]


    zcr = librosa.feature.zero_crossing_rate(
        y,
        frame_length=2048,
        hop_length=args.hop
    )[0]


    # --------------------------------------------------------
    # Center / non-center RMS
    # --------------------------------------------------------

    center_rms = librosa.feature.rms(
        y=center,
        frame_length=2048,
        hop_length=args.hop
    )[0]

    center_db = librosa.amplitude_to_db(
        np.maximum(center_rms, 1e-10),
        ref=1.0
    )


    noncenter_rms = librosa.feature.rms(
        y=noncenter,
        frame_length=2048,
        hop_length=args.hop
    )[0]

    noncenter_db = librosa.amplitude_to_db(
        np.maximum(noncenter_rms, 1e-10),
        ref=1.0
    )


    # --------------------------------------------------------
    # Low-frequency features
    #
    # Keep approximately the same temporal resolution as the
    # broadband analysis.
    # --------------------------------------------------------

    low_hop = max(
        1,
        int(args.hop * low_sr / broad_sr)
    )


    low_rms = librosa.feature.rms(
        y=low,
        frame_length=1024,
        hop_length=low_hop
    )[0]


    low_db = librosa.amplitude_to_db(
        np.maximum(low_rms, 1e-10),
        ref=1.0
    )


    low_onset = librosa.onset.onset_strength(
        y=low,
        sr=low_sr,
        hop_length=low_hop
    )


    # --------------------------------------------------------
    # Align frame counts
    # --------------------------------------------------------

    n = min(
        len(loud_db),
        len(onset),
        len(centroid),
        len(flatness),
        len(zcr),
        len(center_db),
        len(noncenter_db),
        len(low_db),
        len(low_onset),
    )


    if n == 0:
        chunk_start += chunk_duration
        continue


    loud_db = loud_db[:n]
    onset = onset[:n]
    centroid = centroid[:n]
    flatness = flatness[:n]
    zcr = zcr[:n]

    center_db = center_db[:n]
    noncenter_db = noncenter_db[:n]

    low_db = low_db[:n]
    low_onset = low_onset[:n]


    local_times = librosa.frames_to_time(
        np.arange(n),
        sr=broad_sr,
        hop_length=args.hop
    )


    absolute_times = (
        chunk_start +
        local_times
    )


    # --------------------------------------------------------
    # Store only compact feature rows.
    #
    # Audio itself disappears at the end of this loop.
    # --------------------------------------------------------

    for i in range(n):

        rows.append({
            "time": float(
                absolute_times[i]
            ),

            "loudness_db": float(
                loud_db[i]
            ),

            "onset": float(
                onset[i]
            ),

            "centroid_hz": float(
                centroid[i]
            ),

            "flatness": float(
                flatness[i]
            ),

            "zcr": float(
                zcr[i]
            ),

            "low_db": float(
                low_db[i]
            ),

            "low_onset": float(
                low_onset[i]
            ),

            "center_db": float(
                center_db[i]
            ),

            "noncenter_db": float(
                noncenter_db[i]
            ),
        })


    chunk_start += chunk_duration


print()
print()


broad_file.close()
low_file.close()
center_file.close()
noncenter_file.close()


# ============================================================
# Compact full-film feature table
# ============================================================

df = pd.DataFrame(rows)

if len(df) == 0:
    raise SystemExit(
        "No analysis frames generated."
    )


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


frame_rate = (
    broad_sr /
    args.hop
)


# ============================================================
# Global normalization
#
# This occurs only after feature extraction, so statistics are
# calculated over the entire movie rather than independently
# within each chunk.
# ============================================================

z_loud = robust_z(loud_db)
z_onset = robust_z(onset)

z_centroid = robust_z(centroid)
z_flatness = robust_z(flatness)
z_zcr = robust_z(zcr)

z_low = robust_z(low_db)
z_low_onset = robust_z(low_onset)


center_advantage = (
    center_db -
    noncenter_db
)


# ============================================================
# IMPACT
#
# Abrupt broadband events.
# ============================================================

impact_score = (
    0.50 * z_onset +
    0.20 * z_loud +
    0.15 * z_centroid +
    0.10 * z_flatness +
    0.05 * z_zcr
)


# ============================================================
# HARSH
#
# Bright/noisy material.
# ============================================================

harsh_score = (
    0.30 * z_centroid +
    0.30 * z_flatness +
    0.20 * z_zcr +
    0.20 * z_loud
)


# ============================================================
# DRUM RUN
#
# Repeated LF onsets across a four-second window.
# ============================================================

positive_low_onset = np.maximum(
    z_low_onset,
    0
)


drum_window = max(
    1,
    int(4.0 * frame_rate)
)


drum_density = np.convolve(
    positive_low_onset,
    np.ones(drum_window) / drum_window,
    mode="same"
)


drum_score = (
    0.60 * robust_z(drum_density) +
    0.40 * z_low
)


# ============================================================
# SWELL
#
# Deliberately slow.
#
# This is designed to ignore many instantaneous crashes and
# instead favor energy that rises over several seconds.
# ============================================================

smooth_sigma = max(
    1,
    1.5 * frame_rate
)


smooth_loud = gaussian_filter1d(
    loud_db,
    sigma=smooth_sigma
)


gradient = np.gradient(
    smooth_loud
)


positive_gradient = np.maximum(
    gradient,
    0
)


swell_score = gaussian_filter1d(
    robust_z(positive_gradient),
    sigma=max(
        1,
        0.75 * frame_rate
    )
)


# Penalize instantaneous transients.

swell_score -= (
    0.25 *
    np.maximum(z_onset, 0)
)


# ============================================================
# BARRAGE
#
# Sustained density of transients.
# ============================================================

positive_onset = np.maximum(
    z_onset,
    0
)


barrage_window = max(
    1,
    int(5.0 * frame_rate)
)


barrage_density = np.convolve(
    positive_onset,
    np.ones(barrage_window) / barrage_window,
    mode="same"
)


barrage_score = (
    0.60 * robust_z(barrage_density) +
    0.25 * z_loud +
    0.15 * robust_z(centroid)
)


# ============================================================
# ACOUSTIC BURDEN
#
# This is intentionally not "loudness".
#
# It combines amplitude, transients, low-frequency rhythmic
# activity and spectral roughness.
# ============================================================

burden = (
    0.25 * normalize01(loud_db) +
    0.20 * normalize01(onset) +
    0.20 * normalize01(drum_density) +
    0.15 * normalize01(centroid) +
    0.10 * normalize01(flatness) +
    0.10 * normalize01(barrage_density)
)


# Smooth burden slightly for structural analysis.

burden_smooth = gaussian_filter1d(
    burden,
    sigma=max(
        1,
        0.5 * frame_rate
    )
)


# ============================================================
# Candidate peaks
# ============================================================

def get_peaks(
    score,
    percentile,
    minimum_distance_seconds
):

    threshold = np.nanpercentile(
        score,
        percentile
    )

    distance = max(
        1,
        int(
            minimum_distance_seconds *
            frame_rate
        )
    )

    peaks, _ = find_peaks(
        score,
        height=threshold,
        distance=distance
    )

    return peaks


impact_peaks = get_peaks(
    impact_score,
    98.5,
    0.75
)


drum_peaks = get_peaks(
    drum_score,
    97.5,
    4.0
)


swell_peaks = get_peaks(
    swell_score,
    97.5,
    5.0
)


harsh_peaks = get_peaks(
    harsh_score,
    98.0,
    3.0
)


# ============================================================
# Sustained regions
# ============================================================

barrage_threshold = np.percentile(
    barrage_score,
    85
)

high_load_threshold = np.percentile(
    burden_smooth,
    80
)

quiet_threshold = np.percentile(
    burden_smooth,
    25
)


barrage_regions = contiguous_regions(
    barrage_score > barrage_threshold,
    times,
    minimum_duration=3.0
)


high_load_regions = contiguous_regions(
    burden_smooth > high_load_threshold,
    times,
    minimum_duration=4.0
)


recovery_regions = contiguous_regions(
    burden_smooth < quiet_threshold,
    times,
    minimum_duration=5.0
)


# ============================================================
# Event table
# ============================================================

events = []


def add_peak_events(
    label,
    score,
    peaks
):

    for p in peaks:

        events.append({

            "type": label,

            "start_seconds":
                float(times[p]),

            "end_seconds":
                float(times[p]),

            "start":
                timestamp(times[p]),

            "end":
                timestamp(times[p]),

            "duration":
                0.0,

            "score":
                float(score[p]),

            "loudness_db":
                float(loud_db[p]),

            "low_db":
                float(low_db[p]),

            "center_advantage_db":
                float(
                    center_advantage[p]
                ),
        })


def add_regions(
    label,
    score,
    regions
):

    for start, end, t0, t1 in regions:

        section = slice(
            start,
            end
        )

        events.append({

            "type":
                label,

            "start_seconds":
                float(t0),

            "end_seconds":
                float(t1),

            "start":
                timestamp(t0),

            "end":
                timestamp(t1),

            "duration":
                float(t1 - t0),

            "score":
                float(
                    np.mean(
                        score[section]
                    )
                ),

            "loudness_db":
                float(
                    np.mean(
                        loud_db[section]
                    )
                ),

            "low_db":
                float(
                    np.mean(
                        low_db[section]
                    )
                ),

            "center_advantage_db":
                float(
                    np.mean(
                        center_advantage[
                            section
                        ]
                    )
                ),
        })


add_peak_events(
    "IMPACT",
    impact_score,
    impact_peaks
)

add_peak_events(
    "DRUM_RUN",
    drum_score,
    drum_peaks
)

add_peak_events(
    "SWELL",
    swell_score,
    swell_peaks
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
    burden_smooth,
    high_load_regions
)

add_regions(
    "RECOVERY",
    -burden_smooth,
    recovery_regions
)


events_df = pd.DataFrame(events)

events_df = events_df.sort_values(
    [
        "start_seconds",
        "type"
    ]
)


events_df.to_csv(
    out / "events.csv",
    index=False
)


# ============================================================
# Frame-level feature table
# ============================================================

df["impact_score"] = impact_score
df["drum_score"] = drum_score
df["swell_score"] = swell_score
df["harsh_score"] = harsh_score
df["barrage_score"] = barrage_score
df["burden"] = burden_smooth

df["center_advantage_db"] = (
    center_advantage
)


df.to_csv(
    out / "frames.csv",
    index=False
)


# ============================================================
# Per-second timeline
# ============================================================

df["second"] = np.floor(
    df["time"]
).astype(int)


timeline = (
    df.groupby("second")
      .mean(numeric_only=True)
      .reset_index()
)


timeline["timestamp"] = (
    timeline["second"]
    .map(timestamp)
)


timeline.to_csv(
    out / "timeline.csv",
    index=False
)


# ============================================================
# Recovery statistics
# ============================================================

recovery_seconds = sum(
    t1 - t0
    for _, _, t0, t1
    in recovery_regions
)


high_load_seconds = sum(
    t1 - t0
    for _, _, t0, t1
    in high_load_regions
)


barrage_seconds = sum(
    t1 - t0
    for _, _, t0, t1
    in barrage_regions
)


# Gaps between recovery regions.

recovery_gaps = []

previous_end = 0.0

for _, _, t0, t1 in recovery_regions:

    if t0 > previous_end:
        recovery_gaps.append(
            t0 - previous_end
        )

    previous_end = t1


if previous_end < duration:
    recovery_gaps.append(
        duration - previous_end
    )


# ============================================================
# Summary
# ============================================================

summary_lines = [

    f"Source: {source}",

    f"Duration: {timestamp(duration)}",

    f"Source channels: {channels}",

    f"Analysis sample rate: {broad_sr} Hz",

    f"Chunk size: {args.chunk:.1f} s",

    "",

    f"Impact candidates: {len(impact_peaks)}",

    f"Drum-run candidates: {len(drum_peaks)}",

    f"Swell candidates: {len(swell_peaks)}",

    f"Harsh candidates: {len(harsh_peaks)}",

    "",

    f"Barrage regions: {len(barrage_regions)}",

    f"High-load regions: {len(high_load_regions)}",

    f"Recovery regions: {len(recovery_regions)}",

    "",

    (
        "Barrage time: "
        f"{barrage_seconds:.1f} s "
        f"({100*barrage_seconds/duration:.1f}%)"
    ),

    (
        "High-load time: "
        f"{high_load_seconds:.1f} s "
        f"({100*high_load_seconds/duration:.1f}%)"
    ),

    (
        "Recovery time: "
        f"{recovery_seconds:.1f} s "
        f"({100*recovery_seconds/duration:.1f}%)"
    ),
]


if recovery_gaps:

    summary_lines.extend([

        "",

        (
            "Median interval without qualifying recovery: "
            f"{np.median(recovery_gaps):.1f} s"
        ),

        (
            "Longest interval without qualifying recovery: "
            f"{np.max(recovery_gaps):.1f} s"
        ),
    ])


summary = "\n".join(
    summary_lines
) + "\n"


(out / "summary.txt").write_text(
    summary
)


print(summary)


# ============================================================
# Plots
# ============================================================

minutes = times / 60.0


def save_plot(
    values,
    title,
    ylabel,
    filename
):

    plt.figure(
        figsize=(18, 5)
    )

    plt.plot(
        minutes,
        values,
        linewidth=0.8
    )

    plt.xlabel(
        "Movie time (minutes)"
    )

    plt.ylabel(
        ylabel
    )

    plt.title(
        title
    )

    plt.tight_layout()

    plt.savefig(
        out / filename,
        dpi=160
    )

    plt.close()


save_plot(
    loud_db,
    "Drive Through Fire — Loudness",
    "dBFS",
    "01-loudness.png"
)


save_plot(
    onset,
    "Drive Through Fire — Acoustic Transients",
    "Onset strength",
    "02-transients.png"
)


save_plot(
    drum_score,
    "Drive Through Fire — Low-Frequency Drum Activity",
    "Drum-run score",
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
    burden_smooth,
    "Drive Through Fire — Acoustic Burden",
    "Burden",
    "07-burden.png"
)


save_plot(
    center_advantage,
    "Drive Through Fire — Center-Channel Advantage",
    "Center minus non-center (dB)",
    "08-center-advantage.png"
)


# ============================================================
# Recovery visualization
# ============================================================

plt.figure(
    figsize=(18, 5)
)

plt.plot(
    minutes,
    burden_smooth,
    linewidth=0.8
)


for _, _, t0, t1 in recovery_regions:

    plt.axvspan(
        t0 / 60,
        t1 / 60,
        alpha=0.18
    )


plt.xlabel(
    "Movie time (minutes)"
)

plt.ylabel(
    "Acoustic burden"
)

plt.title(
    "Drive Through Fire — Recovery Windows"
)

plt.tight_layout()

plt.savefig(
    out / "09-recovery.png",
    dpi=160
)

plt.close()


# ============================================================
# Combined structural map
# ============================================================

# Normalize only for visualization.

plot_drum = normalize01(
    drum_score
)

plot_swell = normalize01(
    swell_score
)

plot_barrage = normalize01(
    barrage_score
)

plot_burden = normalize01(
    burden_smooth
)


plt.figure(
    figsize=(18, 6)
)


plt.plot(
    minutes,
    plot_drum + 3,
    label="Drum activity"
)

plt.plot(
    minutes,
    plot_swell + 2,
    label="Swells"
)

plt.plot(
    minutes,
    plot_barrage + 1,
    label="Barrage"
)

plt.plot(
    minutes,
    plot_burden,
    label="Burden"
)


plt.yticks(
    [0.5, 1.5, 2.5, 3.5],
    [
        "Burden",
        "Barrage",
        "Swells",
        "Drums"
    ]
)


plt.xlabel(
    "Movie time (minutes)"
)

plt.title(
    "Drive Through Fire — Sound Grammar"
)

plt.tight_layout()

plt.savefig(
    out / "10-sound-grammar.png",
    dpi=160
)

plt.close()


# ============================================================
# Top candidate report
# ============================================================

report_lines = []


for event_type in [
    "DRUM_RUN",
    "SWELL",
    "IMPACT",
    "HARSH"
]:

    subset = events_df[
        events_df["type"] == event_type
    ]

    subset = subset.sort_values(
        "score",
        ascending=False
    ).head(20)


    report_lines.append(
        f"\n{event_type}\n"
        + "=" * len(event_type)
    )


    for _, row in subset.iterrows():

        report_lines.append(
            f"{row['start']}  "
            f"score={row['score']:.2f}  "
            f"level={row['loudness_db']:.1f} dB  "
            f"low={row['low_db']:.1f} dB  "
            f"centerΔ={row['center_advantage_db']:.1f} dB"
        )


(out / "top-candidates.txt").write_text(
    "\n".join(report_lines) + "\n"
)


# ============================================================
# Finish
# ============================================================

print("Written:")
print()
print("  summary.txt")
print("  top-candidates.txt")
print("  events.csv")
print("  timeline.csv")
print("  frames.csv")
print()
print("  01-loudness.png")
print("  02-transients.png")
print("  03-drum-runs.png")
print("  04-swells.png")
print("  05-barrage.png")
print("  06-harshness.png")
print("  07-burden.png")
print("  08-center-advantage.png")
print("  09-recovery.png")
print("  10-sound-grammar.png")
print()


if args.keep_stems:
    print(
        "Analysis stems retained in:",
        stem_dir
    )
else:
    temp.cleanup()


print()
print("Done.")
