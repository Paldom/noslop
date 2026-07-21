#!/usr/bin/env python3
"""verify_edit.py — deterministic before/after verification for text edits.

Given the original and the edited version of a document, asserts that
protected surface content survived and measures over-correction. Stdlib only;
no network, LLM, clock, or randomness. A pass means SURFACE INTEGRITY —
it never proves meaning was preserved (that is not achievable deterministically).

Hard invariants (any failure → exit 2):
  code_fenced   fenced code blocks, byte-exact multiset equality
  code_inline   inline `code` spans, multiset equality
  quotes        quoted spans of >= 5 words survive (whitespace/curly-quote
                normalized; after may add quotes, never lose one)
  numbers       numeric tokens (ints, decimals, %, currency, versions, dates,
                times) multiset EQUALITY — catches deletions and inventions
  urls          URLs + emails, multiset equality (trailing punctuation stripped)
  links         markdown link/image targets, multiset equality
  identifiers   code-ish tokens (snake_case, CamelCase, SCREAMING_CASE,
                @handles) must not be lost

Warn-level checks (reported; exit 2 only with --strict):
  entities      capitalized-run proper-noun proxy, lost/added (crude — no NER)
  negation      negation/modality-word parity in difflib-aligned sentence pairs
  length        after/before word ratio outside [0.75, 1.25]
  edit_ratio    word-level 1 - SequenceMatcher.ratio() above 0.30
  localization  with --lint-report: share of changed lines within ±1 line of a
                lint finding below 0.80
  rhythm        sentence-length CV collapse > 25% (flattening a human's rhythm)

Exit codes: 0 = hard invariants pass, 1 = usage/input error, 2 = failure.
"""

import argparse
import difflib
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

SCHEMA = 1
BIG_INPUT_CHARS = 300_000  # above this, fall back to line-level diffing
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")
FENCE_LINE = re.compile(r"^(?:```|~~~)")
INLINE_CODE = re.compile(r"`[^`\n]+`")
QUOTE = re.compile(r"[\"“]([^\"“”]{10,400}?)[\"”]")
NUMBER = re.compile(
    r"(?<![\w.])[-−]?(?:[$€£]\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)+(?:\.\d+)*|"
    r"\d[\d,]*(?:\.\d+)?\s?%|\d{1,2}:\d{2}|\d[\d,]*(?:\.\d+)?)(?![\w])"
)
URL = re.compile(r"https?://[^\s)\]>\"']+|[\w.+-]+@[\w-]+\.[\w.-]+")
LINK_TARGET = re.compile(r"\]\(([^)\s]+)[^)]*\)")
IDENTIFIER = re.compile(
    r"\b(?:[a-z0-9]+_[a-z0-9_]+|[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+|"
    r"[A-Z]{2,}[0-9]*_[A-Z0-9_]+)\b|@[A-Za-z0-9_]{2,}"
)
CAP_RUN = re.compile(r"(?<![.!?]\s)(?<!^)\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
NEGATION = {"not", "no", "never", "n't", "cannot", "without", "none", "nor"}
MODALITY = {"may", "might", "must", "always", "all", "only", "suggests",
            "suggest", "proves", "prove", "guarantees", "guarantee"}
SENT_SPLIT = re.compile(r"(?<=[.!?])[\"'”’)\]]*\s+")


def words_of(text):
    return WORD.findall(text)


def norm_quote(q):
    return re.sub(r"\s+", " ", q.replace("’", "'").replace("‘", "'")).strip().lower()


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


def cv_of(text):
    lens = [len(WORD.findall(s)) for s in sentences_of(text)]
    if len(lens) < 8:
        return None
    mean = statistics.mean(lens)
    return statistics.pstdev(lens) / mean if mean else None


def multiset(items):
    return Counter(items)


def diff_counter(before, after):
    missing = list((before - after).elements())
    added = list((after - before).elements())
    return missing, added


def fenced_blocks(text):
    """Fenced code blocks via line walk — an unclosed trailing fence is still
    treated as code (so code can't be edited away by breaking the close).
    CommonMark close rule: same fence char, at least the opener's length —
    a ````-wrapped block safely contains ``` fences."""
    blocks, prose_lines, current, fence = [], [], None, None
    for ln in text.splitlines():
        m = re.match(r"(`{3,}|~{3,})", ln)
        if m:
            run = m.group(1)
            if current is None:
                current, fence = [ln], (run[0], len(run))
            elif run[0] == fence[0] and len(run) >= fence[1] and not ln[len(run):].strip():
                current.append(ln)
                blocks.append("\n".join(current))
                current, fence = None, None
            else:
                current.append(ln)
            prose_lines.append("")
            continue
        if current is not None:
            current.append(ln)
            prose_lines.append("")
        else:
            prose_lines.append(ln)
    if current is not None:
        blocks.append("\n".join(current))
    return blocks, "\n".join(prose_lines)


def clean_url(u):
    return u.rstrip(".,;:!?")


def extract_all(text):
    fenced, prose = fenced_blocks(text)
    inline = INLINE_CODE.findall(prose)
    prose_no_code = INLINE_CODE.sub(" ", prose)
    return {
        "code_fenced": multiset(fenced),
        "code_inline": multiset(inline),
        "quotes": multiset(norm_quote(q) for q in QUOTE.findall(prose_no_code)
                           if len(q.split()) >= 5),
        "numbers": multiset(n.replace(",", "").replace(" ", "")
                            for n in NUMBER.findall(prose_no_code)),
        "urls": multiset(clean_url(u) for u in URL.findall(prose)),
        "links": multiset(LINK_TARGET.findall(prose)),
        "identifiers": multiset(IDENTIFIER.findall(prose_no_code)),
        "entities": multiset(CAP_RUN.findall(prose_no_code)),
        "_prose": prose_no_code,
    }


def _polarity_tokens(text):
    text = text.replace("’", "'").lower()
    return WORD.findall(text) + re.findall(r"n't", text)


def negation_check(before_text, after_text):
    """Compare negation/modality counts across every changed block (replace,
    delete, AND insert — a deleted 'never'-sentence is a flag, not a skip)."""
    sb, sa = sentences_of(before_text), sentences_of(after_text)
    sm = difflib.SequenceMatcher(a=sb, b=sa, autojunk=False)
    flags = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        btxt = " ".join(sb[i1:i2])
        atxt = " ".join(sa[j1:j2])
        wb, wa = _polarity_tokens(btxt), _polarity_tokens(atxt)
        for vocab, label in ((NEGATION, "negation"), (MODALITY, "modality")):
            cb = sum(1 for w in wb if w in vocab)
            ca = sum(1 for w in wa if w in vocab)
            if cb != ca:
                flags.append({"kind": label,
                              "before": (btxt or "<nothing>")[:120],
                              "after": (atxt or "<nothing>")[:120]})
    return flags


def changed_lines(before_text, after_text):
    n_before = len(before_text.splitlines())
    sm = difflib.SequenceMatcher(a=before_text.splitlines(), b=after_text.splitlines(), autojunk=False)
    lines = set()
    for tag, i1, i2, _, _ in sm.get_opcodes():
        if tag == "equal":
            continue
        if i1 == i2:  # pure insert: attribute to the neighboring before-lines
            lines.update(ln for ln in (i1, i1 + 1) if 1 <= ln <= max(n_before, 1))
        else:
            lines.update(range(i1 + 1, i2 + 1))
    return lines


def lint_flagged_lines(report_path):
    data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    docs = data if isinstance(data, list) else [data]
    flagged = set()
    for doc in docs:
        for fam in doc.get("families", {}).values():
            for hit in fam.get("hits", []):
                if "line" in hit:
                    flagged.add(hit["line"])
    return flagged


def verify(before_text, after_text, lint_report=None):
    b, a = extract_all(before_text), extract_all(after_text)
    hard, warn = {}, {}

    for key, mode in (("code_fenced", "equal"), ("code_inline", "equal"),
                      ("quotes", "subset"), ("numbers", "equal"),
                      ("urls", "equal"), ("links", "equal"),
                      ("identifiers", "set_subset")):
        if mode == "set_subset":
            # distinct values must survive; repeated mentions may collapse
            # (deleting a slop sentence that repeats a product name is fine)
            missing, added = sorted(set(b[key]) - set(a[key])), []
        else:
            missing, added = diff_counter(b[key], a[key])
        ok = not missing if mode in ("subset", "set_subset") else (not missing and not added)
        hard[key] = {"pass": ok, "missing": missing[:10], "added": added[:10] if mode == "equal" else []}

    ent_missing, ent_added = diff_counter(b["entities"], a["entities"])
    warn["entities"] = {"ok": not ent_missing and not ent_added,
                        "missing": ent_missing[:10], "added": ent_added[:10],
                        "note": "capitalized-run proxy, not real NER"}

    big = max(len(before_text), len(after_text)) > BIG_INPUT_CHARS
    if big:
        warn["negation"] = {"ok": True, "flags": [],
                            "note": "skipped: input over %d chars" % BIG_INPUT_CHARS}
    else:
        neg = negation_check(b["_prose"], a["_prose"])
        warn["negation"] = {"ok": not neg, "flags": neg[:10]}

    wb, wa = len(words_of(before_text)), len(words_of(after_text))
    ratio = (wa / wb) if wb else (99.0 if wa else 1.0)
    warn["length"] = {"ok": 0.75 <= ratio <= 1.25, "after_over_before": round(ratio, 3)}

    if big:  # line-level ratio: cheaper than word-level on huge inputs
        sm = difflib.SequenceMatcher(a=before_text.splitlines(), b=after_text.splitlines(), autojunk=False)
    else:
        sm = difflib.SequenceMatcher(a=words_of(before_text.lower()), b=words_of(after_text.lower()), autojunk=False)
    edit_ratio = round(1 - sm.ratio(), 4)
    warn["edit_ratio"] = {"ok": edit_ratio <= 0.30, "value": edit_ratio}

    cvb, cva = cv_of(before_text), cv_of(after_text)
    rhythm_ok, collapse = True, None
    if cvb and cva and cvb > 0:
        collapse = round((cvb - cva) / cvb, 3)
        rhythm_ok = collapse <= 0.25
    warn["rhythm"] = {"ok": rhythm_ok, "cv_before": cvb and round(cvb, 3),
                      "cv_after": cva and round(cva, 3), "collapse": collapse}

    if lint_report is not None:
        flagged = lint_flagged_lines(lint_report)
        changed = changed_lines(before_text, after_text)
        near = {ln for f in flagged for ln in (f - 1, f, f + 1)}
        localized = (sum(1 for ln in changed if ln in near) / len(changed)) if changed else 1.0
        warn["localization"] = {"ok": localized >= 0.80, "value": round(localized, 3),
                                "changed_lines": len(changed), "flagged_lines": len(flagged)}

    hard_pass = all(v["pass"] for v in hard.values())
    warn_ok = all(v["ok"] for v in warn.values())
    return {
        "schema": SCHEMA, "pass": hard_pass, "warnings_clean": warn_ok,
        "hard": hard, "warn": warn,
        "metrics": {"edit_ratio": edit_ratio, "length_ratio": round(ratio, 3),
                    "words_before": wb, "words_after": wa},
        "notes": [
            "PASS means surface integrity (protected content survived) - it never proves meaning was preserved.",
            "On clean human text expect edit_ratio near 0; a big ratio on low-slop text is over-correction.",
        ],
    }


def human_report(res):
    out = ["verify: %s (warnings %s)" % ("PASS" if res["pass"] else "FAIL",
                                         "clean" if res["warnings_clean"] else "raised")]
    for name, v in res["hard"].items():
        line = "  hard %-12s %s" % (name, "ok" if v["pass"] else "FAIL")
        if v["missing"]:
            line += "  missing=%s" % v["missing"][:3]
        if v.get("added"):
            line += "  added=%s" % v["added"][:3]
        out.append(line)
    for name, v in res["warn"].items():
        detail = {k: w for k, w in v.items() if k not in ("ok", "flags", "missing", "added", "note")}
        out.append("  warn %-12s %s  %s" % (name, "ok" if v["ok"] else "RAISED", detail or ""))
        for f in v.get("flags", [])[:3]:
            out.append("       %s: '%s' -> '%s'" % (f["kind"], f["before"][:60], f["after"][:60]))
        if v.get("missing") or v.get("added"):
            out.append("       missing=%s added=%s" % (v.get("missing", [])[:3], v.get("added", [])[:3]))
    out.append("  edit_ratio=%.3f length_ratio=%.3f" % (res["metrics"]["edit_ratio"], res["metrics"]["length_ratio"]))
    out.extend("  note: " + n for n in res["notes"])
    return "\n".join(out)


FIX_BEFORE = """\
The migration cut costs by 41% in Q2. "We were honestly surprised by how
smooth it went," said Maria Chen, our platform lead. Run `deploy.sh --canary`
first. See https://example.com/runbook for details.

The team shipped PaymentService v2.3.1 after nine hours of testing. Not
everything went well. The cache layer never recovered on the first try.
"""

FIX_GOOD = """\
The migration cut costs by 41% in Q2. "We were honestly surprised by how
smooth it went," said Maria Chen, our platform lead. Run `deploy.sh --canary`
first. See https://example.com/runbook for details.

The team shipped PaymentService v2.3.1 after nine hours of testing. Some
things broke. The cache layer never recovered on the first try.
"""

FIX_BAD = """\
The migration cut costs by about forty percent in Q2. Maria Chen, our
platform lead, was surprised by how smooth it went. Run the deploy script
first. See the runbook for details.

The team shipped the payment service after extensive testing. Everything
went well. The cache layer recovered on the first try.
"""


def selftest():
    good = verify(FIX_BEFORE, FIX_GOOD)
    bad = verify(FIX_BEFORE, FIX_BAD)
    noop = verify(FIX_BEFORE, FIX_BEFORE)
    neg_del = verify("The cache never crashed after that.\n\nWe kept the fix.",
                     "We kept the fix.")
    signed = verify("Margin moved by -4.2% in Q3.", "Margin moved by 4.2% in Q3.")
    unclosed = verify("intro\n\n```py\nsecret_code()\n", "intro\n")
    trailing = verify("See https://example.com/a.", "See https://example.com/a,")
    checks = [
        ("good edit passes hard invariants", good["pass"]),
        ("no-op passes with edit_ratio 0", noop["pass"] and noop["metrics"]["edit_ratio"] == 0),
        ("bad edit fails hard invariants", not bad["pass"]),
        ("bad edit loses the 41% figure", any("41" in m for m in bad["hard"]["numbers"]["missing"])),
        ("bad edit loses the quote", not bad["hard"]["quotes"]["pass"]),
        ("bad edit loses the URL", not bad["hard"]["urls"]["pass"]),
        ("bad edit loses code", not bad["hard"]["code_inline"]["pass"]),
        ("negation flip caught on good-vs-bad", bool(verify(FIX_GOOD, FIX_BAD)["warn"]["negation"]["flags"])),
        ("deleted never-sentence is flagged", bool(neg_del["warn"]["negation"]["flags"])),
        ("sign flip on -4.2% fails numbers", not signed["hard"]["numbers"]["pass"]),
        ("unclosed fence still protects code", not unclosed["hard"]["code_fenced"]["pass"]),
        ("nested fence is one block",
         len(fenced_blocks("````text\na\n```sh\nb\n```\nc\n````\n")[0]) == 1),
        ("trailing URL punctuation is ignored", trailing["hard"]["urls"]["pass"]),
    ]
    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic before/after edit verification. Never proves meaning; asserts surface integrity.")
    ap.add_argument("before", nargs="?", help="original file")
    ap.add_argument("after", nargs="?", help="edited file")
    ap.add_argument("--lint-report", help="slop-lint --json output for edit-localization check")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="warn-level issues also exit 2")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return selftest()
    if not args.before or not args.after:
        print("ERROR: need BEFORE and AFTER files (or --self-test)", file=sys.stderr)
        return 1
    try:
        before = Path(args.before).read_text(encoding="utf-8")
        after = Path(args.after).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    if args.lint_report and not Path(args.lint_report).is_file():
        print("ERROR: lint report not found: %s" % args.lint_report, file=sys.stderr)
        return 1

    res = verify(before, after, lint_report=args.lint_report)
    print(json.dumps(res, indent=2) if args.json else human_report(res))
    if not res["pass"]:
        return 2
    if args.strict and not res["warnings_clean"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
