#!/usr/bin/env python3
"""Merges the chapter and appendix files into hypernormal-cinema.tex. Run from this folder."""
import glob, re
files = sorted(glob.glob('ch*.tex')) + ['appA-counting-and-matching.tex', 'appB-verification-scripts.tex',
                                         'appC-notation-and-relation-to-the-earlier-volume.tex']
parts = {"The Space of Possible Films": "Foundations of Variation", "Slots, Takes, and the Graph of Editions": "The Structure of an Edition",
         "Reports and Adjudication": "Correction", "Locales and the Worldwide Premiere": "Release and Repertoire",
         "Exclusion and Reference Corpora": "Boundaries and Cases"}
extra_bib = r'''\bibitem{yurchak2006}
Alexei Yurchak.
\newblock \emph{Everything Was Forever, Until It Was No More: The Last Soviet Generation}.
\newblock Princeton University Press, 2006.

\bibitem{curtis2016}
Adam Curtis.
\newblock \emph{HyperNormalisation}.
\newblock Documentary film, BBC, 2016.'''
url = "https://standardgalactic.github.io/kitbash/generative-film/generative-film.pdf"
pre_lines = []; seen = set(); bib = {}; bodies = []
for f in files:
    s = open(f).read(); pre, rest = s.split('\\begin{document}')
    pre = pre.split('\\title')[0]
    for l in pre.split('\n'):
        if l.startswith('\\documentclass') and pre_lines: continue
        if l.strip() == '' or l in seen: continue
        seen.add(l); pre_lines.append(l)
    body = rest.split('\\end{document}')[0]
    for m in re.finditer(r'\\bibitem\{([^}]*)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})', body, re.S):
        bib.setdefault(m.group(1), m.group(0).strip())
    body = re.sub(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}', '', body, flags=re.S)
    body = body[body.index('\\chapter{'):]
    if f.startswith('ch09'): body = body.replace('def:robust', 'def:robust-ch9')
    if f.startswith('ch07'): body = body.replace('sec:ledger', 'sec:ledger-ch7')
    bodies.append((f, body.strip()))
out = '\n'.join(pre_lines).replace('\\textsc{A Cinema of Individual Editions}', '\\textsc{Hypernormal Cinema}') + r'''

\title{\Huge\bfseries Hypernormal Cinema\\[1.2ex]
\large Individual Editions and the Limits of Correction}
\author{Flyxion\\[0.3ex]\small Independent Researcher}
\date{November 2026}

\setcounter{tocdepth}{1}
\begin{document}
\frontmatter
\maketitle
\tableofcontents
\mainmatter

''' + open('note-title.tex').read() + '\n'
for f, b in bodies:
    if f.startswith('appA'): out += '\\appendix\n\n'
    m = re.match(r'\\chapter\{([^}]*)\}', b)
    if m and m.group(1) in parts: b = '\\part{%s}\n\n' % parts[m.group(1)] + b
    out += b + '\n\n'
gf = bib['flyxion2026gf'].replace('\\newblock Unpublished monograph, October 2026.', '\\newblock Monograph, October 2026.\n\\newblock \\url{%s}' % url)
bib['flyxion2026gf'] = gf
out += '\\clearpage\n\\addcontentsline{toc}{chapter}{Bibliography}\n\\begin{thebibliography}{99}\n\n' + '\n\n'.join(bib.values()) + '\n\n' + extra_bib + '\n\n\\end{thebibliography}\n\n\\end{document}\n'
open('hypernormal-cinema.tex', 'w').write(out)
