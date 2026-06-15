# Paperbot Parliament

[The Geometry of Control](https://standardgalactic.github.io/kitbash/paperbot/geometry-of-control.pdf)

* [Graphic Novel](https://standardgalactic.github.io/kitbash/paperbot/geometry-of-control-comic.pdf)

[Paperbot Parliament](https://standardgalactic.github.io/kitbash/paperbot/paperbot-parliament.pdf)

A Unix pipeline implementing a multi-office parliamentary review
of academic text, based on the Distinction Economy framework.

## Directory layout

```
paperbot/
├── parliament.sh          # main engine
├── prompts/               # constitutional office instructions
│   ├── claims.txt         # Stage 1: claim extraction
│   ├── nitpicker.txt      # finds ambiguities and undefined terms
│   ├── skeptic.txt        # finds unsupported claims and objections
│   ├── archivist.txt      # finds precedents and lineage
│   ├── synthesist.txt     # finds patterns and bridges
│   └── auditor.txt        # finds logical gaps and inadmissible jumps
├── source/                # place .txt files here
├── reports/               # per-document parliament records (auto-created)
│   └── <stem>/
│       ├── chunk_aa       # raw chunks
│       ├── chunk_aa.claims
│       ├── chunk_aa_c1.nitpicker
│       ├── chunk_aa_c1.skeptic
│       ├── chunk_aa_c1.archivist
│       ├── chunk_aa_c1.synthesist
│       ├── chunk_aa_c1.auditor
│       └── parliament_report.md   # assembled output
├── archive/
│   ├── accepted/
│   ├── rejected/
│   └── revisions/
├── distinction.ledger     # running X ≠ Y pairs extracted across sessions
└── progress.log
```

## Usage

```bash
# Basic (single pass)
cp your_paper.txt source/
bash parliament.sh

# With revision cycles
PAPERBOT_CYCLES=3 bash parliament.sh

# With a different model
PAPERBOT_MODEL=llama3.1:8b bash parliament.sh

# Smaller chunks (more granular)
PAPERBOT_CHUNK=150 bash parliament.sh
```

## Environment variables

| Variable           | Default         | Description                        |
|--------------------|-----------------|------------------------------------|
| PAPERBOT_MODEL     | granite3.2:8b   | Ollama model to use                |
| PAPERBOT_CHUNK     | 250             | Lines per chunk                    |
| PAPERBOT_CYCLES    | 1               | Revision cycles per chunk          |

## Pipeline per chunk

```
raw chunk
    ↓
Claims Extractor     → chunk.claims
    ↓
Nitpicker            → chunk_c1.nitpicker
Skeptic              → chunk_c1.skeptic
Archivist            → chunk_c1.archivist
Synthesist           → chunk_c1.synthesist
Auditor              → chunk_c1.auditor
    ↓
[Revision Office     → chunk_revision.txt]  (if CYCLES > 1)
    ↓
[repeat offices on revised claims]
    ↓
Distinction Ledger   → distinction.ledger   (X ≠ Y pairs)
    ↓
Parliament Report    → reports/<stem>/parliament_report.md
```

## Version roadmap

- v1 (this): sequential offices, flat file outputs, distinction ledger
- v2: voting (Nitpicker FAIL / Skeptic FAIL / Auditor PASS → NEEDS REVISION)
- v3: archive memory (new papers checked against prior accepted claims)
- v4: daemon mode (claim_queue/, office_queue/ directories, inotifywait loop)
- v5: Lyapunov convergence monitor (dV/dt ≤ 0 check across cycles)
