#!/usr/bin/env python3
"""slop_lint.py — deterministic AI-tell scorer for prose.

Scores text 0-100 for CLUSTERS of AI-writing tells against genre-aware soft
thresholds. Detect/score only; never rewrites. Stdlib only; no network, clock,
or randomness — same input, same output.

Design (provenance in ../references/thresholds.md):
- Primary output is span-anchored findings (file:line hits per family); the
  score is derived from them so a rewrite pass can do bounded edits.
- Cluster gate: no single family can push a document past the "mild" band.
  Signs are heuristics, never proof of authorship (WP:AISIGNS framing).
- Structural families carry double weight vs lexical ones (scrubbing flagged
  vocabulary moves detector accuracy only ~1.6pp; structure is the signal).

Exit codes: 0 = scored (or below --fail-above band), 1 = usage/input error,
2 = --fail-above band met or exceeded.
"""

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

SCHEMA = 1
MIN_WORDS = 150
MIN_SENTENCES = 8

# --- Lexicons -----------------------------------------------------------------
# Era-tagged AI-associated vocabulary, curated from verified sources (Kobak et
# al. Science Advances 2025 style-word list; Liang et al. ICML 2024 appendix
# tables; words named by WP:AISIGNS era bands). NOT a verbatim WP snapshot —
# membership churns; see references/thresholds.md for recalibration guidance.
ERA_VOCAB = {
    # GPT-4 era (2023 - mid-2024): weight 1.0 — mostly decayed in frontier chat
    "delve": 1.0,
    "delves": 1.0,
    "delving": 1.0,
    "delved": 1.0,
    "tapestry": 1.0,
    "testament": 1.0,
    "intricate": 1.0,
    "intricacies": 1.0,
    "pivotal": 1.0,
    "meticulous": 1.0,
    "meticulously": 1.0,
    "commendable": 1.0,
    "multifaceted": 1.0,
    "realm": 1.0,
    "embark": 1.0,
    "paramount": 1.0,
    "garner": 1.0,
    "bolster": 1.0,
    "vibrant": 1.0,
    # GPT-4o era (mid-2024 - mid-2025): weight 1.5
    "nestled": 1.5,
    "bustling": 1.5,
    "boasts": 1.5,
    "boasting": 1.5,
    "underscore": 1.5,
    "underscores": 1.5,
    "underscoring": 1.5,
    "fostering": 1.5,
    "leverage": 1.5,
    "leveraging": 1.5,
    "crucial": 1.5,
    "seamless": 1.5,
    "seamlessly": 1.5,
    "groundbreaking": 1.5,
    # GPT-5 era (mid-2025 on): weight 2.0 — the current, shrinking core
    "emphasizing": 2.0,
    "enhance": 2.0,
    "enhancing": 2.0,
    "highlighting": 2.0,
    "showcasing": 2.0,
    "showcases": 2.0,
}

SIGNIFICANCE_PHRASES = [
    r"stands? as a testament",
    r"plays? a (?:vital|pivotal|crucial|key) role",
    r"marks? a (?:significant|pivotal|important) ",
    r"underscor(?:es|ing) (?:the|its|their)",
    r"highlight(?:s|ing) the (?:importance|significance|need)",
    r"serves? as a (?:reminder|testament|foundation)",
    r"rich (?:cultural )?(?:heritage|tapestry|history)",
    r"in today'?s (?:fast-paced|rapidly evolving|ever-changing|digital)",
    r"(?:ever-evolving|rapidly evolving) (?:landscape|world)",
    r"watershed moment",
    r"enduring legacy",
    r"continues? to captivate",
    r"it(?:'|’)s (?:important|worth) (?:to note|noting)",
    r"it is (?:important|worth) (?:to note|noting)",
    r"no discussion .{0,30}complete without",
    r"unlock(?:s|ing)? the (?:power|potential|full potential)",
    r"a testament to",
    r"\bin (?:conclusion|summary),",
    r"\bto sum up\b",
    r"\bin this (?:article|post|guide),? (?:we|you)(?:'|’)?(?:ll| will)?\b",
    r"\bwithout further ado\b",
]

# Trailing present-participle pivot: ", <verb>ing ..." asserting significance.
ING_PIVOT = re.compile(
    r",\s+(?:highlighting|underscoring|showcasing|reflecting|emphasizing|"
    r"demonstrating|ensuring|solidifying|cementing|signaling|signalling|"
    r"paving|reinforcing|illustrating|marking|fostering)\b",
    re.IGNORECASE,
)

NEG_PARALLEL = [
    re.compile(
        r"\bnot (?:just|only|merely|simply)\b[^.!?\n]{0,70}?\b(?:but|it(?:'|’)s|it is)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:it(?:'|’)s|it is|this is|that(?:'|’)s) not (?:about |just |only |merely )?[^.!?\n]{0,50}[,;—-]\s*(?:it(?:'|’)s|it is|but)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bisn(?:'|’)t (?:just|about|merely|only)\b[^.!?\n]{0,70}?\b(?:it(?:'|’)s|but)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bno \w+\.\s*no \w+\.\s*just\b", re.IGNORECASE),
    re.compile(r"\bnot because\b[^.!?\n]{0,60}?\bbut because\b", re.IGNORECASE),
]

TRICOLON = re.compile(r"\b\w+(?:ly)?, \w+(?:ly)?, and \w+", re.IGNORECASE)

# Chatbot artifacts and leaked interface markup: near-zero false positives.
ARTIFACTS = [
    r"\bas an ai(?: language model| assistant)?\b",
    r"\bi hope this (?:helps|email finds you well)\b",
    r"\bgreat question!",
    r"\bi(?:'|’)d be happy to\b",
    r"\bknowledge cutoff\b",
    r"\bas of my last (?:knowledge )?update\b",
    r"\blet me know if you(?:'|’)d like\b",
    r"\bto answer your question\b",
    r"contentReference",
    r"oaicite",
    r"turn\d+(?:search|view|news)\d+",
    r"\[cite[:_]",
    r"grok_card",
    r"utm_source=(?:chatgpt|openai)",
    r"\[start_span\]",
]

HEDGE_STACKS = re.compile(
    r"\b(?:may|might|could|can) (?:potentially|possibly|perhaps|arguably)\b|"
    r"\b(?:potentially|possibly) (?:may|might|could)\b",
    re.IGNORECASE,
)

BULLET_LINE = re.compile(r"^\s*(?:[-*•+]|\d+[.)])\s+")
HEADING_LINE = re.compile(r"^#{1,6}\s+\S")
BOLD_SPAN = re.compile(r"\*\*[^*\n]+\*\*")
FENCE = re.compile(r"^(?:```|~~~)")
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")
SENT_SPLIT = re.compile(r"(?<=[.!?])[\"'”’)\]]*\s+")

# Per-genre soft thresholds: (warn, strong). Engineering priors, not laws —
# derivation and recalibration protocol in references/thresholds.md.
# For burstiness_cv and mtld LOW values are the tell (inverted comparison).
THRESHOLDS = {
    "general": {
        "em_dash": (5, 9),
        "era_vocab": (1.5, 3.0),
        "neg_parallel": (0.6, 1.5),
        "tricolon": (1.5, 3.0),
        "burstiness_cv": (0.45, 0.30),
        "bullet_share": (0.15, 0.30),
        "bold_per_1k": (4, 10),
        "significance": (0.5, 1.5),
        "mtld": (55, 45),
        "list3_share": (0.6, 0.8),
        "hedge_stack": (0.5, 1.5),
    },
    "academic": {
        "em_dash": (6, 11),
        "era_vocab": (1.5, 3.5),
        "neg_parallel": (0.5, 1.2),
        "tricolon": (1.2, 2.5),
        "burstiness_cv": (0.40, 0.28),
        "bullet_share": (0.05, 0.15),
        "bold_per_1k": (2, 6),
        "significance": (0.8, 2.0),
        "mtld": (55, 45),
        "list3_share": (0.6, 0.8),
        "hedge_stack": (0.8, 2.0),
    },
    "technical": {
        "em_dash": (3, 6),
        "era_vocab": (1.2, 2.5),
        "neg_parallel": (0.6, 1.5),
        "tricolon": (1.0, 2.0),
        "burstiness_cv": (0.42, 0.30),
        "bullet_share": (0.45, 0.70),
        "bold_per_1k": (6, 15),
        "significance": (0.4, 1.2),
        "mtld": (50, 40),
        "list3_share": (0.65, 0.85),
        "hedge_stack": (0.5, 1.5),
    },
    "casual": {
        "em_dash": (4, 8),
        "era_vocab": (1.5, 3.5),
        "neg_parallel": (0.8, 2.0),
        "tricolon": (1.5, 3.0),
        "burstiness_cv": (0.50, 0.35),
        "bullet_share": (0.10, 0.25),
        "bold_per_1k": (5, 12),
        "significance": (0.4, 1.2),
        "mtld": (50, 40),
        "list3_share": (0.55, 0.75),
        "hedge_stack": (0.5, 1.5),
    },
}

# Family weights: structure 2x, lexical/diagnostic 1x.
WEIGHTS = {
    "neg_parallel": 2,
    "significance": 2,
    "burstiness": 2,
    "formatting": 2,
    "tricolon": 2,
    "artifacts": 2,
    "era_vocab": 1,
    "em_dash": 1,
    "mtld": 1,
    "hedge_stack": 1,
}


def strip_code(lines):
    """Blank out fenced code blocks and inline code, preserving line numbers.
    CommonMark close rule: same fence char, at least the opener's length —
    so a ````-wrapped block safely contains ``` fences."""
    out, fence = [], None  # fence = (char, length) while inside a block
    for ln in lines:
        m = re.match(r"(`{3,}|~{3,})", ln)
        if m:
            run = m.group(1)
            if fence is None:
                fence = (run[0], len(run))
            elif run[0] == fence[0] and len(run) >= fence[1] and not ln[len(run) :].strip():
                fence = None
            out.append("")
            continue
        out.append("" if fence else re.sub(r"`[^`\n]+`", " ", ln))
    return out


ABBREV = re.compile(r"\b(e\.g|i\.e|vs|Dr|Mr|Mrs|Ms|St|etc|approx|U\.S|cf)\.")


def sentences_of(text):
    parts = []
    for block in re.split(r"\n\s*\n", text):
        block = " ".join(block.split())
        if not block:
            continue
        guarded = ABBREV.sub(lambda m: m.group(0).replace(".", "\x00"), block)
        for s in SENT_SPLIT.split(guarded):
            s = s.replace("\x00", ".")
            if len(WORD.findall(s)) >= 2:
                parts.append(s)
    return parts


def paragraphs_of(lines):
    """Yield (start_line, joined_text) per paragraph so cross-line patterns
    (a clause wrapped onto the next line) still match."""
    start, buf = None, []
    for i, ln in enumerate(lines, 1):
        if ln.strip():
            if start is None:
                start = i
            buf.append(ln.strip())
        elif buf:
            yield start, " ".join(buf)
            start, buf = None, []
    if buf:
        yield start, " ".join(buf)


def find_hits_paragraphs(lines, patterns, flags=re.IGNORECASE):
    hits = []
    for start, text in paragraphs_of(lines):
        for pat in patterns:
            rx = pat if isinstance(pat, re.Pattern) else re.compile(pat, flags)
            for m in rx.finditer(text):
                hits.append({"line": start, "match": m.group(0)[:80]})
    return hits


def mtld(tokens, threshold=0.72):
    """Measure of Textual Lexical Diversity (McCarthy & Jarvis 2010)."""

    def factors(seq):
        count, types, factor_count = 0, set(), 0.0
        for tok in seq:
            count += 1
            types.add(tok)
            ttr = len(types) / count
            if ttr <= threshold:
                factor_count += 1
                count, types = 0, set()
        if count:
            ttr = len(types) / count
            if ttr < 1:
                factor_count += (1 - ttr) / (1 - threshold)
        return factor_count

    if len(tokens) < 50:
        return None
    fwd, bwd = factors(tokens), factors(list(reversed(tokens)))
    if fwd == 0 or bwd == 0:
        return None
    return (len(tokens) / fwd + len(tokens) / bwd) / 2


def find_hits(lines, patterns, flags=re.IGNORECASE):
    hits = []
    for i, ln in enumerate(lines, 1):
        for pat in patterns:
            rx = pat if isinstance(pat, re.Pattern) else re.compile(pat, flags)
            for m in rx.finditer(ln):
                hits.append({"line": i, "match": m.group(0)[:80]})
    return hits


def era_vocab_hits(lines):
    """Weighted era-vocab occurrences that CO-OCCUR (>=2 distinct era words
    within a 100-word window). Isolated hits contribute 0 (WP:AISIGNS density
    rule: single words prove nothing)."""
    positions = []  # (word_index, word, weight, line)
    idx = 0
    for i, ln in enumerate(lines, 1):
        for w in WORD.findall(ln.lower()):
            if w in ERA_VOCAB:
                positions.append((idx, w, ERA_VOCAB[w], i))
            idx += 1
    hits, weight_sum = [], 0.0
    for j, (pos, w, wt, line) in enumerate(positions):
        near_distinct = any(
            abs(p2 - pos) <= 100 and w2 != w for k, (p2, w2, _, _) in enumerate(positions) if k != j
        )
        if near_distinct:
            hits.append({"line": line, "match": w})
            weight_sum += wt
    return hits, weight_sum


def band(value, warn, strong, invert=False):
    """0 below warn; 0.5 at warn; 1.0 at/above strong (linear between)."""
    if value is None:
        return 0.0
    if warn == strong:
        return 1.0 if (value <= strong if invert else value >= strong) else 0.0
    if invert:
        if value > warn:
            return 0.0
        if value <= strong:
            return 1.0
        return 0.5 + 0.5 * (warn - value) / (warn - strong)
    if value < warn:
        return 0.0
    if value >= strong:
        return 1.0
    return 0.5 + 0.5 * (value - warn) / (strong - warn)


def analyze(text, genre):
    th = THRESHOLDS[genre]
    raw_lines = text.splitlines()
    lines = strip_code(raw_lines)
    prose = "\n".join(lines)
    tokens = [w.lower() for w in WORD.findall(prose)]
    n_words = len(tokens)
    sents = sentences_of(prose)
    n_sents = len(sents)

    def per_1k(n):
        return (n / n_words * 1000) if n_words else 0.0

    fam = {}

    em_hits = find_hits(lines, [re.compile(r"—|(?<!-)--(?!-)")])
    fam["em_dash"] = {"value": round(per_1k(len(em_hits)), 2), "hits": em_hits}

    ev_hits, ev_weight = era_vocab_hits(lines)
    fam["era_vocab"] = {"value": round(per_1k(ev_weight), 2), "hits": ev_hits}

    np_hits = find_hits_paragraphs(lines, NEG_PARALLEL)
    fam["neg_parallel"] = {"value": round(per_1k(len(np_hits)), 2), "hits": np_hits}

    tri_hits = find_hits_paragraphs(lines, [TRICOLON])
    tri_value = per_1k(len(tri_hits))
    # exactly-3-item list share (needs >=4 lists to be meaningful)
    lists, current = [], 0
    for ln in [*lines, ""]:
        if BULLET_LINE.match(ln):
            current += 1
        else:
            if current:
                lists.append(current)
            current = 0
    list3_share = (sum(1 for c in lists if c == 3) / len(lists)) if len(lists) >= 4 else None
    tri_band = max(
        band(tri_value, *th["tricolon"]),
        band(list3_share, *th["list3_share"]) if list3_share is not None else 0.0,
    )
    fam["tricolon"] = {"value": round(tri_value, 2), "list3_share": list3_share, "hits": tri_hits}

    cv = None
    if n_sents >= MIN_SENTENCES:
        lens = [len(WORD.findall(s)) for s in sents]
        mean = statistics.mean(lens)
        cv = statistics.pstdev(lens) / mean if mean else None
    fam["burstiness"] = {"value": round(cv, 3) if cv is not None else None, "hits": []}

    nonempty = [ln for ln in lines if ln.strip()]
    bullet_share = (
        (sum(1 for ln in nonempty if BULLET_LINE.match(ln)) / len(nonempty)) if nonempty else 0.0
    )
    bold_hits = find_hits(lines, [BOLD_SPAN])
    fmt_band = max(
        band(bullet_share, *th["bullet_share"]),
        band(per_1k(len(bold_hits)), *th["bold_per_1k"]),
    )
    fam["formatting"] = {
        "value": round(bullet_share, 3),
        "bold_per_1k": round(per_1k(len(bold_hits)), 2),
        "hits": bold_hits[:10],
    }

    sig_hits = find_hits_paragraphs(lines, SIGNIFICANCE_PHRASES) + find_hits_paragraphs(
        lines, [ING_PIVOT]
    )
    fam["significance"] = {"value": round(per_1k(len(sig_hits)), 2), "hits": sig_hits}

    hs_hits = find_hits(lines, [HEDGE_STACKS])
    fam["hedge_stack"] = {"value": round(per_1k(len(hs_hits)), 2), "hits": hs_hits}

    art_hits = find_hits(lines, ARTIFACTS)
    fam["artifacts"] = {"value": len(art_hits), "hits": art_hits}

    m = mtld(tokens)
    fam["mtld"] = {"value": round(m, 1) if m is not None else None, "hits": []}

    bands = {
        "em_dash": band(fam["em_dash"]["value"], *th["em_dash"]),
        "era_vocab": band(fam["era_vocab"]["value"], *th["era_vocab"]),
        "neg_parallel": band(fam["neg_parallel"]["value"], *th["neg_parallel"]),
        "tricolon": tri_band,
        "burstiness": band(cv, *th["burstiness_cv"], invert=True),
        "formatting": fmt_band,
        "significance": band(fam["significance"]["value"], *th["significance"]),
        "hedge_stack": band(fam["hedge_stack"]["value"], *th["hedge_stack"]),
        "artifacts": 1.0 if art_hits else 0.0,
        "mtld": band(m, *th["mtld"], invert=True),
    }
    for name, info in fam.items():
        info["band"] = round(bands[name], 2)
        info["weight"] = WEIGHTS[name]

    total_w = sum(WEIGHTS.values())
    raw_score = 100 * sum(WEIGHTS[k] * bands[k] for k in bands) / total_w
    active = [k for k, b in bands.items() if b >= 0.5]

    # Cluster gate: a single family can never flag a document. Chatbot/markup
    # artifacts are the one exception (near-zero-FP confession).
    score = raw_score
    if art_hits:
        score = max(score, 50.0)
    elif len(active) <= 1:
        score = min(score, 24.0)
    elif len(active) == 2:
        score = min(score, 49.0)

    score = round(score)
    band_name = (
        "clean"
        if score < 25
        else "mild"
        if score < 50
        else "slop-cluster"
        if score < 75
        else "heavy-slop"
    )
    confident = n_words >= MIN_WORDS and n_sents >= MIN_SENTENCES

    return {
        "schema": SCHEMA,
        "genre": genre,
        "words": n_words,
        "sentences": n_sents,
        "confidence": "ok"
        if confident
        else f"low (below {MIN_WORDS} words / {MIN_SENTENCES} sentences)",
        "score": score,
        "band": band_name,
        "active_families": active,
        "families": fam,
        "notes": [
            "Score reflects clusters of co-occurring tells, never a single metric.",
            "This is a style lint, not authorship detection; never use it to accuse a writer.",
            "Thresholds are genre-relative engineering priors; see references/thresholds.md.",
        ],
    }


def human_report(res, name):
    out = [
        f"{name}: score {res['score']}/100 "
        f"({res['band']}, genre={res['genre']}, confidence={res['confidence']})",
        f"  words={res['words']} sentences={res['sentences']} "
        f"active_families={','.join(res['active_families']) or 'none'}",
    ]
    for fname, info in res["families"].items():
        flag = "  <-- " + ("STRONG" if info["band"] >= 1 else "warn") if info["band"] >= 0.5 else ""
        out.append(f"  {fname:<13} value={info['value']!s:<8} band={info['band']:.2f}{flag}")
        for h in info["hits"][:5]:
            out.append(f"      L{h['line']:<5} {h['match']}")
        if len(info["hits"]) > 5:
            out.append(f"      ... {len(info['hits']) - 5} more hits")
    out.extend("  note: " + n for n in res["notes"])
    return "\n".join(out)


SELFTEST_SLOP = """\
In today's fast-paced digital landscape, our platform stands as a testament to
seamless innovation. It's not just a tool, it's a transformative journey. We
delve into intricate challenges, leveraging pivotal insights and showcasing
groundbreaking results, highlighting the importance of meticulous design.

- **Robust:** delivers seamless, vibrant, and intricate workflows
- **Pivotal:** underscores crucial outcomes, emphasizing enduring value
- **Seamless:** fosters commendable results, showcasing multifaceted gains

Our solution plays a pivotal role in the ever-evolving landscape. It marks a
significant milestone, underscoring the importance of innovation. The results
are commendable, reflecting our enduring legacy. Not just efficient, but
transformative. The platform boasts intricate features, ensuring seamless
adoption. It serves as a testament to progress, paving the way for growth.
This underscores the importance of vision. It highlights the significance of
craft. It demonstrates enduring value, cementing our pivotal position.
"""

SELFTEST_HUMAN = """\
I spent Tuesday tearing the water pump out of the Corolla. Twenty-year-old
bolts do not want to move. Two snapped. I drilled them out, swore a lot, and
drove to three stores before finding the right extractor bit.

The pump itself cost forty-one dollars. The gasket was six. What actually hurt
was time: nine hours across two days, most of it on those bolts.

Would I do it again? Probably. The shop quoted $620. But if you try this at
home, soak every bolt in penetrating oil the night before. Cheap insurance.

My neighbor wandered over halfway through and told me about his old Datsun.
Good story. Terrible timing. The radiator was balanced on my knee while he
talked. Some jobs teach patience in ways you didn't ask for.
"""


def selftest():
    slop = analyze(SELFTEST_SLOP, "general")
    human = analyze(SELFTEST_HUMAN, "general")
    checks = [
        ("slop sample scores >= 50", slop["score"] >= 50),
        ("slop sample has >= 3 active families", len(slop["active_families"]) >= 3),
        ("human sample scores < 25", human["score"] < 25),
        ("human sample never flags on cluster gate", len(human["active_families"]) <= 1),
        ("tricolon regex fires", bool(TRICOLON.search("fast, cheap, and reliable"))),
        (
            "neg-parallel regex fires",
            any(rx.search("It's not just a tool, it's a journey") for rx in NEG_PARALLEL),
        ),
        (
            "neg-parallel matches across a line wrap",
            bool(
                find_hits_paragraphs(
                    ["It's not just a tool,", "it's a journey for everyone."], NEG_PARALLEL
                )
            ),
        ),
        (
            "artifact regex fires",
            bool(re.search(ARTIFACTS[0], "as an AI language model", re.IGNORECASE)),
        ),
        (
            "recap scaffold fires",
            bool(
                find_hits_paragraphs(
                    ["In conclusion, the results were mixed."], SIGNIFICANCE_PHRASES
                )
            ),
        ),
        (
            "abbreviations don't split sentences",
            len(sentences_of("We saw Dr. Smith at the lab. He waved at us.")) == 2,
        ),
        (
            "nested fences stay stripped",
            analyze(
                "````text\nprose -- with dashes\n```sh\nrm --rf\n```\nmore -- here\n````\n"
                + SELFTEST_HUMAN,
                "general",
            )["families"]["em_dash"]["value"]
            == 0.0,
        ),
    ]
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    print(f"slop={slop['score']} ({slop['band']}) human={human['score']} ({human['band']})")
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Deterministic AI-tell cluster scorer (0-100). Detect only; never rewrites."
    )
    ap.add_argument("paths", nargs="*", help="text/markdown files ('-' or empty = stdin)")
    ap.add_argument("--genre", choices=sorted(THRESHOLDS), default="general")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON report")
    ap.add_argument(
        "--fail-above",
        choices=["mild", "slop-cluster", "heavy-slop"],
        default=None,
        help="exit 2 if any confident score reaches this band (CI gate)",
    )
    ap.add_argument("--self-test", action="store_true", help="run built-in fixtures and exit")
    args = ap.parse_args(argv)

    if args.self_test:
        return selftest()

    inputs = []
    if not args.paths or args.paths == ["-"]:
        inputs.append(("<stdin>", sys.stdin.read()))
    else:
        for p in args.paths:
            path = Path(p)
            if not path.is_file():
                print(f"ERROR: not a file: {p}", file=sys.stderr)
                return 1
            try:
                inputs.append((p, path.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError) as exc:
                print(f"ERROR: cannot read {p}: {exc}", file=sys.stderr)
                return 1

    band_rank = {"clean": 0, "mild": 1, "slop-cluster": 2, "heavy-slop": 3}
    results, tripped = [], False
    for name, text in inputs:
        res = analyze(text, args.genre)
        res["file"] = name
        results.append(res)
        if (
            args.fail_above
            and res["confidence"] == "ok"
            and band_rank[res["band"]] >= band_rank[args.fail_above]
        ):
            tripped = True

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    else:
        print("\n\n".join(human_report(r, r["file"]) for r in results))

    return 2 if tripped else 0


if __name__ == "__main__":
    sys.exit(main())
