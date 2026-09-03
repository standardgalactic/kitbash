# Logic Books — Completion Plan and Proof Spines

Status as of this document: **both books complete**, zero `[TODO]` markers, zero LaTeX compile errors, every experiment/countermodel visually verified against the rendered PDF. This file is the durable map of what's in each book — chapter by chapter, theorem by theorem, with each proof's *spine* (its essential shape, not the full listing) — so the content is navigable without re-reading ~80KB of `.tex` source.

Neither book's Lean content has been checked against a real toolchain — everything here is LaTeX-verified (renders correctly, no missing glyphs, no corrupted brackets) but not Lean-compiler-verified. Treat proof spines as "should typecheck," not "confirmed typechecks."

---

## Book I — *Proof and Countermodel: An Introduction to Logic with Lean*

39 pages, 6 chapters, self-contained (assumes nothing beyond itself).

### Ch.1 — Propositions and Connectives
Method-defining chapter: introduces the Prop/Bool distinction and the experiment/countermodel pairing everything else follows.

| Name | Spine | Point |
|---|---|---|
| `or_intro_left` | `Or.inl hp` | ∨-introduction is definitional |
| *(countermodel)* | `by decide` over `Bool` | converse of ∨-intro fails |
| `demorgan_or` | `Iff.intro` of two `Or.inl`/`Or.inr`-composed functions | ¬(p∨q) ↔ ¬p∧¬q, both directions constructive |
| `demorgan_and_one_way` | `h.elim (fun hnp => hnp hpq.1) (fun hnq => hnq hpq.2)` | ¬p∨¬q → ¬(p∧q); converse deferred to Ch.3 |
| `and_distrib_or` | nested `Iff.intro` / `.elim` | p∧(q∨r) ↔ (p∧q)∨(p∧r) |
| *(countermodel)* | `by decide` | p∧(q∨r) does **not** force p∧q **and** p∧r separately |
| `sFromTable`/`sFromDNF` | `by decide` equality of two `Bool` functions | canonical sum-of-products = truth table |
| `circuitA`/`circuitB` | `by decide` | two differently-shaped circuits, same function |

### Ch.2 — Natural Deduction as Tactics
Reads `intro`/`constructor`/`apply`/`exact`/`cases` as the introduction/elimination rules directly.

| Name | Spine | Point |
|---|---|---|
| `and_intro_tactic` | `constructor` → two `exact` goals | ∧-intro as tactic |
| `chain` | `apply hqr; apply hpq; exact hp` | →-elim (modus ponens) read backwards from goal |
| `or_idem` | `cases h with | inl hp => exact hp | inr hp => exact hp` | ∨-elim, both branches converge |

### Ch.3 — Classical and Constructive Logic
| Name | Spine | Point |
|---|---|---|
| `dn_intro` | `fun hnp => hnp hp` | p→¬¬p, fully constructive |
| `dn_elim` | `Classical.byContradiction h` | ¬¬p→p, needs the axiom by name |
| `dn_elim_from_em` | `cases Classical.em p with | inl hp => exact hp | inr hnp => exact absurd hnp h` | second derivation, reusing Ch.2's `cases` |

*(Editorial note: the original stub put `dn_elim` in a `countermodel` box — a category error, since ¬¬p→p is true. Converted to `experiment`.)*

### Ch.4 — Quantifiers
| Name | Spine | Point |
|---|---|---|
| *(bound-var experiment)* | `Iff.rfl` | ∀x,Px ↔ ∀y,Py are the *same term* |
| `Pex` | `by decide` on `Fin 2` | free substitution is **not** costless, unlike bound renaming |
| `ex_all_to_all_ex` | `obtain ⟨x, hx ⟩ := h; intro y; exact ⟨x, hx y ⟩` | ∃∀ ⟹ ∀∃ |
| *(countermodel)* | `by decide` on `Fin 2` | converse quantifier order fails |
| **§4.3 Euler Diagrams** (TikZ, not Lean) | — | valid/invalid syllogism, Converse Error & Inverse Error `fallacy` boxes, "No" argument, BFO/OBO sidebar |
| `zeus_syllogism` | `intro hz; exact minor (major zeus hz)` | valid syllogism formalized |
| `no_p_are_q` | `intro ha; exact (major a ha) minor` | universal-negative ("No P are Q") argument |

### Ch.5 — Relations and Orders
| Name | Spine | Point |
|---|---|---|
| `SameParity` | 3× `by decide` on `Fin 4` | genuine equivalence relation (refl+symm+trans all proven) |
| `Close` | 3× `by decide` on `Fin 3` | reflexive+symmetric, **not** transitive |
| `History`/`Extends`/`extends_refl`/`extends_trans` | `fun x hx => hx` / `fun x hx => h23 (h12 hx)` | Extends is a preorder |
| *(antisymmetry discussion, prose only)* | — | true for bare `History`, deliberately not claimed — survives future enrichment |
| `Constrain`/`constrain_subset` | `fun x hx => hx.1` | the exercise's own missing definition — added here (gap found in original scaffold) |
| `countdown` | structural recursion on `Nat` | well-founded recursion, concrete instance |

### Ch.6 — Elementary Set Theory as Applied Logic
Closing chapter; explicitly hands off to Book II.

| Name | Spine | Point |
|---|---|---|
| *(subset experiment)* | `intro x hx; simp [Set.mem_setOf_eq] at hx ⊢; omega` | `Set α = α → Prop`; subset proof is `intro`/`exact` |
| *(De Morgan for sets)* | `ext x; simp [...]; exact Iff.intro (...)` | literally the same proof shape as Ch.1's `demorgan_or`, one membership-unfold away |
| `russellSet` | **deliberately does not typecheck** | `s ∉ s` needs `alpha = Set alpha` — paradox blocked structurally, before any truth value |

---

## Book II — *Inference Under Constraint: Logic Experiments in Lean*

33 pages, 4 chapters. Successor volume — assumes Book I's method, not its content.

### Ch.1 — Three-Valued and Paraconsistent Logic
| Name | Spine | Point |
|---|---|---|
| `K3`, `K3.knot`, `K3.kor` | Kleene truth tables | gap value |
| `excluded_middle_fails` | `⟨K3.unknown, by decide ⟩` | p∨¬p fails at a gap |
| `LP`, `LP.lnot`, `LP.lor`, `LP.designated` | min/max under `f < b < t` | **scoped down** from the original "extend K3 to 4-valued FDE" plan — a full bilattice was too easy to get subtly wrong blind; LP built instead as its own correct 3-valued type |
| `lp_excluded_middle` | `by decide` | glut value **restores** excluded middle (opposite of the gap case) |
| `LP.land` + countermodel | `by decide` ×2 | p∧¬p designated at `b`, but `f` undesignated — explosion fails |
| *(closing paragraph)* | prose | explicit link to the Priest–Flyxion program |

### Ch.2 — Modal Logic
| Name | Spine | Point |
|---|---|---|
| `World`, `accessible`, `val`, `diamondP`, `boxP` | `List.any`/`List.all` over `worlds` | 3-world Kripke frame; uses inductive-constructor pattern matching deliberately, **not** `Fin 3` literals (avoids a pattern-matching risk that bit other parts of this project) |
| 4× `example ... := by decide` | — | □/◇ at `w0` (informative) vs `w2` (dead-end, □ vacuous) |
| `State`/`valid`/`consequence_requires_record` | `h.1 (h.2.1 (h.2.2 hc))` | record→admit→commit→consequential forward chain |
| `recordedOnly`/`record_does_not_imply_admit` | explicit countermodel state | none of the converses hold |
| **§2.3 correspondence theory** (prose) | — | T/4/B ↔ reflexive/transitive/symmetric |
| `committed_reaches_recorded` | `fun hc => h.1 (h.2.1 hc)` | **same composition shape** as `extends_trans`, shown side by side |

### Ch.3 — Admissibility as a Logic
The book's thesis chapter.

| Name | Spine | Point |
|---|---|---|
| `History`/`Extends`/`extends_refl`/`extends_trans`/`witnessed_facts_persist` | (same as Book I Ch.5) | preorder, restated as the base for what follows |
| `Constrain`/`constrain_subset` | `fun x hx => hx.1` | narrowing, restated |
| `Admissible` | `f ∈ Constrain h.witnessed C` | consequence relation, defined *from* what's already built |
| `admissible_of_witnessed_and_permitted` | `And.intro hw hc` | reflexivity/assumption rule |
| `admissible_persists_under_extension` | `And.intro (hext ha.1) ha.2` | persistence under history growth |
| `sampleHistory`/`openConstraint`/`stricterConstraint` + 2 examples | `And.intro rfl trivial` / `intro h; exact h.2.2 rfl` | **non-monotonicity in the constraint** — the specific fact that makes this a distinct logic, not classical logic in new notation |

### Ch.4 — Metatheory
Deliberately the most conservative chapter — see "Scope calls," below.

| Name | Spine | Point |
|---|---|---|
| `knot_involutive`, `kor_comm` | `by decide` | encoding matches Kleene's own semantics ("soundness" reframed, since there's no separate calculus in this book) |
| *(unknown-doesn't-block example)* | `by decide` | classical intuition about gaps is wrong; only the logic's own semantics settles it |
| `kor_idempotent` | `by decide` | K3 validity is decidable — finite search, same principle as `Bool` throughout Book I |
| `Formula`, `encode`, `decode`, `encode_decode` | structural recursion + `induction n` | Gödel-numbering, **deliberately minimal** (atom/neg only, no Cantor pairing) — a total bijection, honestly described as such |
| `isWellFormed`/`isWellFormed_always` | `fun _ => rfl` | deliberately trivial — stated as such, not dressed up |
| *(closing discussion, prose)* | — | what a real soundness/completeness result for `Admissible` would require; explicitly left as future work, not attempted |

---

## Cross-book connections (the load-bearing parallels)

These are the specific places where a proof term in one book is deliberately built to have the *same shape* as a proof term elsewhere, not just an analogy asserted in prose:

- Book I `demorgan_or` (Ch.1) ↔ Book I `Set` De Morgan (Ch.6) — literally the same term, one membership-unfold apart
- Book I `extends_trans` (Ch.5) ↔ Book II `committed_reaches_recorded` (Ch.2) — both `fun x hx => h23 (h12 hx)`-shaped composition
- Book II `extends_trans`/`Extends`/`Constrain` (Ch.3) — restated verbatim from Book I Ch.5, then built on rather than re-derived
- Book II Ch.1's `LP.designated` ↔ Book II Ch.3's `Admissible` — named explicitly in Ch.1's closing paragraph as "the simplest possible instance" of the same constraint idea

## Scope calls made along the way (things deliberately *not* built)

Worth keeping visible rather than letting them look like oversights:

1. **Full 4-valued FDE/Belnap-Dunn bilattice** (Book II Ch.1) — real bilattice connectives are easy to get subtly *mathematically* wrong with no compiler to catch it (unlike a Lean syntax slip, a wrong truth table wouldn't error, it'd just be incorrect logic in a book about logic). Scoped down to LP as its own correct 3-valued type instead.
2. **Cantor-pairing Gödel numbering** (Book II Ch.4) — scoped down to a minimal atom/neg-only language with a genuinely total encoding, explicit about why `isWellFormed` is trivial as a result.
3. **Soundness/completeness for `Admissible`** (Book II Ch.4, closing section) — named as what a second book's worth of work would need to establish; not attempted.
4. **`rank_le`/`rank_ge` and the Euclidean lifting theorem** — not these books; noted here only because it's the same *kind* of scope call made in the parallel `ciupa-lean` project.

## Known engineering hazards (if extending either book further)

Found and fixed during writing — worth knowing before adding more Lean listings:

- **`listings` + `tcolorbox`'s `breakable` skin can corrupt code that splits across a page boundary.** Fixed by removing `breakable` from the three code-bearing box types (`experiment`/`countermodel`/`fallacy`); kept on prose-only `sidebar`/`historicalnote`.
- **Any identifier or symbol immediately touching `⟨`/`⟩`/`(` with no space gets transposed** (`decide⟩` → `⟩decide`, `(φ` → `φ(`). Confirmed via direct render, not just theory. Fix: always leave a space before closing brackets in Lean listings; avoid Greek-letter identifiers if a bracket sits next to one — use ASCII instead.
- **`\texttt{}` in ordinary prose uses the default Latin Modern Mono font, which lacks ∈/⊆/∉ (though not →/¬/·).** Fix: use math mode (`$\in$` etc.) for logic symbols in prose; reserve `\texttt{}` for actual code identifiers.
- **`Fin n` literal pattern matching (`| 0, 1 => ...`) is a version-dependent risk.** Book II Ch.2's Kripke frame uses an inductive type with named constructors instead, deliberately, to sidestep it.
- Both books' `main.tex` are otherwise self-contained and don't share a preamble file — any fix made in one should be manually ported to the other (this has already been done once, for the `breakable` fix).
