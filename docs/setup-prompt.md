# Setup prompt — de-slop a corpus with the noslop pipeline

Paste the `/goal` block below into a Claude Code session in the repository
that holds your prose (docs, marketing copy, posts), with the noslop skills
installed (`npx skills add Paldom/noslop`). Replace the `<...>` placeholders
first. The goal orchestrates the three skills in their designed order —
lint → bounded rewrite → deterministic verification — with the guardrails
(no-op on clean text, dialect/ESL guard, fail-closed verification) enforced
per file.

```text
/goal De-slop the prose files listed under TARGETS until every file passes both gates: slop-lint no longer reports a slop-cluster band, and deslop-verify hard invariants PASS against the saved original. Work autonomously. NEVER run git commit or git push - leave every change in the working tree for my review.

TARGETS: <paths or a glob of prose files, e.g. docs/*.md blog/*.md>
GENRE: <general | academic | technical | casual>

Method (ordering is a constraint):
1. Baseline pass: run the slop-lint skill on every target with GENRE and --json; record file -> score, band, active families. Copy each target to <file>.orig before any edit - the originals are the verification baseline and my diff surface.
2. Files banded clean are no-ops: report them untouched. Never edit clean text to justify the goal.
3. For each remaining file, run the deslop skill: edits bounded to lint-flagged spans plus their sentences, dialect/ESL guard on, quotes/code/numbers/links protected, deletion preferred over synonym swaps, two passes maximum. deslop must finish by running deslop-verify against <file>.orig with the lint report, fail closed: if a hard invariant fails, restore the original and flag the file for me instead of forcing the edit through.
4. Parallelism: agents may run only on disjoint files - one file belongs to exactly one agent, never split a file, at most 4 agents at once. Catalog-wide steps (1 and 5) run single-threaded.
5. Verification bracket, after all edits: re-run slop-lint over every edited file (each must have dropped >=15 points or now band clean) and run deslop-verify <file>.orig <file> --strict per file. If TARGETS includes a known human-written control file, it must come back with edit ratio 0.
6. Final report: a table of file -> before/after score and band, edit ratio, verify result, families fixed, and items deliberately left alone (dialect features, meaning-bearing hedges, the writer's own habits); plus every file left unedited and why. Leave the .orig files in place beside the edited ones.

Definition of Done:
- every target is either edited-and-verified (hard invariants PASS, edit ratio <= 0.30, lint score dropped >= 15 or bands clean) or explicitly reported as a no-op / flagged with a reason
- unflagged prose is byte-identical to the original (spot-check at least 3 files by diff)
- zero git commits or pushes; the final summary lists every file that changed
```

## Notes

- The `/goal` block is ~2,400 characters — well under the 4,000-character goal
  limit, leaving room for your own additions (extra targets, house rules).
- Add a file you wrote yourself to TARGETS as a canary: the pipeline's no-op
  gate should return it untouched, and step 5 makes that a hard check.
- The pipeline never runs detector-evasion passes; if a file's remaining
  warns are legitimate style (academic hedging, a dash-heavy essayist), the
  report says so instead of forcing edits.
- Genre matters: `technical` relaxes list/bold thresholds for READMEs and
  docs; `academic` relaxes hedging. Pick the profile that matches the corpus,
  or run separate goals per corpus.
