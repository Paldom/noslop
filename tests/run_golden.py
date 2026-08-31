#!/usr/bin/env python3
"""run_golden.py — pipeline performance eval for the noslop skills.

Measures whether a change to the skills (SKILL.md wording, playbook,
thresholds) improved or regressed de-slop behavior, using the golden corpus
in tests/golden/. The agent half (running deslop) is manual by design; the
measurement half is fully deterministic via slop_lint.py and verify_edit.py.

Modes:
  --check-corpus            deterministic, agent-free: asserts the corpus is
                            healthy (slop/edge cases lint >= mild, controls
                            lint clean, floors met). Safe for CI.
  --outputs DIR --model M   score a run: DIR holds one <case-stem>.md per
                            manifest case, produced by a deslop session
                            (see tests/golden/README.md for the protocol).
                            Writes a results JSON next to the outputs dir.

Gates (conjunctive, count-based — no weighted composite):
  invariants   100% of pairs pass verify hard invariants        [all strata]
  controls     ZERO controls with edit_ratio > 0.02             [control]
  effect       median lint drop >= 15 AND no case's score rises [slop]
  localization median >= 0.80 over slop cases that edited       [slop]
Floors come from manifest.json; below a floor the aggregate verdict is
INVALID (per-case results still print). Missing outputs count as failures.

Exit codes: 0 gates pass, 1 usage/corpus error, 2 gates fail, 3 aggregate
invalid (floors not met / missing outputs).
"""

import argparse
import datetime
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden"
LINT = ROOT / "skills" / "slop-lint" / "scripts" / "slop_lint.py"
VERIFY = ROOT / "skills" / "deslop-verify" / "scripts" / "verify_edit.py"


def run_json(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if not proc.stdout.strip():
        raise RuntimeError(f"no output from {cmd} (stderr: {proc.stderr[:200]})")
    return json.loads(proc.stdout), proc.returncode


def lint(path, genre):
    data, _ = run_json([sys.executable, str(LINT), str(path), "--genre", genre, "--json"])
    return data


def load_manifest():
    return json.loads((GOLDEN / "manifest.json").read_text(encoding="utf-8"))


def check_corpus():
    man = load_manifest()
    counts = {"slop": 0, "control": 0, "edge": 0}
    problems = []
    for case in man["cases"]:
        path = GOLDEN / case["file"]
        if not path.is_file():
            problems.append("missing file: {}".format(case["file"]))
            continue
        counts[case["stratum"]] += 1
        res = lint(path, case["genre"])
        if res["confidence"] != "ok":
            problems.append(f"{case['file']}: low-confidence lint ({res['words']} words)")
        if case["stratum"] in ("slop", "edge") and res["score"] < 25:
            problems.append(
                f"{case['file']}: {case['stratum']} case lints clean "
                f"({res['score']}) — fixture no longer flags"
            )
        if case["stratum"] == "control" and res["score"] >= 25:
            problems.append(
                f"{case['file']}: control lints {res['band']} ({res['score']}) — must be clean"
            )
    for stratum, floor in man["floors"].items():
        if counts[stratum] < floor:
            problems.append(
                f"floor not met: {stratum} has {counts[stratum]} cases, need >= {floor}"
            )
    if problems:
        print("CORPUS UNHEALTHY:")
        for p in problems:
            print("  - " + p)
        return 1
    print(
        f"corpus healthy: {counts['slop']} slop, {counts['control']} control, "
        f"{counts['edge']} edge cases; floors met"
    )
    return 0


def git_sha():
    try:
        return (
            subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
            ).stdout.strip()
            or None
        )
    except OSError:
        return None


def skill_hash():
    h = hashlib.sha256()
    for p in sorted(ROOT.glob("skills/*/SKILL.md")) + sorted(ROOT.glob("skills/*/references/*.md")):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def score_run(outputs, model, note):
    man = load_manifest()
    outputs = Path(outputs)
    per_case, missing = [], []
    for case in man["cases"]:
        src = GOLDEN / case["file"]
        out = outputs / Path(case["file"]).name
        if not out.is_file():
            missing.append(case["file"])
            per_case.append({"case": case["file"], "stratum": case["stratum"], "status": "MISSING"})
            continue
        before = lint(src, case["genre"])
        after = lint(out, case["genre"])
        lint_json = outputs / (Path(case["file"]).stem + ".lint.json")
        lint_json.write_text(json.dumps(before), encoding="utf-8")
        vres, _vcode = run_json(
            [
                sys.executable,
                str(VERIFY),
                str(src),
                str(out),
                "--lint-report",
                str(lint_json),
                "--json",
            ]
        )
        edited = vres["metrics"]["edit_ratio"] > 0
        per_case.append(
            {
                "case": case["file"],
                "stratum": case["stratum"],
                "status": "ok",
                "score_before": before["score"],
                "score_after": after["score"],
                "drop": before["score"] - after["score"],
                "invariants_pass": vres["pass"],
                "edit_ratio": vres["metrics"]["edit_ratio"],
                "localization": vres["warn"].get("localization", {}).get("value")
                if edited
                else None,
            }
        )
    scored = [c for c in per_case if c["status"] == "ok"]
    slop = [c for c in scored if c["stratum"] == "slop"]
    controls = [c for c in scored if c["stratum"] == "control"]

    floors = man["floors"]
    invalid = bool(missing) or len(slop) < floors["slop"] or len(controls) < floors["control"]

    gates = {}
    gates["invariants_100"] = all(c["invariants_pass"] for c in scored) and not missing
    bad_controls = [c["case"] for c in controls if c["edit_ratio"] > 0.02]
    gates["controls_zero_touched"] = len(bad_controls) == 0
    if slop:
        drops = [c["drop"] for c in slop]
        gates["slop_median_drop_ge_15"] = statistics.median(drops) >= 15
        gates["no_score_increase"] = all(c["drop"] >= 0 for c in scored)
        locs = [c["localization"] for c in slop if c["localization"] is not None]
        gates["localization_median_ge_080"] = (statistics.median(locs) >= 0.80) if locs else False
    result = {
        "schema": 1,
        "date": datetime.date.today().isoformat(),
        "model": model,
        "note": note,
        "git_sha": git_sha(),
        "skill_hash": skill_hash(),
        "aggregate": "INVALID (floors/missing outputs)"
        if invalid
        else ("PASS" if all(gates.values()) else "FAIL"),
        "gates": gates,
        "missing_outputs": missing,
        "controls_touched": bad_controls,
        "per_case": per_case,
    }
    out_file = outputs.parent / (
        "golden-results-{}-{}.json".format(result["date"], (model or "unknown").replace("/", "_"))
    )
    out_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_case"}, indent=2))
    print(f"full results: {out_file}")
    if invalid:
        return 3
    return 0 if result["aggregate"] == "PASS" else 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check-corpus", action="store_true")
    ap.add_argument("--outputs", help="directory of deslop outputs to score")
    ap.add_argument("--model", help="model id that produced the outputs (required with --outputs)")
    ap.add_argument("--note", default="", help="free-form run note (what changed)")
    args = ap.parse_args(argv)
    if args.check_corpus:
        return check_corpus()
    if args.outputs:
        if not args.model:
            print(
                "ERROR: --model is required with --outputs (results are not comparable without it)",
                file=sys.stderr,
            )
            return 1
        if not Path(args.outputs).is_dir():
            print(f"ERROR: outputs dir not found: {args.outputs}", file=sys.stderr)
            return 1
        return score_run(args.outputs, args.model, args.note)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
