#!/usr/bin/env python3

import json
import os
import html

from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation

import hdbscan   # AUTO CLUSTER COUNT
import numpy as np

STATE_DIR = "state"
INPUT = os.path.join(STATE_DIR, "ngrams.jsonl")

# KMeans parameters
CLUSTERS = 15

# LDA parameters
LDA_TOPICS = 15
SHOW_LDA_TOP_WORDS = 15

# -------------------------------------------------------------------
# Load ngram data
# -------------------------------------------------------------------
ngrams = []
filenames = []

with open(INPUT, "r", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        filenames.append(rec["file"])
        ngrams.append(rec["ngrams"])

vec = DictVectorizer()
X = vec.fit_transform(ngrams)

tfidf = TfidfTransformer()
Xtfidf = tfidf.fit_transform(X)

feature_names = vec.get_feature_names_out()

# ===================================================================
# KMEANS
# ===================================================================
kmeans = KMeans(n_clusters=CLUSTERS, random_state=0, n_init="auto")
labels_k = kmeans.fit_predict(Xtfidf)

clusters_k = {}
for label, fname in zip(labels_k, filenames):
    clusters_k.setdefault(label, []).append(fname)

print("\n=======================================")
print("KMEANS CLUSTERS")
print("=======================================")

for label, files in clusters_k.items():
    print(f"\n--- Cluster {label} ---")
    for f in files:
        print("   ", f)

# Save KMeans cluster assignment JSON
out_k = os.path.join(STATE_DIR, "clusters-kmeans.json")
with open(out_k, "w", encoding="utf-8") as f:
    json.dump(
        [{"cluster": int(l), "file": fn} for l, fn in zip(labels_k, filenames)],
        f,
        indent=2
    )
print(f"KMeans written to {out_k}")

# -------------------------------------------------------------------
# Top terms per KMeans cluster (TF-IDF)
# -------------------------------------------------------------------
top_terms_out = os.path.join(STATE_DIR, "cluster-top-terms.txt")
cluster_top_terms = {}  # for HTML report

with open(top_terms_out, "w", encoding="utf-8") as outf:
    outf.write("=== Top TF-IDF Terms per KMeans Cluster ===\n")

    for c in range(CLUSTERS):
        idx = [i for i, lab in enumerate(labels_k) if lab == c]
        if not idx:
            continue

        cluster_vec = np.asarray(Xtfidf[idx].mean(axis=0)).ravel()
        top_indices = cluster_vec.argsort()[::-1][:SHOW_LDA_TOP_WORDS]
        top_feats = [feature_names[i] for i in top_indices]

        cluster_top_terms[c] = top_feats

        outf.write(f"\n--- Cluster {c} ---\n")
        for term in top_feats:
            outf.write(term + "\n")

print(f"Top terms per cluster saved to: {top_terms_out}")

# ===================================================================
# HDBSCAN (AUTO cluster count)
# ===================================================================
hdb = hdbscan.HDBSCAN(
    min_cluster_size=10,   # tune if you like
    min_samples=3,
    metric='euclidean',
    cluster_selection_method='eom'
)

labels_h = hdb.fit_predict(Xtfidf)

clusters_h = {}
for label, fname in zip(labels_h, filenames):
    clusters_h.setdefault(label, []).append(fname)

print("\n=======================================")
print("HDBSCAN CLUSTERS (AUTO)")
print("=======================================")

for label, files in clusters_h.items():
    print(f"\n--- Cluster {label} ---")  # -1 == noise
    for f in files:
        print("   ", f)

out_h = os.path.join(STATE_DIR, "clusters-hdbscan.json")
with open(out_h, "w", encoding="utf-8") as f:
    json.dump(
        [{"cluster": int(l), "file": fn} for l, fn in zip(labels_h, filenames)],
        f,
        indent=2
    )
print(f"HDBSCAN written to {out_h}")

# ===================================================================
# LDA topics
# ===================================================================
print("\n=======================================")
print("LDA TOPICS")
print("=======================================")

lda = LatentDirichletAllocation(
    n_components=LDA_TOPICS,
    random_state=0,
    learning_method='batch'
)

lda.fit(X)

topics_out = os.path.join(STATE_DIR, "topics.txt")
lda_topics_terms = {}  # for HTML

with open(topics_out, "w", encoding="utf-8") as f:
    for topic_idx, topic in enumerate(lda.components_):
        top_idx = topic.argsort()[:-SHOW_LDA_TOP_WORDS - 1:-1]
        words = [feature_names[i] for i in top_idx]
        lda_topics_terms[topic_idx] = words

        print(f"\n--- Topic {topic_idx} ---")
        for w in words:
            print(w)

        f.write(f"\n--- Topic {topic_idx} ---\n")
        for w in words:
            f.write(w + "\n")

print(f"LDA topics written to {topics_out}")

# ===================================================================
# HTML REPORT
# ===================================================================
report_path = os.path.join(STATE_DIR, "report.html")

def esc(s: str) -> str:
    return html.escape(str(s))

with open(report_path, "w", encoding="utf-8") as rep:
    rep.write("<!DOCTYPE html>\n<html lang='en'>\n<head>\n")
    rep.write("<meta charset='UTF-8'>\n")
    rep.write("<title>Text Clustering Report</title>\n")
    rep.write("""
<style>
body { font-family: sans-serif; margin: 2rem; max-width: 1000px; }
h1, h2, h3 { font-family: sans-serif; }
code { font-family: monospace; }
.section { margin-bottom: 2rem; }
.cluster-box, .topic-box {
    border: 1px solid #ccc;
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 4px;
}
.cluster-header { font-weight: bold; margin-bottom: 0.5rem; }
ul { margin-top: 0.3rem; }
.small { color: #666; font-size: 0.9em; }
.badge { display: inline-block; padding: 0.1rem 0.4rem;
         border-radius: 3px; font-size: 0.8em; background: #eee; }
.badge-noise { background: #f8d7da; color: #721c24; }
</style>
</head>
<body>
""")

    rep.write("<h1>Text Clustering Report</h1>\n")
    rep.write("<p class='small'>Generated from n-gram features in "
              f"<code>{esc(INPUT)}</code>.</p>\n")

    # ----------------- KMeans Section -----------------
    rep.write("<div class='section'>\n<h2>KMeans Clusters</h2>\n")
    rep.write(f"<p class='small'>Number of clusters: {CLUSTERS}</p>\n")

    for c in sorted(clusters_k.keys()):
        files = clusters_k[c]
        terms = cluster_top_terms.get(c, [])

        rep.write("<div class='cluster-box'>\n")
        rep.write(f"<div class='cluster-header'>Cluster {c}</div>\n")

        rep.write("<div><strong>Top terms:</strong><ul>\n")
        for t in terms:
            rep.write(f"<li>{esc(t)}</li>\n")
        rep.write("</ul></div>\n")

        rep.write("<div><strong>Files:</strong><ul>\n")
        for fname in files:
            rep.write(f"<li>{esc(fname)}</li>\n")
        rep.write("</ul></div>\n")

        rep.write("</div>\n")

    rep.write("</div>\n")

    # ----------------- HDBSCAN Section -----------------
    rep.write("<div class='section'>\n<h2>HDBSCAN Clusters (Auto)</h2>\n")
    rep.write("<p class='small'>Cluster label <code>-1</code> = noise/outliers.</p>\n")

    for label in sorted(clusters_h.keys()):
        files = clusters_h[label]
        badge_class = "badge badge-noise" if label == -1 else "badge"
        rep.write("<div class='cluster-box'>\n")
        rep.write("<div class='cluster-header'>"
                  f"HDBSCAN Cluster {label} "
                  f"<span class='{badge_class}'>size: {len(files)}</span>"
                  "</div>\n")

        rep.write("<div><strong>Files:</strong><ul>\n")
        for fname in files:
            rep.write(f"<li>{esc(fname)}</li>\n")
        rep.write("</ul></div>\n")

        rep.write("</div>\n")

    rep.write("</div>\n")

    # ----------------- LDA Topics Section -----------------
    rep.write("<div class='section'>\n<h2>LDA Topics</h2>\n")
    rep.write(f"<p class='small'>Number of topics: {LDA_TOPICS}</p>\n")

    for topic_idx in sorted(lda_topics_terms.keys()):
        words = lda_topics_terms[topic_idx]
        rep.write("<div class='topic-box'>\n")
        rep.write(f"<div class='cluster-header'>Topic {topic_idx}</div>\n")
        rep.write("<div><strong>Top words:</strong><ul>\n")
        for w in words:
            rep.write(f"<li>{esc(w)}</li>\n")
        rep.write("</ul></div>\n")
        rep.write("</div>\n")

    rep.write("</div>\n")

    rep.write("</body></html>\n")

print(f"HTML report written to: {report_path}")
print("\n=== Done ===")

