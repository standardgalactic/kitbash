#!/usr/bin/env bash
set -euo pipefail

INPUT_BIB="time-irreversibility-old.bib"
OUTPUT_BIB="time-irreversibility.bib"
CONFIG="bibtool.rsc"

echo "Running bibtool (SAFE MODE)"
echo "Input:  ${INPUT_BIB}"
echo "Output: ${OUTPUT_BIB}"
echo "Config: ${CONFIG}"

if [[ ! -f "$INPUT_BIB" ]]; then
  echo "Error: Input bibliography '$INPUT_BIB' not found."
  exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
  echo "Error: bibtool config '$CONFIG' not found."
  exit 1
fi

# Run bibtool
bibtool -s -r "$CONFIG" -o "$OUTPUT_BIB" "$INPUT_BIB"

# Fail loudly if bibtool commented anything out
if grep -q '^###' "$OUTPUT_BIB"; then
  echo "ERROR: BibTool commented out entries!"
  echo "Aborting to prevent data loss."
  exit 1
fi

echo "Bibliography cleaned successfully."
