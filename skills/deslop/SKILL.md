---
name: deslop
description: Rewrites copy to strip AI-writing tells - negative parallelism (it's not X, it's Y), stacked hedging, inflated significance - preserving meaning and voice through bounded edits on flagged spans, protected quotes/code/numbers and a deterministic post-check. Use to deslop, de-AI, cut hedging, or make a draft read human. Not for scoring only, judging an edit pair, or grammar fixes.
---

# deslop

## Purpose

Strip AI-writing tells (negative parallelism, significance inflation, hedge
stacks, formatting reflexes, era vocabulary, uniform rhythm) from a draft so
it reads human — with the edits *bounded* by deterministic tooling. It fixes
the two observed failures of prompt-only humanizers: silent damage (facts,
quotes, and code drift during "improvement") and over-correction (real
writers, especially non-native ones, get sanded flat; absolute rules like
"zero em dashes" produce a new tell instead of removing one).

## When to use

- "deslop / de-AI this", "strip the AI slop / tells", "this reads
  machine-written — clean it up", "make it read human without changing meaning"
- Cleaning AI-assisted drafts before publishing, with proof nothing broke

## When NOT to use

- Score or report only, no edit wanted → `slop-lint`.
- Checking an edit that already happened → `deslop-verify`.
- Grammar/typo fixing, tone shifts, shortening, translation — different jobs;
  never smuggle them into a de-slop pass.
- "Beat the AI detector" requests: decline the detector-evasion framing;
  offer editorial cleanup instead (this skill improves writing, not evasion).

## Workflow

Sibling scripts (installed together with this skill):
`LINT="${CLAUDE_SKILL_DIR}/../slop-lint/scripts/slop_lint.py"`,
`VERIFY="${CLAUDE_SKILL_DIR}/../deslop-verify/scripts/verify_edit.py"`.
If a sibling is missing (partial install), do **not** edit blind — the no-op
gate, span bounds, and verification all depend on the tools. Say which tool
is missing, deliver playbook-based *suggestions* (a list of flagged spans and
proposed transforms, not an applied rewrite), and point to the full install.

1. **Lint first (no-op gate).** Save the original to a temp file; run
   `python3 "$LINT" original.md --genre <genre> --json > lint.json`.
   If the band is `clean` (score < 25), **return the text untouched** and say
   why — editing clean text is over-correction, not service. If confidence is
   `low` (under 150 words), the score gates don't apply: make bounded
   playbook edits to clearly flagged spans only, note the low confidence, and
   still verify in step 5.
2. **Inventory before editing.** Note: protected spans (quotes, code,
   numbers, URLs, names), the writer's own habits (their dashes/triads are
   their voice), and any consistent dialect/L2 features. Read
   `references/tells-playbook.md` for the per-family transforms and the
   dialect guard — it is the edit contract, not advice.
3. **Bounded edits.** Edit **only** lint-flagged spans plus their sentence;
   copy every unflagged sentence verbatim. Apply the playbook transform for
   each active family; prefer deleting padding over swapping synonyms; never
   invent facts, anecdotes, typos, or slang to "add humanity".
4. **Re-lint the result.** Accept the pass only if the score dropped ≥15
   points or the band is now `clean`. If not, do **one** more constrained
   pass on remaining flagged spans. Two passes maximum — then stop and
   report what remains rather than thrash.
5. **Verify, fail closed.**
   `python3 "$VERIFY" original.md edited.md --lint-report lint.json`.
   On **any non-zero exit**: exit 2 (hard invariant broken) → restore the
   lost content or revert to the original; exit 1 (verify could not run) →
   treat the rewrite as unverified and do not present it as done. Never
   present a rewrite that failed or skipped verification.
6. **Report.** Deliver the edited text plus: before/after scores, families
   fixed, verify result (state it as surface integrity, not proven meaning),
   and anything deliberately left (dialect features, writer habits,
   meaning-bearing hedges, remaining warn-band items).

## Output spec

The edited text, changed as little as possible: all hard invariants pass in
`deslop-verify`, edit ratio ≤ 0.30 (near 0 for clean input), length within
±25%, lint score reduced ≥15 points or banded `clean`, unflagged prose
byte-equal, and a report of before/after scores + verify status. On clean
input: the original text, unchanged, with the no-op explanation.

## Gotchas

- **The dialect/ESL guard is non-negotiable.** Never convert nonstandard,
  regional, or L2 English toward Standard American English; if it could be
  dialect or error, leave it. Evidence and the full rule: the playbook's
  "Dialect and ESL guard" section (26% vs 92% marker retention; 61.2%
  detector false-positive rate on non-native writing).
- **Meaning-bearing hedges are content.** "May cause drowsiness" and "does
  not establish causation" must survive; only stacked hedges are tells.
- **Zero em dashes is itself a tell.** Reduce flagged clusters; never purge.
- **Don't chase score 0.** Below warn is done. Looping to a perfect score
  Goodharts the linter and flattens voice — two passes, then stop.
- **A second deslop of your own output should change < 2%.** If it doesn't,
  the first pass was over-editing; revert and report.
- Drafts produced late in a long chat session tend to carry more tells than
  fresh-session drafts — lint and deslop the final text in a fresh pass
  rather than polishing mid-thread.
- Rewriting wholesale because "everything sounds AI" is refused by design;
  the edit budget exists to protect the writer.

## Pointers

- `references/tells-playbook.md` — per-family transforms, what NOT to flag,
  dialect guard, evidence with primary sources.
- Sibling tools: `slop-lint` (scoring, thresholds provenance) and
  `deslop-verify` (invariants, over-correction gates).
