#!/bin/bash
# Usage: ./fix_arrows.sh essay.tex

FILE="$1"

if [[ -z "$FILE" ]]; then
  echo "Usage: $0 <tex-file>"
  exit 1
fi

# Insert the macro definitions after the last \usepackage line if not present
if ! grep -q "\\newcommand{\\ra}" "$FILE"; then
  # Make a backup
  cp "$FILE" "$FILE.bak"

  # Find the last \usepackage line and insert after it
  awk '
    /\\usepackage/ { last=NR }
    { lines[NR]=$0 }
    END {
      for(i=1;i<=NR;i++) {
        print lines[i]
        if(i==last) {
          print "% For Unicode arrows"
          print "\\newcommand{\\ra}{\\Rightarrow}"
          print "\\newcommand{\\lra}{\\Leftrightarrow}"
          print "\\newcommand{\\lr}{\\leftrightarrow}"
          print "\\newcommand{\\neqsym}{\\neq}"
        }
      }
    }
  ' "$FILE" > "$FILE.tmp" && mv "$FILE.tmp" "$FILE"
fi

# Replace Unicode symbols with LaTeX macros
sed -i \
  -e 's/⇔/\\lra/g' \
  -e 's/⇒/\\ra/g' \
  -e 's/↔/\\lr/g' \
  -e 's/≠/\\neqsym/g' \
  "$FILE"

echo "Done. Backup saved as $FILE.bak"
