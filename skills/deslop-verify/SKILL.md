---
name: deslop-verify
description: Verifies a before/after pair of texts with a deterministic script - asserts code, quotes, numbers, links, and identifiers survived an edit; flags negation flips and over-correction. Use when the user asks to verify or compare an edited draft against the original, or whether a rewrite changed facts. Requires both versions. Not for scoring a single text or producing rewrites.
---

# deslop-verify

## Purpose

Deterministically answer "did this edit break anything?" for a text rewrite.
Given the original and the edited version, `verify_edit.py` asserts hard
invariants (fenced/inline code byte-exact, quotations, numbers in both
directions, URLs, link targets, identifiers) and measures over-correction
(token edit ratio, length band, sentence-rhythm collapse, edit localization
against a slop-lint report). It fixes the observed failure of AI-cleanup
passes silently paraphrasing figures, softening quotes, flipping negations,
and sanding human prose flat — failures no prompt-only humanizer pack checks.

## When to use

- "verify / check the edited draft against the original"
- "did the rewrite change any facts, numbers, quotes, code?"
- "was this over-edited?" — any before/after pair, whatever tool or person
  made the edit (deslop, another humanizer, a human editor)
- As the mandatory post-step of a `deslop` rewrite, and in CI over golden
  before/after corpora

## When NOT to use

- No before/after pair exists: scoring a single text → `slop-lint`.
- Producing or fixing a rewrite → `deslop` (this skill never writes prose).
- Generic file diffing, PR review, plagiarism, or build verification.

## Workflow

1. Get both versions on disk (write them to temp files if pasted inline).
2. Run the script:

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/verify_edit.py" original.md edited.md
   python3 "${CLAUDE_SKILL_DIR}/scripts/verify_edit.py" original.md edited.md --json
   ```

   Add `--lint-report lint.json` (output of `slop-lint --json` on the
   original) to compute edit localization — the share of changed lines inside
   flagged spans. Add `--strict` in CI to make warn-level issues fail too.
3. Read the exit code: `0` hard invariants pass, `1` usage/input error,
   `2` a hard invariant failed (or any warn under `--strict`).
4. Report to the user: hard results first (exactly what went missing or was
   added, with values), then warn-level findings (negation/modality flips with
   the sentence pair, edit ratio, rhythm collapse), then the honest framing —
   a pass is **surface integrity, never proof that meaning survived**.
5. On failure, recommend restoring the exact lost content (or reverting to
   the original when edit_ratio is high on text that linted clean) — do not
   silently accept a paraphrase of a figure or quote.
6. Sanity check after any script edit: `--self-test` must print all PASS.

## Output spec

A report with three sections: `hard` (7 invariants, each pass/FAIL with up to
10 missing/added items), `warn` (entities proxy, negation parity, length band,
edit_ratio, rhythm, localization), and `metrics` (edit_ratio, length_ratio,
word counts). JSON mode emits the same as `schema: 1`. Success criteria for a
well-behaved de-slop edit: all hard invariants pass, edit_ratio ≤ 0.30,
length ratio 0.75-1.25, no negation flags, localization ≥ 0.80, and near-zero
edit_ratio when the original was clean human text.

## Gotchas

- **Never claim "meaning preserved".** Deterministic checks prove surface
  integrity only; two texts can pass everything and still differ in meaning.
  Say so in every report (the script prints this note — keep it).
- The entity check is a capitalized-run heuristic, not NER — warn-level by
  design; do not promote it to a hard failure.
- Quotes under 5 words are not tracked; scare-quotes would flood the check.
- Intentional edits can legitimately fail invariants (e.g. the user asked to
  delete a section). Ask whether the loss was intended before declaring the
  edit broken — the tool reports facts, the user owns intent. Exception: when
  the edit came from a `deslop` pass, its fail-closed rule wins — restore the
  content; never rationalize your own pipeline's failure as intent.
- Heavy table/frontmatter edits inflate edit_ratio without meaning harm.
- High edit ratio on prose that scored clean on `slop-lint` is the signature
  of over-correction — the top failure mode of AI-cleanup tools. See
  `references/verification-contract.md` for the release-gate numbers.

## Pointers

- `scripts/verify_edit.py` — the checker (`--help`, `--self-test`).
- `references/verification-contract.md` — what each invariant catches, honest
  limits, and over-correction release gates with evidence.
