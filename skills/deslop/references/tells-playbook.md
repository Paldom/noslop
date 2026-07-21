# AI-tell rewrite playbook

**Contents:** [Doctrine](#doctrine) · [Per-pattern transforms](#per-pattern-transforms) ·
[What NOT to flag](#what-not-to-flag) · [Dialect and ESL guard](#dialect-and-esl-guard) ·
[Evidence](#evidence)

## Doctrine

1. **Clusters, never lone marks.** Every sign is a heuristic; a single em dash
   or "delve" means nothing (WP:AISIGNS framing). Edit only what `slop-lint`
   flagged, plus the flagged span's own sentence.
2. **Deletion beats substitution.** Most slop is padding; remove it. Swapping
   "delve" for "explore" produces different slop, not human prose — scrubbing
   vocabulary alone moves AI-text classifiers by only ~1.6 percentage points.
3. **Unflagged prose is copied verbatim.** This is the fairness mechanism:
   what the linter didn't flag, the rewrite cannot touch.
4. **Never fake humanity.** No injected typos, forced contractions, planted
   slang, or manufactured anecdotes. "Clean but empty is a failure"; fake
   texture is worse — it is a new kind of slop and reads as deception.
5. **The critic is the linter, not taste.** Accept an edit pass only if the
   re-lint score drops and `deslop-verify` passes. Never loop to a perfect
   score: two passes maximum, then stop and report.

## Per-pattern transforms

| Lint family | Transform |
| --- | --- |
| neg_parallel ("it's not X, it's Y") | State the positive claim once, drop the negated half: "It's not just a tool, it's a platform" → "It's a platform" (or name the concrete capability). If the contrast carries real information, keep it but break the template. |
| significance ("stands as a testament", "underscores the importance") | Delete the significance assertion; let the fact speak. "The launch marks a significant milestone, underscoring our commitment" → "We launched." Add the concrete detail the phrase was hiding, if the source material has one. Recap scaffolds ("In conclusion,", "In summary,", "In this article we'll...") are deletions too — after editing, the first sentence should do real work (not announce the text) and the last should not restate what was just said. |
| -ing pivots (", highlighting...", ", ensuring...") | Cut the trailing clause or promote it to its own sentence with a real subject and a falsifiable claim. |
| tricolon / rule of three | Keep the strongest one or two items; vary list lengths. If every list has exactly three items, merge or split at least one. |
| era_vocab clusters | Replace with the plain word the sentence needs ("leverage" → "use", "delve into" → "look at") or delete the sentence if it says nothing. Only touch words the linter flagged as co-occurring. |
| burstiness (uniform rhythm) | Merge two short flagged sentences or split a long one so lengths vary; front-load one point. Do not randomize rhythm mechanically — vary it where emphasis genuinely differs. |
| formatting reflexes | Convert decorative bullets back to prose; drop bold from mid-sentence keywords; remove headings that section a text shorter than ~300 words. Keep genuinely enumerable content as lists. |
| hedge stacks ("may potentially") | Keep exactly one hedge that reflects real uncertainty; delete the stack. Never delete a lone hedge — see What NOT to flag. |
| artifacts ("As an AI", `oaicite`, leaked markup) | Delete the artifact, then re-read the sentence and repair any leftover syntax. **Exception — artifacts inside URLs** (`utm_source=chatgpt` query params): leave the URL byte-intact and report it — `deslop-verify` protects URLs as a hard invariant, so editing them fails verification; the user decides link edits. |
| em dash overuse | Only when flagged as part of a cluster: convert some to commas, periods, or parentheses — never all of them. Zero em dashes is itself a tell of machine editing. |

## What NOT to flag

Never treat these as slop; edits here are over-correction:

- **Lone hedges and calibrated uncertainty.** "May", "suggests", "we believe"
  are content in legal, medical, security, and scientific prose — removing
  them changes the claim. Only stacked hedges are tells.
- **Legitimate em dashes.** Human baseline is ~3.23 per 1k words with a range
  up to 17; essayists and fiction writers earn their dashes.
- **Formal register, perfect grammar, technical vocabulary.** Formality is
  not slop; many professionals and non-native speakers write formally by
  training. (Detectors false-flag exactly this: 61.2% average false-positive
  rate on human non-native TOEFL essays.)
- **Necessary lists in docs.** A README's install steps belong in bullets.
- **Repetition with rhetorical purpose**, quotes, code, numbers, names —
  protected outright (verify enforces this).
- **A writer's own habits.** If the user's other writing shows the pattern
  (they genuinely use dashes or triads), leave their signature alone and say
  so rather than "fixing" them.

## Dialect and ESL guard

Non-negotiable, and the reason edits are span-bounded:

- Do not convert nonstandard, regional, or L2 English into Standard American
  English. Grammar, article use, prepositions, aspect/tense preference,
  idiom, code-switching, honorifics, and spelling variety are **voice, not
  slop** — never edit them unless the user explicitly asked for copyediting.
- If a construction could be dialect or error, leave it.
- If consistent dialect/L2 features are present, note the variety in your
  report and treat marker retention as a success criterion.

Why this is a hard rule, not a preference: standard "grammar correction"
retained only 26.0% of South Asian English dialect markers (14.0% under
formalization), while dialect-aware instructions retained 92.0% — measured on
Llama 3.3 70B over a 500-sentence benchmark (Bharati et al., "The American
Palimpsest", C3NLP @ ACL 2026, <https://aclanthology.org/2026.c3nlp-1.8/>;
figures verified against the anthology page). AI-text
detectors flag non-native writing at ~61% false-positive rates (Liang et al.,
*Patterns* 2023, <https://arxiv.org/abs/2304.02819>). An unbounded "make it
sound human" pass sands real writers down to the same flat profile it claims
to fix — the span-bounded edit rule makes that mechanically impossible.

## Evidence

- WP:AISIGNS — canonical, community-maintained tell inventory; signs are
  heuristics, era-banded, decaying:
  <https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>
- Vocabulary spikes are real but era-bound: Kobak et al., *Science Advances*
  11(27) 2025 (doi 10.1126/sciadv.adt3813) — "delves" 28x in 2024 biomedical
  abstracts; decayed since. Liang et al., ICML 2024
  (<https://arxiv.org/abs/2403.07183>) — "meticulous" 34.7x in peer reviews.
- Structure outlasts vocabulary: negative parallelism appeared in ~6% of
  328,744 analyzed ChatGPT messages (Washington Post, Nov 2025) and survives
  vendor patching; em dashes were vendor-suppressed from GPT-5.1 (Nov 2025).
- The "explain-own-significance" habit separates AI (~77%) from human (~52%)
  text (attributed to a UMD / Google DeepMind study, mid-2026 — secondary
  sourcing only, no primary citation located; treat as directional) — hence
  the significance family gets deletion, not paraphrase.
