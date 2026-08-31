# Changelog

All notable changes to this repository's skills are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org) on the plugin manifest
(breaking skill-interface change → major, new skill → minor, fix → patch).

## [Unreleased]

## [0.2.0] - 2026-08-31

### Added
- Adopted the current skillskit gate: executed trigger evals scoring every trigger
  prompt against every skill description (rank-1 routing accuracy 78.9%), a security
  scan over skill content and bundled scripts, ruff lint and format, README-shape
  validation, pre-commit hooks and a write-time lint hook.

### Fixed
- Findings the new lint gate surfaced in this repo's own scripts, fixed at the source;
  where a rule was wrong for a line it is suppressed there with its reason, never by
  dropping the rule.


Nothing yet.

## [0.1.0] - 2026-07-21

### Fixed
- `slop-lint` + `deslop-verify`: fence walkers now follow the CommonMark
  close rule (same char, at least the opener's length), so a ````-wrapped
  block containing ``` fences is treated as one code block — previously the
  inner fence flipped the state and exposed exhibit text to prose scoring
  (found by linting `docs/examples.md` itself).
- `deslop-verify`: the identifiers invariant now tracks distinct identifiers
  (set subset) instead of per-occurrence counts — deleting a slop sentence
  that repeated a product name no longer hard-fails verification (found by
  running the pipeline for `docs/examples.md`).

### Added
- `docs/examples.md`: five measured before/after demonstrations (email,
  LinkedIn post, product blurb, README, and a clean-human no-op) with real
  lint scores, verify results, and edit ratios; linked from the README.
- `slop-lint`: recap/meta-scaffold detection ("In conclusion,", "In summary,",
  "To sum up", "In this article we'll", "Without further ado") in the
  significance family, plus the "to answer your question" chat wrapper in
  artifacts; matching first-line/last-line editing guidance in the deslop
  playbook. (Gap surfaced by comparing against ayghri/i-have-adhd's no-recap
  rules; patterns are WP:AISIGNS-backed.)
- `slop-lint` skill: deterministic 0-100 cluster scorer for AI-writing tells
  (stdlib Python, genre-aware soft thresholds, span-anchored findings,
  `--fail-above` CI gate, built-in self-test).
- `deslop` skill: lint-driven bounded rewrite pass that strips AI tells while
  preserving meaning, voice, and dialect (no-op gate on clean text, two-pass
  cap, mandatory fail-closed verification via `deslop-verify`).
- `deslop-verify` skill: deterministic before/after edit verification
  (hard invariants on code/quotes/numbers/links/identifiers, negation-flip
  alarm, over-correction metrics, `--lint-report` edit localization,
  built-in self-test).
- `docs/setup-prompt.md`: paste-ready `/goal` orchestrating the three skills
  over a corpus (ordering constraints, disjoint-file parallelism, per-file
  verification bracket).
- `tests/golden/` + `tests/run_golden.py`: continuous-improvement performance
  eval — 26-case fabricated corpus (12 slop with ground-truth injected
  families, 8 clean human-style controls, 6 invariant-pressure edge cases),
  deterministic `--check-corpus` health gate, and a count-based conjunctive
  scorer (invariants 100%, zero touched controls, median lint drop ≥15,
  localization ≥0.80) that refuses verdicts below per-stratum floors and
  stamps model/date/SHA into results.
- Repository scaffolded from the skills template.
