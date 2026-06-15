#!/usr/bin/env bash
# Paperbot Parliament v1
# Architecture: Document → Claims → Offices → Reports → Distinction Ledger
# Each chunk passes through six constitutional offices before archiving.

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

MODEL="${PAPERBOT_MODEL:-granite3.2:8b}"
CHUNK_LINES="${PAPERBOT_CHUNK:-250}"
CYCLES="${PAPERBOT_CYCLES:-1}"   # revision cycles per chunk

ROOT="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$ROOT/source"
REPORT_DIR="$ROOT/reports"
PROMPT_DIR="$ROOT/prompts"
ARCHIVE_DIR="$ROOT/archive"
LEDGER="$ROOT/distinction.ledger"
PROGRESS="$ROOT/progress.log"

mkdir -p "$REPORT_DIR" "$ARCHIVE_DIR/accepted" "$ARCHIVE_DIR/rejected" "$ARCHIVE_DIR/revisions"

# ── Logging ───────────────────────────────────────────────────────────────────

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$PROGRESS"; }

# ── Core: run a single office ─────────────────────────────────────────────────
# Usage: run_office <office_name> <input_file> <output_file>
# The office prompt is prepended to the input so the model sees both.

run_office() {
    local office="$1"
    local input="$2"
    local output="$3"

    log "  ↳ $office"

    {
        cat "$PROMPT_DIR/$office.txt"
        echo
        echo "---"
        echo
        cat "$input"
    } | ollama run "$MODEL" > "$output" 2>/dev/null

    echo "" >> "$output"
}

# ── Stage 1: extract claims from a raw chunk ──────────────────────────────────

extract_claims() {
    local input="$1"
    local output="$2"

    log "  ↳ claims extractor"

    {
        cat "$PROMPT_DIR/claims.txt"
        echo
        echo "---"
        echo
        cat "$input"
    } | ollama run "$MODEL" > "$output" 2>/dev/null
}

# ── Stage 2: run all offices on the claims file ───────────────────────────────

run_all_offices() {
    local claims="$1"
    local workdir="$2"
    local prefix="$3"

    run_office nitpicker  "$claims" "$workdir/${prefix}.nitpicker"
    run_office skeptic    "$claims" "$workdir/${prefix}.skeptic"
    run_office archivist  "$claims" "$workdir/${prefix}.archivist"
    run_office synthesist "$claims" "$workdir/${prefix}.synthesist"
    run_office auditor    "$claims" "$workdir/${prefix}.auditor"
}

# ── Stage 3: update distinction ledger ───────────────────────────────────────
# Ask the Synthesist to extract any new Distinction X ≠ Y pairs.

update_ledger() {
    local claims="$1"

    local ledger_prompt="From the following claims, extract any distinctions of the form:
X ≠ Y  (two things being distinguished)
X ≢ Y  (two things being separated conceptually)

Return only pairs, one per line, in the format:
  DISTINCTION: X ≠ Y

If none, return nothing."

    {
        echo "$ledger_prompt"
        echo
        echo "---"
        echo
        cat "$claims"
    } | ollama run "$MODEL" 2>/dev/null >> "$LEDGER"
}

# ── Stage 4: assemble chunk report ───────────────────────────────────────────

assemble_report() {
    local workdir="$1"
    local prefix="$2"
    local report="$3"

    {
        echo "# Parliament Report: $prefix"
        echo
        echo "## Claims"
        cat "$workdir/${prefix}.claims"
        echo
        for office in nitpicker skeptic archivist synthesist auditor; do
            echo "## $office"
            cat "$workdir/${prefix}.$office" 2>/dev/null || echo "(no output)"
            echo
        done
        echo "---"
        echo
    } >> "$report"
}

# ── Process one source file ───────────────────────────────────────────────────

process_file() {
    local file="$1"
    local stem
    stem=$(basename "$file" .txt)

    local workdir="$REPORT_DIR/$stem"
    local report="$workdir/parliament_report.md"

    mkdir -p "$workdir"

    log "Processing: $stem"

    # Split into chunks
    split -l "$CHUNK_LINES" "$file" "$workdir/chunk_"

    echo "# Paperbot Parliament — $stem" > "$report"
    echo "Generated: $(date)" >> "$report"
    echo >> "$report"

    for chunk in "$workdir"/chunk_*; do
        [ -f "$chunk" ] || continue
        local id
        id=$(basename "$chunk")
        local prefix="$id"

        log "Chunk: $id"

        # Cycle loop — default 1 pass, set PAPERBOT_CYCLES=3 for revision
        local cycle=1
        local claims="$workdir/${prefix}.claims"

        extract_claims "$chunk" "$claims"
        update_ledger "$claims"

        while [ "$cycle" -le "$CYCLES" ]; do
            log "  Cycle $cycle/$CYCLES"
            run_all_offices "$claims" "$workdir" "${prefix}_c${cycle}"

            # On cycles > 1, feed office output back into a revised claims file
            if [ "$cycle" -lt "$CYCLES" ]; then
                local revision="$workdir/${prefix}_c${cycle}_revision.txt"
                {
                    echo "You are the Revision Office."
                    echo "Given the original claims and the office findings below,"
                    echo "produce a revised and improved claims list."
                    echo "Remove claims that failed auditor review."
                    echo "Flag claims that need evidence."
                    echo "Preserve claims that survived skeptic scrutiny."
                    echo
                    echo "--- ORIGINAL CLAIMS ---"
                    cat "$claims"
                    echo
                    for office in nitpicker skeptic auditor; do
                        echo "--- $office ---"
                        cat "$workdir/${prefix}_c${cycle}.$office" 2>/dev/null || true
                        echo
                    done
                } | ollama run "$MODEL" > "$revision" 2>/dev/null
                claims="$revision"
            fi

            cycle=$((cycle + 1))
        done

        # Assemble this chunk into the report
        {
            echo "## Chunk: $id"
            echo
            echo "### Claims"
            cat "$workdir/${prefix}.claims"
            echo

            local last_cycle=$((CYCLES))
            for office in nitpicker skeptic archivist synthesist auditor; do
                echo "### $office"
                cat "$workdir/${prefix}_c${last_cycle}.$office" 2>/dev/null || echo "(no output)"
                echo
            done

            echo "---"
            echo
        } >> "$report"

        log "  ✓ $id complete"
    done

    log "Report: $report"
}

# ── Main ──────────────────────────────────────────────────────────────────────

log "Paperbot Parliament started"
log "Model: $MODEL  Chunk: $CHUNK_LINES lines  Cycles: $CYCLES"
log "Source: $SOURCE_DIR"

touch "$LEDGER"

found=0
for file in "$SOURCE_DIR"/*.txt; do
    [ -f "$file" ] || continue
    process_file "$file"
    found=$((found + 1))
done

if [ "$found" -eq 0 ]; then
    log "No .txt files found in $SOURCE_DIR"
    log "Place source documents there and run again."
    exit 1
fi

log "Distinction ledger: $LEDGER"
log "Parliament session complete."
