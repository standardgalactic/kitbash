#!/usr/bin/env bash

set -euo pipefail

SOURCE="template-source.tex"
TARGET="operator-ecology.tex"
LEDGER="line-history.tsv"

if [[ ! -f "$SOURCE" ]]; then
    echo "Missing source file: $SOURCE"
    exit 1
fi

touch "$TARGET"
touch "$LEDGER"

classify() {

    local line="$1"

    case "$line" in

        \\documentclass*)
            echo frontmatter ;;

        \\usepackage*)
            echo frontmatter ;;

        \\title*)
            echo frontmatter ;;

        \\author*)
            echo frontmatter ;;

        \\date*)
            echo frontmatter ;;

        \\maketitle*)
            echo frontmatter ;;

        \\tableofcontents*)
            echo frontmatter ;;

        \\begin\{document\}*)
            echo frontmatter ;;

        \\end\{document\}*)
            echo backmatter ;;

        \\chapter\{*)
            echo add-chapter ;;

        \\section\{*)
            echo add-section ;;

        \\subsection\{*)
            echo add-subsection ;;

        \\subsubsection\{*)
            echo add-subsubsection ;;

        \\begin\{definition\}*)
            echo define ;;

        \\begin\{theorem\}*)
            echo theorem ;;

        \\begin\{lemma\}*)
            echo lemma ;;

        \\begin\{corollary\}*)
            echo corollary ;;

        \\begin\{example\}*)
            echo example ;;

        \\begin\{proof\}*)
            echo proof ;;

        \\begin\{figure\}*)
            echo figure ;;

        \\includegraphics*)
            echo figure ;;

        \\begin\{table\}*)
            echo table ;;

        \\begin\{equation\}*)
            echo equation ;;

        \\begin\{align\}*)
            echo equation ;;

        *\\cite\{*|*\\citep\{*|*\\citet\{*)
            echo cite ;;

        \\bibliography*)
            echo bibliography ;;

        \\printbibliography*)
            echo bibliography ;;

        "")
            echo whitespace ;;

        %*)
            echo comment ;;

        *)
            echo prose ;;
    esac
}

SOURCE_LINES=$(wc -l < "$SOURCE")

while true
do
    TARGET_LINES=$(wc -l < "$TARGET")

    if (( TARGET_LINES >= SOURCE_LINES )); then
        break
    fi

    NEXT=$((TARGET_LINES + 1))

    LINE=$(sed -n "${NEXT}p" "$SOURCE")

    CATEGORY=$(classify "$LINE")

    printf '%s\n' "$LINE" >> "$TARGET"

    ID=$(printf "OE-%05d" "$NEXT")

    TIMESTAMP=$(date "+%Y-%m-%dT%H:%M:%S")

    printf "%s\t%s\t%s\t%s\n" \
        "$ID" \
        "$CATEGORY" \
        "$NEXT" \
        "$TIMESTAMP" \
        >> "$LEDGER"

    git add "$TARGET" "$LEDGER"

    if [[ "$CATEGORY" == "whitespace" ]]; then
        BODY="<blank line>"
    else
        BODY="$LINE"
    fi

    git commit \
        -m "$ID $CATEGORY" \
        -m "$BODY"

    echo "$ID $CATEGORY"
done

echo
echo "Finished."
echo "Lines processed: $SOURCE_LINES"
