#!/usr/bin/env bash

set -euo pipefail

###############################################################################

# Paperbot Parliament Prototype

#

# A flow-computing implementation of the Paperbot Parliament.

#

# Pipeline:

#

# Document

# -> Chunker

# -> Summarizer

# -> Nitpicker

# -> Skeptic

# -> Archivist

# -> Synthesist

# -> Admissibility Auditor

# -> Distinction Ledger

# -> Parliament Record

#

###############################################################################

MODEL="granite3.2:8b"

PROGRESS_FILE="progress.log"
PARLIAMENT_FILE="parliament.txt"
LEDGER_FILE="distinctions.log"

ROOT="$(pwd)"

###############################################################################

# Initialization

###############################################################################

touch "$ROOT/$PROGRESS_FILE"
touch "$ROOT/$PARLIAMENT_FILE"
touch "$ROOT/$LEDGER_FILE"

echo "Parliament started $(date)" >> "$ROOT/$PROGRESS_FILE"

###############################################################################

# Utility Functions

###############################################################################

is_processed() {
grep -Fxq "$1" "$ROOT/$PROGRESS_FILE"
}

append_section() {
local title="$1"

```
{
    echo
    echo "=================================================================="
    echo "$title"
    echo "=================================================================="
    echo
} >> "$ROOT/$PARLIAMENT_FILE"
```

}

get_context() {

```
if [ -f "$ROOT/$PARLIAMENT_FILE" ]; then
    tail -n 300 "$ROOT/$PARLIAMENT_FILE"
fi
```

}

get_ledger() {

```
if [ -f "$ROOT/$LEDGER_FILE" ]; then
    cat "$ROOT/$LEDGER_FILE"
fi
```

}

run_bot() {

```
local bot="$1"
local prompt="$2"
local input_file="$3"

echo "Running $bot"

{
    echo
    echo "## $bot"
    echo
} >> "$ROOT/$PARLIAMENT_FILE"

{
    echo "PARLIAMENT CONTEXT"
    echo
    get_context

    echo
    echo "DISTINCTION LEDGER"
    echo
    get_ledger

    echo
    echo "DOCUMENT CHUNK"
    echo
    cat "$input_file"

} | ollama run "$MODEL" "$prompt" \
  >> "$ROOT/$PARLIAMENT_FILE"

echo >> "$ROOT/$PARLIAMENT_FILE"
```

}

extract_distinctions() {

```
local input_file="$1"

{
    echo "Extract key distinctions, oppositions, separations,"
    echo "projection failures, conceptual contrasts, and"
    echo "important differentiations from the following text."
    echo
    cat "$input_file"

} | ollama run "$MODEL" \
  >> "$ROOT/$LEDGER_FILE"

echo >> "$ROOT/$LEDGER_FILE"
```

}

###############################################################################

# Constitutional Offices

###############################################################################

summarizer() {

```
run_bot \
    "Summarizer" \
    "Summarize this chunk in detail. Preserve all major claims, definitions, arguments, evidence, and conclusions." \
    "$1"
```

}

nitpicker() {

```
run_bot \
    "Nitpicker" \
    "Identify ambiguities, undefined terms, hidden assumptions, vague language, overloaded concepts, and distinctions that should be made explicit." \
    "$1"
```

}

skeptic() {

```
run_bot \
    "Skeptic" \
    "Provide the strongest possible objections, criticisms, counterexamples, failure modes, and alternative explanations." \
    "$1"
```

}

archivist() {

```
run_bot \
    "Archivist" \
    "Identify historical precedents, related theories, intellectual traditions, prior work, and conceptual ancestors." \
    "$1"
```

}

synthesist() {

```
run_bot \
    "Synthesist" \
    "Identify connections to other fields, frameworks, theories, mathematical structures, scientific domains, and philosophical traditions." \
    "$1"
```

}

auditor() {

```
run_bot \
    "Admissibility Auditor" \
    "Identify unsupported transitions, logical leaps, unjustified assumptions, missing intermediate steps, and conclusions that exceed premises." \
    "$1"
```

}

###############################################################################

# Chunk Processing

###############################################################################

process_chunk() {

```
local chunk="$1"

{
    echo
    echo "############################################################"
    echo "CHUNK $(basename "$chunk")"
    echo "############################################################"
    echo
} >> "$ROOT/$PARLIAMENT_FILE"

summarizer "$chunk"
nitpicker "$chunk"
skeptic "$chunk"
archivist "$chunk"
synthesist "$chunk"
auditor "$chunk"

extract_distinctions "$chunk"
```

}

###############################################################################

# File Processing

###############################################################################

process_file() {

```
local file="$1"

local filename
filename=$(basename "$file")

if is_processed "$filename"; then
    return
fi

echo "Processing $filename"

append_section "DOCUMENT: $filename"

local temp_dir
temp_dir=$(mktemp -d)

split -l 282 "$file" "$temp_dir/chunk_"

for chunk in "$temp_dir"/chunk_*; do

    [ -f "$chunk" ] || continue

    process_chunk "$chunk"

done

rm -rf "$temp_dir"

echo "$filename" >> "$ROOT/$PROGRESS_FILE"
```

}

###############################################################################

# Directory Traversal

###############################################################################

process_directory() {

```
local dir="$1"

echo "Scanning: $dir"

for file in "$dir"/*.txt; do

    [ -e "$file" ] || continue

    case "$(basename "$file")" in
        "$PARLIAMENT_FILE"|"$LEDGER_FILE"|"$PROGRESS_FILE")
            continue
            ;;
    esac

    process_file "$file"

done

for subdir in "$dir"/*/; do

    [ -d "$subdir" ] || continue

    process_directory "$subdir"

done
```

}

###############################################################################

# Main

###############################################################################

process_directory "$ROOT"

echo "Parliament completed $(date)" >> "$ROOT/$PROGRESS_FILE"

echo
echo "Done."
echo
echo "Parliament record:"
echo "  $PARLIAMENT_FILE"
echo
echo "Distinction ledger:"
echo "  $LEDGER_FILE"
