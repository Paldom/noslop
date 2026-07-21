# Golden corpus — pipeline performance eval

This is the continuous-improvement harness for the noslop skills: a frozen,
append-only corpus plus a deterministic runner, so a change to any SKILL.md,
the playbook, or the lint thresholds can be shown to improve or regress the
pipeline instead of being judged by feel. The agent half (running `deslop`)
is manual by design — deslop is agent behavior, not a function; everything
that scores is deterministic (`slop_lint.py`, `verify_edit.py`).

## Corpus

26 fabricated, original fixtures in `cases/`, indexed by `manifest.json`
with per-case ground truth (`injected_families` for slop cases):

- **12 slop cases** — deliberately injected tells across genres; every one
  lints ≥ mild with 4-6 active families, and each carries protected content
  (numbers, quotes, code, URLs) to pressure the invariants.
- **8 clean controls** — human styles written for the repo (terse,
  dash-heavy essayist, formal academic, casual). Ground truth: no edit.
  We never fabricate "ESL/dialect" text; add your own real pre-AI writing as
  extra controls (it improves the eval but doesn't count toward floors).
- **6 edge cases** — slop-flavored with heavy invariant pressure (code,
  quotes, dense numbers, links, identifiers). Scored descriptively;
  invariants are hard.

Corpus health is checked deterministically (no agent, safe for CI):

```bash
python3 tests/run_golden.py --check-corpus
```

## Producing a run

1. Fresh Claude Code session **per case** (no cross-case contamination).
   In each, invoke deslop with its natural trigger, e.g.
   `deslop tests/golden/cases/slop-05-listicle.md --genre general` (genre
   from the manifest), and save the result verbatim to
   `<outputs-dir>/<case-file-name>` (same file name, your chosen dir).
2. Controls and edge cases go through the identical process — the pipeline
   itself decides that clean controls are no-ops. Do not hint at the
   expected outcome in the prompt.
3. Score the run:

```bash
python3 tests/run_golden.py --outputs runs/2026-07-20-baseline --model claude-fable-5 --note "baseline"
```

## Gates (conjunctive, count-based)

- `invariants_100` — every pair passes verify hard invariants; a missing
  output counts as a failure.
- `controls_zero_touched` — zero controls with edit ratio > 0.02. Stated as
  a count, not a percentage: at n=8, "95%" would just mean "one failure".
- `slop_median_drop_ge_15` and `no_score_increase` — median lint drop ≥ 15
  on slop cases; no case anywhere gets sloppier.
- `localization_median_ge_080` — edits stay inside flagged spans.

Below the per-stratum floors (12/8/6) or with missing outputs, the runner
refuses a PASS/FAIL verdict and reports `INVALID` — a green check on a
handful of cases is false precision.

## Comparison rules

- Every results file records `model`, `date`, `git_sha`, and a hash of the
  SKILL.md + references set. **An A/B of skill changes is only valid within
  one model version.** A new model is a new baseline, not a regression.
- Re-run the suite (or a canary subset) 2-3x before trusting a delta —
  agent output varies between sessions.
- **The corpus is append-only.** Never edit a fixture to make a failure go
  away; add cases. Once you have tuned skill wording against this corpus,
  it is compromised as a gate for that change — generate a fresh slop batch
  (cheap by construction) and use it as the held-out check for the release.
  This is the honest small-scale version of a train/held-out split; revisit
  a real split at ~100+ cases.
- Weighted composite scores are deliberately absent. Detector-bypass-style
  weighting (e.g. HumanizerBench's 42% bypass weight) is the objective this
  repo refuses; gates stay conjunctive so a hard failure can never be
  averaged away.
