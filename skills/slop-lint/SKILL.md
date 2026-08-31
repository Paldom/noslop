---
name: slop-lint
description: Scores copy 0-100 for AI-writing tells with a deterministic script - measures em dash rate, hedge-stack density and other cluster rates against genre-aware thresholds, with span-anchored findings and CI gating via exit codes. Use to scan, score, lint, measure or gate text for AI-sounding patterns. Detect-only - not for rewriting, verifying an edit, or code linting.
---

# slop-lint

## Purpose

Deterministically measure how much a piece of prose relies on AI-writing tells
— negative parallelism, significance inflation, uniform rhythm, formatting
reflexes, era-tagged vocabulary, leaked chatbot artifacts — and report
span-anchored findings plus a 0-100 cluster score. The script is pure Python
stdlib: no network, no LLM, same input → same output. It fixes the observed
failure of prompt-only "humanizer" packs: judgments by feel, no numbers, no CI
gate, and single-tell overreactions (an em dash is not a verdict).

## When to use

- "score / scan / lint / check this text for AI tells or slop"
- "how AI-sounding is this?" — anything wanting a number or a report
- Gating docs or marketing copy in CI before publishing
- Producing the findings a rewrite pass will edit against

## When NOT to use

- Rewriting or de-slopping text → use `deslop` (it runs this lint first).
- Checking whether an edit changed facts/quotes/meaning → use `deslop-verify`.
- Judging whether a specific person or student used AI — this is a style lint,
  never an authorship detector; refuse accusation framings.
- Linting code, grammar, or spelling.

## Workflow

1. Pick the genre profile: `general` (default), `academic`, `technical`
   (docs/READMEs), or `casual`. When unsure, say which you chose and why.
2. Run the script (span-anchored findings + score):

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/slop_lint.py" FILE... --genre technical
   python3 "${CLAUDE_SKILL_DIR}/scripts/slop_lint.py" --json < draft.md   # machine-readable
   ```

3. Report to the user: the score and band, which families are active, and the
   top flagged lines (the report includes line numbers). Always state that the
   score reflects a **cluster** of co-occurring tells — never conclude anything
   from one family, and never frame results as proof of AI authorship.
4. If `confidence` is `low` (under 150 words / 8 sentences), say the text is
   too short for a reliable score and report values without a verdict.
5. For CI gating, use the exit-code contract:

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/slop_lint.py" docs/*.md --genre technical --fail-above slop-cluster
   ```

   Exit 0 = pass, 1 = usage/input error, 2 = a confidently-scored file reached
   the `--fail-above` band. Recommend starting with `--fail-above heavy-slop`
   (warn-first rollout) before tightening to `slop-cluster`.
6. Sanity check after any script edit: `--self-test` must print all PASS.

## Output spec

A report per file: `score` (0-100), `band` (clean / mild / slop-cluster /
heavy-slop), `confidence`, `active_families`, and per-family `value`, `band`,
and `hits` with line numbers. JSON mode emits the same as `schema: 1` JSON.
Bands: <25 clean, 25-49 mild, 50-74 slop-cluster, 75+ heavy-slop. A single
active family caps the score at 24; two cap it at 49 — except leaked chatbot
artifacts (`oaicite`, "As an AI", `utm_source=chatgpt`...), which force ≥50
because their false-positive rate is near zero.

## Gotchas

- **Em dashes are weak evidence.** Human baseline is ~3.23/1k words with a
  huge range, and current models are vendor-suppressed below it. The dash
  family carries minimal weight; never present dash counts as a conclusion.
- **Hedging is only scored when stacked** ("may potentially"). Academic prose
  is legitimately hedge-dense; flagging raw hedges punishes real scholars.
- **Fairness**: the underlying signals overlap legitimate ESL, formal, and
  neurodivergent writing styles. The cluster gate and genre profiles exist to
  protect those writers — do not bypass them, and never report a score as
  evidence about the writer.
- **Thresholds decay.** Lexical tells die when vendors patch them (delve is
  gone; em dashes are fading). Thresholds and the era lexicon are dated
  engineering priors — see `references/thresholds.md` for the 6-12 month
  recalibration protocol before trusting them long-term.
- Code blocks are stripped before scoring; a file that is mostly code will
  come back low-confidence. Score the prose, not the repo.
- The heuristics are tuned for English prose (ASCII word tokenization);
  scores on other languages or heavily accented text are unreliable — say so
  rather than reporting them as fact.

## Pointers

- `scripts/slop_lint.py` — the scorer (`--help`, `--self-test`).
- `references/thresholds.md` — evidence per family, threshold provenance,
  era-lexicon sourcing, fairness rationale, recalibration protocol.
