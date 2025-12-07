#!/bin/bash

set -e

echo "=== Building ngrams incrementally ==="
python3 build_ngrams.py

echo "=== Clustering (KMeans + HDBSCAN + LDA) ==="
python3 cluster.py

echo "=== Done ==="

