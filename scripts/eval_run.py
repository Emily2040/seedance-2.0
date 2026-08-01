#!/usr/bin/env python3
"""Model-in-the-loop eval harness for the seedance-20 skill.

The deterministic CI validators (eval_schema_check.py, sequence_eval_check.py, ...)
prove the eval suite is well-formed. They do not prove the skill actually produces
good output. This harness closes that gap: it runs each case prompt through the
real skill content (root SKILL.md plus the case's expected skills) to get a
response, then asks a judge model to score that response against the case's own
assertions using references/eval-rubric.md.

Two modes:
  --self-test   Offline. Validates wiring only - cases load, the rubric parses,
                every case's skills resolve, a responder context can be built,
                and assertions are non-empty. No network. Safe for CI.
  (default)     Live. Requires ANTHROPIC_API_KEY. Runs responder + judge for each
                case, prints per-case scores, aggregates against the rubric
                thresholds, and (with --ledger) writes a markdown score ledger.

Standard library only; honors HTTPS_PROXY and SSL_CERT_FILE from the environment.
This script is intentionally NOT part of the strict offline CI gate - run it
manually (or in a network-enabled job) when you want evidence, not just shape.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

if __package__:
    from .strict_json import (
        MAX_JSON_BYTES,
        diagnostic_path,
        diagnostic_text,
        load_json,
        loads_json,
        loads_json_bytes,
        read_repo_text,
        validate_repo_input_path,
    )
else:
    from strict_json import (
        MAX_JSON_BYTES,
        diagnostic_path,
        diagnostic_text,
        load_json,
        loads_json,
        loads_json_bytes,
        read_repo_text,
        validate_repo_input_path,
    )

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-6"
# Thresholds sourced from references/eval-rubric.md.
LEGACY_MIN, LEGACY_AVG = 2, 2.6          # 0-3 scale
SEQUENCE_CRIT, SEQUENCE_AVG, SEQUENCE_FLOOR = 4, 3.5, 3  # 0-4 scale


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_cases(root: Path) -> list[dict]:
    data = load_json(
        root / "evals" / "evals.json", expected_type=dict, root=root
    )
    return data.get("cases", [])


def read_text(root: Path, path: Path, limit: int = 12000) -> str:
    if not os.path.lexists(path):
        validate_repo_input_path(root, path.parent)
        return ""
    text = read_repo_text(root=root, path=path)
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


def is_sequence_case(case: dict) -> bool:
    return "expected_sequence_relation" in case or case.get("critical") is True


def responder_context(root: Path, case: dict) -> str:
    parts = [
        "# Skill: seedance-20 (root router)",
        read_text(root, root / "SKILL.md"),
    ]
    for name in case.get("skills_expected_to_activate", []):
        if name == "seedance-20":
            continue  # the root router is already included above
        body = read_text(root, root / "skills" / name / "SKILL.md", limit=8000)
        if body:
            parts.append(f"\n# Sub-skill: {name}\n{body}")
    fixture = case.get("state_fixture")
    if fixture:
        fixture_text = read_text(root, root / fixture, limit=6000)
        if fixture_text:
            parts.append(
                f"\n# Project state fixture ({fixture})\n{fixture_text}"
            )
    return "\n\n".join(parts)


def call_api(system: str, user: str, model: str, api_key: str, max_tokens: int = 1500) -> str:
    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=payload, method="POST")
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", ANTHROPIC_VERSION)
    req.add_header("content-type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = loads_json_bytes(
            resp.read(MAX_JSON_BYTES + 1), expected_type=dict
        )
    return "".join(block.get("text", "") for block in body.get("content", []) if block.get("type") == "text")


def judge(case: dict, response: str, model: str, api_key: str, rubric: str) -> dict:
    scale = "0-4" if is_sequence_case(case) else "0-3"
    extra = ""
    if case.get("forbidden_behaviors"):
        extra += "\nForbidden behaviors (any present => fail):\n- " + "\n- ".join(case["forbidden_behaviors"])
    if case.get("required_output_sections"):
        extra += "\nRequired output sections:\n- " + "\n- ".join(case["required_output_sections"])
    system = (
        "You are a strict eval judge for an AI video-prompting skill. Apply the rubric exactly and "
        "return ONLY a JSON object, no prose. Be skeptical: reward only behavior that is actually present."
    )
    user = (
        f"RUBRIC:\n{rubric}\n\n"
        f"Use the {scale} scale for this case.\n"
        f"CASE PROMPT:\n{case['prompt']}\n\n"
        f"ASSERTIONS (each must be satisfied):\n- " + "\n- ".join(case["assertions"]) + extra + "\n\n"
        f"CANDIDATE RESPONSE TO GRADE:\n{response}\n\n"
        'Return JSON: {"assertion_scores":[{"assertion":str,"met":bool}],'
        '"overall_score":int,"pass":bool,"notes":str}. '
        f'overall_score is on the {scale} scale.'
    )
    raw = call_api(system, user, model, api_key, max_tokens=900)
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {"overall_score": 0, "pass": False, "notes": "judge returned no JSON", "assertion_scores": []}
    try:
        return loads_json(match.group(0), expected_type=dict)
    except ValueError:
        return {"overall_score": 0, "pass": False, "notes": "unparseable judge JSON", "assertion_scores": []}


def self_test(root: Path) -> int:
    errors: list[str] = []
    cases = load_cases(root)
    if len(cases) < 16:
        errors.append("fewer than 16 cases")
    rubric = read_text(root, root / "references" / "eval-rubric.md")
    if "0 to 3" not in rubric or "0-4" not in rubric:
        errors.append("eval-rubric.md missing the 0-3 and 0-4 scales")
    seq = 0
    for case in cases:
        cid = case.get("id", "?")
        if not case.get("assertions"):
            errors.append(f"{cid}: no assertions")
        for name in case.get("skills_expected_to_activate", []):
            if name != "seedance-20" and not (root / "skills" / name).is_dir():
                errors.append(
                    f"{diagnostic_text(cid)}: skill '{diagnostic_text(name)}' does not resolve"
                )
        if not responder_context(root, case).strip():
            errors.append(f"{cid}: empty responder context")
        if is_sequence_case(case):
            seq += 1
    if errors:
        print("eval_run self-test FAILED:")
        for e in errors[:40]:
            print(diagnostic_text(f"- {e}"))
        return 1
    print(
        diagnostic_text(
            f"eval_run self-test passed: {len(cases)} cases wired, {seq} on the "
            "0-4 sequence scale, rubric parsed, all skills resolve."
        )
    )
    return 0


def aggregate(scored: list[dict]) -> int:
    legacy = [s for s in scored if not s["sequence"]]
    seq = [s for s in scored if s["sequence"]]
    ok = True
    if legacy:
        avg = sum(s["score"] for s in legacy) / len(legacy)
        below = [s["id"] for s in legacy if s["score"] < LEGACY_MIN]
        print()
        print(
            diagnostic_text(
                f"Legacy (0-3): {len(legacy)} cases, avg {avg:.2f} "
                f"(need >= {LEGACY_AVG}); {len(below)} below {LEGACY_MIN}"
            )
        )
        if avg < LEGACY_AVG or below:
            ok = False
            if below:
                print(diagnostic_text("  below floor: " + ", ".join(below)))
    if seq:
        avg = sum(s["score"] for s in seq) / len(seq)
        crit_fail = [s["id"] for s in seq if s.get("critical") and s["score"] < SEQUENCE_CRIT]
        floor_fail = [s["id"] for s in seq if s["score"] < SEQUENCE_FLOOR]
        print(
            diagnostic_text(
                f"Sequence (0-4): {len(seq)} cases, avg {avg:.2f} "
                f"(need >= {SEQUENCE_AVG}); {len(crit_fail)} critical below "
                f"{SEQUENCE_CRIT}; {len(floor_fail)} below floor "
                f"{SEQUENCE_FLOOR}"
            )
        )
        if avg < SEQUENCE_AVG or crit_fail or floor_fail:
            ok = False
            if crit_fail:
                print(
                    diagnostic_text(
                        "  critical not at 4: " + ", ".join(crit_fail)
                    )
                )
    print()
    print(diagnostic_text("RESULT: " + ("PASS" if ok else "FAIL")))
    return 0 if ok else 1


def write_ledger(path: Path, scored: list[dict], model: str, stamp: str) -> None:
    lines = [
        "# Eval Run Ledger", "",
        f"Last scored: **{stamp}** with responder+judge model `{model}` via `scripts/eval_run.py`.",
        "This is the evidence layer for the rubric in `references/eval-rubric.md`; the deterministic",
        "CI validators check shape, this checks output quality. Regenerate with",
        "`python scripts/eval_run.py --run --ledger evals/eval-run-ledger.md`.", "",
        "| id | scale | score | pass | notes |", "|---|---|---|---|---|",
    ]
    for s in sorted(scored, key=lambda x: (x["sequence"], x["id"])):
        scale = "0-4" if s["sequence"] else "0-3"
        note = (s.get("notes") or "").replace("|", "/").replace("\n", " ")[:80]
        lines.append(f"| {s['id']} | {scale} | {s['score']} | {'yes' if s['pass'] else 'NO'} | {note} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print()
    print(diagnostic_text(f"Ledger written to {diagnostic_path(path)}"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Model-in-the-loop eval harness for seedance-20.")
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--self-test", action="store_true", help="offline wiring check, no network")
    parser.add_argument("--strict", action="store_true", help="accepted for parity with other validators")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="responder + judge model id")
    parser.add_argument("--judge-model", default=None, help="override judge model (defaults to --model)")
    parser.add_argument("--id", action="append", help="run only these case ids")
    parser.add_argument("--limit", type=int, default=0, help="cap number of cases (0 = all)")
    parser.add_argument("--ledger", default=None, help="write a markdown score ledger to this path")
    parser.add_argument("--stamp", default="unstamped", help="date label for the ledger (pass an ISO date)")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    if args.self_test:
        try:
            return self_test(root)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(diagnostic_text(f"eval_run self-test FAILED: {exc}"))
            return 1

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set. Use --self-test for an offline wiring check, "
              "or export a key to run a live scored pass.")
        return 2

    try:
        rubric = read_text(root, root / "references" / "eval-rubric.md")
        cases = load_cases(root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(diagnostic_text(f"eval_run repository input error: {exc}"))
        return 1
    judge_model = args.judge_model or args.model
    if args.id:
        wanted = set(args.id)
        cases = [c for c in cases if c.get("id") in wanted]
    if args.limit:
        cases = cases[: args.limit]

    scored: list[dict] = []
    for case in cases:
        cid = case.get("id", "?")
        try:
            response = call_api(responder_context(root, case), case["prompt"], args.model, api_key)
            verdict = judge(case, response, judge_model, api_key, rubric)
            score = int(verdict.get("overall_score", 0) or 0)
            passed = bool(verdict.get("pass"))
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            print(diagnostic_text(f"[{cid}] API error: {exc}"))
            verdict = {"overall_score": 0, "pass": False, "notes": f"api error: {exc}"}
            score = 0
            passed = False
        scored.append({"id": cid, "score": score, "pass": passed,
                       "sequence": is_sequence_case(case), "critical": case.get("critical"),
                       "notes": verdict.get("notes", "")})
        print(
            diagnostic_text(
                f"[{cid}] {'PASS' if passed else 'FAIL'} score={score} :: "
                f"{str(verdict.get('notes', ''))[:70]}"
            )
        )

    if args.ledger:
        write_ledger(Path(args.ledger), scored, args.model, args.stamp)
    return aggregate(scored)


if __name__ == "__main__":
    raise SystemExit(main())
