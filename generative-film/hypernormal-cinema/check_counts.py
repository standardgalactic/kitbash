#!/usr/bin/env python3
"""Regression check: runs the fast verification scripts and fails if a count that the manuscript states is
missing from their output. It covers headline counts of the quick scripts and is not a substitute for
reading the full output. Run from this folder:  python3 check_counts.py
"""
import subprocess, sys
EXPECT = {
    "verify_ch01.py": ["1,941,560,821,238", "perceptual editions before 494, after 238, removed 256", "take tuples before 204,800,000, after 102,400,000"],
    "verify_ch03.py": ["class tuples: 126", "consistent with some history: 112", "consistent with the script history h* (agreement with the story): 32"],
    "verify_ch12.py": ["take tuples after G 102400000", "premiere 494 after G 238 take tuples after G 57834"],
    "verify_ch17.py": ["film 26676 -> 6426", "6426 pairs for 500 viewers: moves 0, ledger records 500"],
    "verify_ch17_shared.py": ["shown directly: 8", "left open: 24", "pairs of faithful editions ( 496 )", "('direct', 'direct') 28", "after the reveal, pairs that share the reading and do not both warrant the third-bolt claim: 468"],
    "verify_appA.py": ["A premiere matrix count 494 enumerated 494 match", "A after G matrix count 238 enumerated 238 match", "B after G matrix count 96 enumerated 96 match"],
}
failed = 0
for script, needles in EXPECT.items():
    out = subprocess.run([sys.executable, script], capture_output=True, text=True).stdout
    for n in needles:
        if n not in out:
            print("MISSING in", script + ":", n); failed += 1
print("checks failed:", failed, "of", sum(len(v) for v in EXPECT.values()))
sys.exit(1 if failed else 0)
