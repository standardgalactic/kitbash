#!/usr/bin/env bash
# Runs every verification script of the book from this folder and reports status and time.
# Scripts that import lawnmodel.py must be run from this folder without python's -I flag.
# Set SKIP to a space-separated list of script names (without .py) to leave some out.
cd "$(dirname "$0")" || exit 1
fail=0
for f in verify_ch01 verify_ch02 verify_ch03 verify_ch04 verify_ch05 verify_ch06 verify_ch07 verify_ch08 \
         verify_ch09 verify_ch10 verify_ch11 verify_ch12 verify_ch13 verify_ch14 verify_ch15 verify_ch16 \
         verify_ch17 verify_ch17_shared verify_appA; do
  case " $SKIP " in *" $f "*) echo "$f skipped"; continue;; esac
  start=$(date +%s)
  python3 "$f.py" > "$f.log" 2>&1
  rc=$?
  echo "$f exit=$rc seconds=$(( $(date +%s) - start )) output=$f.log"
  [ $rc -ne 0 ] && fail=1
done
exit $fail
