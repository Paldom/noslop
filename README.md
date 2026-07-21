# Noslop

[![CI](https://github.com/Paldom/noslop/actions/workflows/ci.yml/badge.svg)](https://github.com/Paldom/noslop/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![skills.sh](https://skills.sh/b/Paldom/noslop)](https://skills.sh/Paldom/noslop)

Agent Skills that strip AI writing tells from copy - em dashes, 'it's not X, it's Y' constructions, hedging, and bloat - so text reads like a human wrote it, with evals to verify.

Agent Skills for [Claude Code](https://code.claude.com/docs/en/skills) (and any
[Agent Skills](https://agentskills.io)-compatible tool). Each skill is a folder under
[`skills/`](skills/) with a single-purpose `SKILL.md`, trigger evals, and optional
scripts/references — validated on every write, commit, and PR.

## Quick start

Install with the [skills CLI](https://skills.sh) — auto-detects 70+ agents
(Claude Code, Codex, Cursor, Copilot, pi, …):

```bash
npx skills add Paldom/noslop                  # all detected agents
npx skills add Paldom/noslop -a codex -a pi   # or target specific agents
```

Or with the [GitHub CLI](https://cli.github.com/manual/gh_skill_install) (≥ 2.90),
including version-pinned installs from releases:

```bash
gh skill install Paldom/noslop
gh skill install Paldom/noslop <skill> --pin <tag>
```

Or as a Claude Code plugin:

```
/plugin marketplace add Paldom/noslop
/plugin install noslop@noslop
```

Or copy a single skill into a project:

```bash
git clone https://github.com/Paldom/noslop.git
cp -r noslop/skills/<skill-name> your-project/.claude/skills/
```

Then just describe the task — the skill activates on its description — or invoke it
explicitly with `/<skill-name>`.

## Skills

| Skill | Description |
| --- | --- |
| [slop-lint](skills/slop-lint/) | Scores copy 0-100 for clusters of AI-writing tells with a deterministic script — genre-aware soft thresholds, span-anchored findings, CI gating via exit codes. Detect-only. |
| [deslop](skills/deslop/) | Rewrites copy to strip AI-writing tells while preserving meaning and voice — bounded edits on flagged spans only, protected quotes/code/numbers, dialect-safe, with a deterministic post-check. |
| [deslop-verify](skills/deslop-verify/) | Verifies a before/after edit pair with a deterministic script — code, quotes, numbers, links, and identifiers must survive; flags negation flips and over-correction. |

The three skills compose into a pipeline (lint → bounded rewrite → deterministic
verification). See it on real text in [docs/examples.md](docs/examples.md) —
five before/after pairs with measured scores, including the no-op on clean
human prose. To run the pipeline over a whole corpus, paste the ready-made goal
prompt in [docs/setup-prompt.md](docs/setup-prompt.md).

## Repository structure

```
skills/                  # distributed skills, one folder per skill (SKILL.md + evals/ + scripts/)
docs/                    # skill-authoring guide, eval methodology, deployment guide
scripts/                 # deterministic validator used by hooks and CI
skills.sh.json           # skills.sh repo-page customization (groupings)
tests/golden/            # frozen golden corpus + runner: pipeline performance eval (see its README)
.claude/                 # agentic dev setup: hooks + bundled add-skill / publish-repo skills
.claude-plugin/          # plugin + marketplace manifests (makes this repo installable)
.local/                  # gitignored working area: sources, research, PROMPT.md (see below)
```

## Working on this repo with an agent

This repo is agent-native: canonical agent instructions live in
[AGENTS.md](AGENTS.md) (CLAUDE.md imports it), hooks validate every `SKILL.md` on
write, `make check` runs the full validator, and CI enforces the same gate on every
PR. The bundled `add-skill` skill walks the eval-first authoring workflow described
in [docs/skill-authoring.md](docs/skill-authoring.md). Maintainers drive sessions
with their own (gitignored, personal) `.local/PROMPT.md` goal prompt.

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the skill-proposal
process, the authoring workflow, and the PR checklist. Please note the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Support

Questions, ideas, or something not working? Start with [SUPPORT.md](SUPPORT.md) —
bugs and skill proposals have [issue templates](../../issues/new/choose), and
security concerns go through [SECURITY.md](SECURITY.md) (never a public issue).

## License

[MIT](LICENSE) © 2026 Paldom
