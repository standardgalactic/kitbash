#!/usr/bin/env python3

import os, json, nltk
from nltk import ngrams
from collections import Counter
from tqdm import tqdm
from multiprocessing import Pool, cpu_count

nltk.download('punkt', quiet=True)

# parameters
NGRAM_N = 2
WORKERS = max(cpu_count() - 1, 1)  # leave 1 core free

STATE_DIR = "state"
DONE_FILE = os.path.join(STATE_DIR, "done.txt")
OUT_FILE = os.path.join(STATE_DIR, "ngrams.jsonl")

os.makedirs(STATE_DIR, exist_ok=True)

# Load checkpoint of processed files
if os.path.exists(DONE_FILE):
    with open(DONE_FILE) as f:
        done = set(x.strip() for x in f if x.strip())
else:
    done = set()

def extract_ngrams_single(fname):
    """Return (filename, {ngram: count})"""
    counter = Counter()
    try:
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                tokens = nltk.word_tokenize(line.lower())
                for gram in ngrams(tokens, NGRAM_N):
                    counter["_".join(gram)] += 1
        # keep only top N terms
                TOPN = 50
                top_counts = counter.most_common(TOPN)
                return fname, dict(top_counts)

    except Exception as e:
        # Ensure one bad file doesn't kill everything
        return fname, {"__error": str(e)}

# Collect unapplied files
files = sorted([x for x in os.listdir(".") if x.lower().endswith(".txt")])
files_to_process = [f for f in files if f not in done]

# Multiprocessing pool
with Pool(WORKERS) as pool, \
     open(OUT_FILE, "a", encoding="utf-8") as out, \
     open(DONE_FILE, "a", encoding="utf-8") as done_out:

    # imap_unordered yields (filename, ngram_dict)
    for fname, counts in tqdm(
            pool.imap_unordered(extract_ngrams_single, files_to_process),
            total=len(files_to_process),
            desc="Building ngrams (mp)"
        ):
        # Write JSON line
        record = {"file": fname, "ngrams": counts}
        out.write(json.dumps(record) + "\n")
        out.flush()

        # Mark complete
        done_out.write(fname + "\n")
        done_out.flush()

        done.add(fname)

