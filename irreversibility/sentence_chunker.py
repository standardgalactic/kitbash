#!/usr/bin/env python3
"""
sentence_chunker.py

Read text from stdin and emit coherent chunks ending at sentence boundaries.
"""

import sys
import re

MAX_CHARS = 1200

text = sys.stdin.read().strip()

# Normalize whitespace
text = re.sub(r'\s+', ' ', text)

# Simple sentence splitter (robust enough without NLP deps)
sentences = re.split(r'(?<=[.!?])\s+', text)

chunks = []
current = ""

for sent in sentences:
    if not sent:
        continue

    # If adding this sentence would overflow, flush
    if len(current) + len(sent) > MAX_CHARS:
        if current:
            chunks.append(current.strip())
            current = sent
        else:
            # Single long sentence fallback
            chunks.append(sent[:MAX_CHARS])
            current = sent[MAX_CHARS:]
    else:
        current += " " + sent

if current.strip():
    chunks.append(current.strip())

# Emit with delimiter
for chunk in chunks:
    print("<<<CHUNK>>>")
    print(chunk)

