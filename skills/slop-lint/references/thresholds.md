# Threshold and lexicon provenance

**Contents:** [What the score means](#what-the-score-means) ·
[Family evidence](#family-evidence) · [Threshold tables](#threshold-tables) ·
[Era lexicon](#era-lexicon) · [Known biases](#known-biases-and-fairness) ·
[Recalibration](#recalibration-protocol)

## What the score means

`slop_lint.py` scores clusters of co-occurring AI-writing tells, 0-100, banded
clean (<25) / mild (25-49) / slop-cluster (50-74) / heavy-slop (75+). The design
follows Wikipedia's "Signs of AI writing" framing: every sign is a heuristic,
useful only in combination, never proof of authorship
(<https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>, WP:AISIGNS).
The cluster gate enforces that mechanically: one active family caps the score
at 24, two at 49. The one exception is the artifacts family (leaked chatbot
phrases and interface markup such as `oaicite`, `turn0search`, `[cite:`,
`utm_source=chatgpt`), which has near-zero false positives and forces >= 50.

The score is a *style lint* for copy you intend to edit. It is not an
authorship detector: detector-style judgments false-flag non-native English
writing at high rates (7 detectors averaged 61.2% false positives on human
TOEFL essays — Liang et al., *Patterns* 2023,
<https://arxiv.org/abs/2304.02819>), which is why this tool scores clusters
against genre baselines and refuses single-signal verdicts.

## Family evidence

Structural families carry weight 2, lexical/diagnostic families weight 1,
because scrubbing flagged vocabulary improves AI-text classification accuracy
by only ~1.6 percentage points — the durable signature is structural
(negative parallelism, uniform rhythm, formatting reflexes, text that explains
its own significance at ~77% vs ~52% for human writing). Both figures are
attributed to a University of Maryland / Google DeepMind study reported
mid-2026 via secondary sources only — no primary citation located; treat them
as directional support for the weighting, not as constants.

| Family | Why it is scored | Strongest source |
| --- | --- | --- |
| neg_parallel | "It's not X, it's Y" contrast scaffolding appeared in ~6% of 328,744 analyzed ChatGPT messages and survives vocabulary de-slopping | Washington Post corpus analysis, Nov 2025 <https://www.washingtonpost.com/technology/interactive/2025/how-detect-chatgpt-em-dash/> |
| significance | Significance inflation ("stands as a testament") and trailing -ing pivots ("..., highlighting...") are WP:AISIGNS core content tells | WP:AISIGNS |
| burstiness | Low sentence-length variance (CV) is the classic LLM regularity signal; human CV roughly 0.5-0.7, LLM default ~0.3-0.45 (engineering prior, not a literature constant) | GPTZero-popularized burstiness; vendor-grade evidence only |
| formatting | Unprompted bullets, bold run-ins, heading inflation are post-training reflexes; too universal for absolute counts, so scored genre-relatively | WP:AISIGNS; SlopBench dropped raw bullet counts as unusable |
| tricolon | Rule-of-three saturation and exactly-3-item list share separate AI/human corpora with simple counting | Solmaz "AI de-smeller" <https://solmaz.io/ai-de-smeller> |
| artifacts | Leaked interface markup ties text to a product family with near-zero false positives (brittle but decisive) | WP:AISIGNS markup section |
| era_vocab | Excess style vocabulary is real but era-bound and decaying; co-occurrence density is the signal, isolated words are not | Kobak et al., *Science Advances* 11(27) 2025, doi 10.1126/sciadv.adt3813 |
| em_dash | Genre-relative, contested, decaying (vendor-suppressed since GPT-5.1, Nov 2025); human baseline ~3.23/1k words with range 0.33-17.12 | "The Last Fingerprint" (arXiv 2603.27006, single-source); Ars Technica Nov 2025 |
| hedge_stack | Raw hedge density is a bad tell (academic prose is legitimately hedge-dense, ~1 hedge per 50 words in science writing — Hyland); only *stacked* hedges ("may potentially") are scored | Hyland's hedging corpus work |
| mtld | Lexical flatness (low Measure of Textual Lexical Diversity) tracks templated output | McCarthy & Jarvis 2010; `diversity` package (arXiv 2403.00553) |

## Threshold tables

The per-genre (warn, strong) pairs embedded in the script are **engineering
priors**, merged from three independent model-panel recommendations plus the
corpus numbers above. They are deliberately soft: crossing warn contributes
0.5 of a family's weight, strong contributes 1.0, and the cluster gate decides
whether anything is reported as slop. No published corpus provides validated
per-genre tables for these exact metrics (COCA/BNC ship nothing directly
usable); treat every number as replaceable by local calibration.

Verified anchors worth knowing when tuning:

- Em dash: human essay baseline ~3.23/1k (range 0.33-17.12); GPT-4.1-era
  models 9-11/1k; GPT-5.4 ~1.4/1k (below human). A per-document em-dash
  threshold is indefensible alone — hence weight 1 and the cluster gate.
- Kobak excess-vocabulary ratios (2024 PubMed abstracts): "delves" r=28.0,
  "underscores" r=13.8, "showcasing" r=10.7; >=13.5% of 2024 abstracts
  LLM-processed. Ratios describe biomedical abstracts — do not transfer to
  blogs without genre norming.
- Liang et al. (ICML 2024, <https://arxiv.org/abs/2403.07183>): "commendable"
  9.8x, "meticulous" 34.7x, "intricate" 11.2x sentence-occurrence spikes in
  ICLR 2024 peer reviews; appendix Tables 2-3 provide top-100 adjective and
  adverb lists if you want to extend the lexicon.

## Era lexicon

The embedded `ERA_VOCAB` dict is curated from the verified sources above and
the era bands WP:AISIGNS maintained as of 2026-07-20, when the live wikitext
was programmatically counted (GPT-4 era: 19 items; GPT-4o era: 12; GPT-5
era: 4 — emphasizing, enhance, highlighting, showcasing — plus a
notability-emphasis word family). It is **not** a verbatim snapshot: the live
page churns, and lexical tells decay fast once patched (delve "dropped off
sharply in 2025"). Weights rise with era recency (1.0 / 1.5 / 2.0) because
current-era words carry more signal. The berenslab companion repo
(<https://github.com/berenslab/llm-excess-vocab>) ships `excess_words.csv`
with 900 rows; if you extend the lexicon from it, filter to the 407
`type=='style'` rows — roughly half the raw file is topic words (covid,
telehealth) that would false-positive.

## Known biases and fairness

The statistical signals this linter uses (low variance, formal register,
predictable vocabulary) overlap legitimate human writing — especially
non-native English, formal/academic prose, and highly structured personal
styles. Mitigations built in: cluster-only flagging, genre profiles, hedge
scoring restricted to stacks, low-confidence refusal under 150 words / 8
sentences, and explicit no-authorship-claims notes in every report. Do not
remove these to make the tool "stricter"; the failure mode is real people
getting flagged for how they naturally write.

## Recalibration protocol

Tells drift with every model release (delve decayed; em dashes were
vendor-suppressed; new tells emerge). Recalibrate every 6-12 months, or after
any frontier-model release:

1. Assemble >= 30 human documents per genre you care about (pre-AI text where
   possible) and >= 30 fresh outputs from current frontier models.
2. Run `slop_lint.py --json` over both piles; collect per-family values.
3. Set warn = ~90th percentile and strong = ~97th percentile of the *human*
   pile per family; sanity-check that the AI pile separates.
4. Edit the `THRESHOLDS` dict (and `ERA_VOCAB` membership/weights) in the
   script; run `--self-test`; commit with the calibration date in the message.
