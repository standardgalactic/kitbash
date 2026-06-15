#!/usr/bin/env bash
set -euo pipefail

MODEL="granite3.2:8b"
CHUNK_SIZE=282
CONTEXT_LINES=300

PROGRESS_FILE="progress.log"
PARLIAMENT_FILE="parliament.txt"
LEDGER_FILE="distinctions.log"

ROOT="$(pwd)"

touch "$ROOT/$PROGRESS_FILE"
touch "$ROOT/$PARLIAMENT_FILE"
touch "$ROOT/$LEDGER_FILE"

is_processed() {
    grep -Fxq "$1" "$ROOT/$PROGRESS_FILE" 2>/dev/null
}

get_context() {
    [ -f "$ROOT/$PARLIAMENT_FILE" ] && tail -n "$CONTEXT_LINES" "$ROOT/$PARLIAMENT_FILE"
}

run_bot() {
    local bot="$1"
    local prompt="$2"
    local input_file="$3"

    {
        echo
        echo "## $bot"
        echo
        cat constitution.txt
        echo
        cat movement.txt
        echo
        get_context
        echo
        cat "$input_file"
    } | ollama run "$MODEL" "$prompt" >> "$ROOT/$PARLIAMENT_FILE"

    echo >> "$ROOT/$PARLIAMENT_FILE"
}

process_chunk() {
    local chunk="$1"

    run_bot "Summarizer" \
      "Summarize this chunk in detail." "$chunk"

    run_bot "Nitpicker" \
      "Identify ambiguities, undefined terms, and hidden assumptions." "$chunk"

    run_bot "Skeptic" \
      "Provide the strongest objections and criticisms." "$chunk"

    run_bot "Archivist" \
      "Identify historical precedents and related ideas." "$chunk"

    run_bot "Synthesist" \
      "Connect this material to other theories and domains." "$chunk"

    run_bot "Admissibility Auditor" \
      "Identify unsupported transitions and reasoning gaps." "$chunk"
}

process_file() {
    local file="$1"
    local filename
    filename=$(basename "$file")

    if is_processed "$filename"; then
        return
    fi

    temp_dir=$(mktemp -d)
    split -l "$CHUNK_SIZE" "$file" "$temp_dir/chunk_"

    for chunk in "$temp_dir"/chunk_*; do
        [ -f "$chunk" ] || continue
        process_chunk "$chunk"
    done

    rm -rf "$temp_dir"
    echo "$filename" >> "$ROOT/$PROGRESS_FILE"
}

find . -type f -name "*.txt" \
    ! -name "$PARLIAMENT_FILE" \
    ! -name "$LEDGER_FILE" \
    ! -name "$PROGRESS_FILE" | while read -r file; do
        process_file "$file"
done
