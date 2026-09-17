# The Shape of Search: Claim Ledger

Classes: **S** source result (reported by a cited study) · **F** formal consequence (follows from definitions; proposition or derivation) · **I** interpretation (a reading beyond what the source reports) · **P** new proposal (definition or construction introduced here).

## 1–2. Endpoint fallacy; Search is not enumeration

| Claim | Class | Basis |
|---|---|---|
| Observed trajectory ≠ underlying dynamics | P | Organizing thesis |
| E₁ = E₂ ⇏ K₁ = K₂; E(x) = E(y) ⇏ Γ(x) ≅ Γ(y) | F | Kernel is not determined by the objective |
| Energy geometry (scalar field) ≠ continuation geometry (relation) | P | Framing distinction |

## 3–4. Minimum as relation; probability as material property

| Claim | Class | Basis |
|---|---|---|
| Glauber update, flip rate from ~0.5 toward 0 over 1,000 iterations | S | Li et al. main text, Fig. 4 |
| ε-continuation set; practical minimum at (T, ε) | P | Definition |
| x_t ⇏ Γ_t(x_t) without specification of K_t | F | Γ is a function of the kernel |
| Pulse widths 0.5/0.65/0.8 ns → ~2/55/95% switching; sigmoid fit | S | Li et al. Fig. 2 |
| W_v = δH/(αT) + W₀ | S | Li et al. eq. 4 |
| Problem, schedule, and matter meet in one scalar | I | Reading of eq. 4 |
| FPGA computes δH; junction performs the Bernoulli trial; 45 ns end-to-end | S | Li et al. methods, Table 1 |
| 16-bit LFSR parity; 8- and 4-bit worse | S | Li et al. Ext. Data Fig. 3 |
| Coarser probability resolution means coarser search geometry | I | Marked as a natural reading |
| >95% success with a fifth of devices peaking at 60% (FPGA emulation) | S | Li et al. methods |

## 5–7. Constraint as geometry; occupied invalidity; competing valuations

| Claim | Class | Basis |
|---|---|---|
| H_c1–H_c4 formulas; order variables enforce acyclicity by transitive ordering | S | Li et al. Supp. Note 4 (preprint version) |
| Order variables enlarge X to make admissibility writable | I | Reading of the encoding |
| Possible ⊇ reachable ⊇ admissibly reachable | P | Builds on Arranged Conditions (sets) and Clipboard (graded Adm) |
| Invalid outcomes dominate early; >95% optimal beyond 10⁴ iterations | S | Li et al. Fig. 4f |
| Re-parenting a vertex forces an invalid intermediate under single flips | F | Argument about the encoding, not a reported result |
| Per-coefficient sensitivity profile (λ₁…λ₄) | S | Li et al. Ext. Data Fig. 2 |
| Raising one penalty cannot expel an admissible ground state | F | Proposition 2; hypotheses checked for all four terms |
| Increased invalidity under high λ₃ is dynamical | F | Conditional on baseline ground state being optimal (stated) |
| New basins separated by barriers (mechanism) | I | Marked as interpretation |
| Authors' relative-importance explanation of λ₃; exploration account of λ₁ | S | Li et al. Supp. Note 5 |
| Low-λ₄ suboptimality is a relocated ground state | I | Marked as inference |
| Scored admissible set ≠ intersection of encoded constraints | I | Inferred from outcome classes |
| Raising vs. lowering penalties is asymmetric | F | Prop. 2 and its failure for lowering |
| (H, T) ∼ (cH + d, cT); landscape height unobservable to the search | F | Glauber rule depends only on δH/T; authors' remark (S) |
| Search manufactures adjacency | P | Thesis statement |

## 8–10. Adverse transitions; annealing; controlled admissible divergence

| Claim | Class | Basis |
|---|---|---|
| Error of state ≠ transition ≠ process | P | Distinction |
| Uphill continuation sets nest as T falls; downhill sets grow | F | Proposition 1 |
| Late updates pushed toward pulse-window edges | F | From eq. 4; share of updates affected not reported (stated) |
| Novelty band θ_min < Adm < θ_max | S | Everything Is a Clipboard §19.12 |
| Non-collapse enforced by recoverability R_h(x, A) ≥ η, not per transition | P | Refinement motivated by the Ising case |
| Inadmissible ≠ irrecoverable | P | Distinction |

## 11. The task enters the quantity (TVA)

| Claim | Class | Basis |
|---|---|---|
| C modes 49 / 58 Hz; difference −9.5 Hz; 95.7% and 78.8% in ROPE | S | Biermeier & Scharlau results |
| 8 Hz / 6 Hz measurement error | S | Biermeier & Scharlau, via main text (S1–S2 not read) |
| 12 of 30 within ROPE; two clusters | S | Biermeier & Scharlau post-hoc analysis |
| Four routes (spatial sampling, criterion, motivation, flexibility) | S | Biermeier & Scharlau discussion |
| Capacity as field c(s); Ĉ_τ = F_τ[c restricted to S_τ] | P | Formalization of the spatial-sampling route |
| One-parameter model as drain for task variance | I | Generalization of the authors' flexibility point |
| TOJ indifferent to speedup vs. slowdown | S | Tünnermann et al. 2015, footnote 1 |
| Cued −9 ms, uncued +16 ms; PE ~25 ms (TVA) vs. ~60 ms (TOJ) | S | Tünnermann et al. 2015, Exp. 1–2 |
| Evidence-threshold account of the dissociation | S | Authors' proposed model, marked as such |
| C conserved under cueing (~58 vs. 60 Hz) | S | Tünnermann et al. 2015 |
| Invariance is relative to a transformation family 𝒯 | P | Framing; the cueing vs. task contrast is S |
| Three possibilities, including an inadequate decomposition | P | Analysis |
| Equivalence as a relation at tolerance δ | P | Parallel to ε |

## 12–13. Shared destination; uncertainty has shape (LLM dialogue)

| Claim | Class | Basis |
|---|---|---|
| Design: 6 models, 12 topics, 5 rounds, 150,000 observations per model | S | Brockers et al.; peer review file |
| Probe not retained in context; M commutes with K | S / I | Protocol (S); commutation phrasing (I) |
| Attractor ≠ prior; correlations 0.62–0.96 except Grok | S | Supp. Figs. 13–14; peer review file |
| Four-pull drift model | S | Brockers et al. eq. 1–5 |
| Topic bias is a modeled contribution, not an observed force | I | Following the referee exchange (S) |
| Fixed agreement target resolved collinearity | S | Peer review file |
| Trajectory ≠ decomposition ≠ identifiable decomposition | P | Distinction supported by the review history |
| Topic bias has greatest individual LOO explanatory power, all six models | S | Supp. Fig. 2 |
| Anchoring sign not interpreted | S | Authors' restraint, adopted |
| Parameter recovery; 32–77% of explainable variance | S | Supp. Fig. 3; peer review file |
| Linear pulls reduce to a centroid; endpoint identifies at most the centroid | F | Proposition 3 |
| Negation, fixed targets, and asymmetric application break the degeneracy | F / S | Prop. 3 remark (F); authors' rebuttal (S) |
| Co-motion ≠ coupling; inherited geometry | P / I | Distinction (P); reading of the study (I) |
| Fine-tuning moves the attractor | S | Brockers et al. Fig. 7; authors' interventional reading |
| Initialization failures as a gap between representable and occupiable | I | Reading of Fig. 3 dotted regions |
| Entropy bounds (two-point minimum, Gibbs maximum) | S | Supp. theoretical bounds |
| Entropy–variance r = 0.38–0.95; significant for 4 of 6 | S | Supp. Table 3 |
| Mean and entropy jointly insufficient | F | Proposition 4 example |
| Entropy link shows dynamic incompleteness, not non-lumpability | I | Explicitly bounded |
| Scope limited to LLM-to-LLM dialogue | S | Authors' stated contribution |

## 14. Equivalence has grades

| Claim | Class | Basis |
|---|---|---|
| ∼_b ⇒ ∼_π; ∼_π ⇏ ∼_b; ∼_Γ ⇏ ∼_K | F | Definitions |
| Q-preservation as factoring through π; lumpability as a special case | F | Proposition 5 (Kemeny–Snell) |
| Compression admissible only relative to future distinctions | P | Principle |
| Shared label ⇏ shared continuation; a fibre is not a faction; bundles legitimate only for claims whose property factors through the label | P | Application to taxonomies; applying it to any named bundle would be I and require evidence |
| Continuation structure 𝒞(x) with Rev_x = R_h(·, {x}) | P | Definition |
| Finite-horizon continuation sets | P | Definition |
| Persistence as class preservation, not fixed point | P | Proposed correction to Clipboard §8.4 |
| Continuation-preserving compression | P | Definition bridging to Clipboard |

## 15–17. Synthesis; neighboring frameworks; conclusion

| Claim | Class | Basis |
|---|---|---|
| y_t = M(K^t(x_0)); history diagram | P | Synthesis |
| Three observational regimes map onto the three studies | I | Reading of their designs |
| Arranged conditions O = f(x, Θ) | P | After Arranged Conditions |
| Some resolutions belong to the system, others are declared | P | Corrected in this pass |
| Positioning against landscapes, bisimulation, invariance, opinion dynamics, affordances | I | Literature placement |
| State descriptions are lossy quotients; different quotients preserve different claims | P | Central novelty claim |
| Existence ≠ reachability | P | Supported by Unchosen Adjacency and the penalty analysis |

## Changes made in this pass

- Added a claim-status paragraph to Section 1.
- Marked as interpretation or inference: the probability-resolution reading, the barrier mechanism under high λ₃, the fine-tuning result (now attributed to the authors' reading), and the "plausibly in part" causal claim in the divergence section.
- Replaced an unqualified claim about valid-only paths with an argument limited to re-parenting in this encoding.
- Bounded the pulse-window claim to what follows from eq. 4, noting the share of affected updates is not reported.
- Attributed the clipboard novelty weakness to the monograph's own objections section.
- Softened "does not change" to "did not change detectably" for TVA-based prior entry across cue intervals.
- Removed "quality of the endpoint" for the dialogue case, where no quality measure exists.
- Corrected the synthesis: the TVA work shows invariance still outstanding rather than demonstrated; the six distinctions are "supported by," not "established by," the cases.
- Fixed an internal contradiction: probability resolution belongs to the system, while ε and δ are declared by the describer.

## Verb audit (second pass)

- "Often unavailable" replaced with "some elementary changes between valid trees necessarily pass through invalid intermediates," matching the ledger entry.
- "The next section shows that the search needs them" became "argues that the search makes use of them and, for some changes, cannot avoid them."
- "Therefore" in the scored-admissible-set inference became "If so," keeping it conditional on the marked inference.
- "The TVA comparison shows ... has a different reading" became "can have a different reading," with the latent question left open.
- The Proposition 2 remark now restates its hypothesis (admissible ground state before the change) before drawing its conclusion.
- Remaining uses of "shows," "therefore," and "hence" were checked and attach to source results, formal steps, or explicitly attributed readings.

## Figures

All five figures are schematic (class P): they depict definitions and formal relations, not data from the cited studies, and each caption says so.

| Figure | Depicts | Class |
|---|---|---|
| 1. Same height, different continuation geometry | E(x) = E(y) ⇏ Γ^ε(x) ≅ Γ^ε(y) | F, drawn schematically |
| 2. Possible, reachable, admissibly reachable | X ⊇ Γ^ε(x) ⊇ Γ^{ε,θ}(x), admissible set disconnected | P |
| 3. Annealing as scheduled loss of alternatives | Nesting of uphill continuation sets (Proposition 1) | F, drawn schematically |
| 4. Quotient geometry | π(x₁) = π(x₂) with Q(𝒞(x₁)) ≠ Q(𝒞(x₂)) | P |
| 5. The composition y_t = M(K^t(x₀)) | History, kernel fan, attractor region, collapse onto observation axis | P |
