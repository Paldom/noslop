# Verification contract and release gates

## What a PASS honestly means

`verify_edit.py` proves **surface integrity**: protected content extracted by
deterministic rules survived the edit. It cannot prove meaning was preserved —
real named-entity recognition and semantic equivalence are not achievable
reliably with stdlib-only tooling, and even embedding-based metrics coexist
with flipped negations. Always report results as "surface integrity passed",
never "meaning proven". The negation/modality parity check is a cheap alarm
for the most dangerous drift class (a dropped "not" flips a claim), not a
semantic verifier.

## Why these invariants

The known failure modes of AI-cleanup rewrites, each mapped to a check:

| Failure mode | Check | Severity |
| --- | --- | --- |
| Paraphrased figures ("41%" → "about forty") | numbers, multiset equality both directions | hard |
| Invented figures added during "improvement" | numbers (added side) | hard |
| Softened or truncated quotations | quotes (>=5 words, normalized) | hard |
| Touched code, commands, flags | fenced + inline code, byte-exact | hard |
| Dropped links/sources | urls + markdown link targets | hard |
| Renamed products/APIs mid-prose | identifiers (snake/Camel/SCREAMING, @handles) | hard |
| Dropped/added people or orgs | capitalized-run proxy | warn (crude, no NER) |
| Negation/modality flips | difflib-aligned sentence parity | warn |
| Silent deletion or fluff injection | length band 0.75-1.25 | warn |
| Wholesale rewriting | token edit ratio > 0.30 | warn |
| Edits outside what a linter flagged | localization vs --lint-report < 0.80 | warn |
| Flattening a human's rhythm | sentence-length CV collapse > 25% | warn |

## Over-correction: the numbers that matter

Over-correction — sanding legitimate human prose into a flat "clean" profile —
is the number-one design risk of de-slop tooling. Detector-style signals
already false-flag non-native English writing (7 detectors averaged 61.2%
false positives on human TOEFL essays; Liang et al., *Patterns* 2023,
<https://arxiv.org/abs/2304.02819>), and standard "grammar correction" retains
only ~26% of South Asian English dialect markers versus 92% under
dialect-aware instructions (Bharati et al., C3NLP @ ACL 2026,
<https://aclanthology.org/2026.c3nlp-1.8/>). Deterministic proxies used here:

- **No-op discipline**: run the rewriter over clean human text; verify should
  report edit_ratio ≈ 0. Release-gate suggestion for any rewrite pipeline:
  >= 95% of clean human controls come back with edit_ratio <= 0.02.
- **Edit budget**: token edit ratio above ~0.30 on any single document is
  wholesale rewriting; big edits on text that linted clean are over-correction
  by definition.
- **Rhythm preservation**: an edit that collapses sentence-length variance by
  more than a quarter is flattening voice, not removing slop.
- **Localization**: with a slop-lint JSON report, >= 80% of changed lines
  should sit within one line of a flagged span. Unflagged prose should be
  copied verbatim by a well-behaved rewrite pass.

Treating over-correction as its own measured failure axis (rather than a
footnote to correction success) follows the grammatical-error-correction
literature: CLEME2.0 explicitly decouples hit/wrong/under/over-correction and
shows the split correlates better with human judgment (ACL 2025,
<https://aclanthology.org/2025.acl-long.10/>) — analogous evidence for this
contract's design, not direct validation of this verifier.

## Known limits

- Entity check is a capitalized-run heuristic; expect noise on Title Case
  headings and sentence-initial names. That is why it is warn-level.
- Quotes under 5 words are not tracked (too many false pairs from
  scare-quotes); a rewrite that alters a 3-word quote passes the hard check.
- Tables and YAML frontmatter are treated as prose; heavy table edits inflate
  edit_ratio without meaning harm.
- Two texts can pass every check and still differ in meaning. Surface
  integrity is a floor, not a ceiling — pair with human review for anything
  high-stakes (legal, medical, security claims).
