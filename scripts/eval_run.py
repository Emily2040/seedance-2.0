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
  (default)     Live. Uses the selected provider's API key. Runs responder +
                judge for each case, prints per-case scores, aggregates against
                the rubric thresholds, and (with --ledger) writes a markdown
                score ledger.

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
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-6"
MINIMAX_MODELS = ("MiniMax-M3", "MiniMax-M2.7")
MINIMAX_ANTHROPIC_BASE_URLS = {
    "global_en": "https://api.minimax.io/anthropic",
    "cn_zh": "https://api.minimaxi.com/anthropic",
}
# Thresholds sourced from references/eval-rubric.md.
LEGACY_MIN, LEGACY_AVG = 2, 2.6          # 0-3 scale
SEQUENCE_CRIT, SEQUENCE_AVG, SEQUENCE_FLOOR = 4, 3.5, 3  # 0-4 scale


@dataclass(frozen=True)
class ProviderConfig:
    api_key_env: str
    default_model: str
    endpoints: Mapping[str, str]
    models: tuple[str, ...] = ()
    auth_header: str = "x-api-key"
    auth_prefix: str = ""


PROVIDER_CONFIGS = {
    "anthropic": ProviderConfig(
        api_key_env="ANTHROPIC_API_KEY",
        default_model=DEFAULT_MODEL,
        endpoints={"global_en": ANTHROPIC_API_URL},
    ),
    "minimax": ProviderConfig(
        api_key_env="MINIMAX_API_KEY",
        default_model=MINIMAX_MODELS[0],
        endpoints={
            region: f"{base_url}/v1/messages"
            for region, base_url in MINIMAX_ANTHROPIC_BASE_URLS.items()
        },
        models=MINIMAX_MODELS,
        auth_header="Authorization",
        auth_prefix="Bearer ",
    ),
}
REGIONS = tuple(sorted({region for config in PROVIDER_CONFIGS.values() for region in config.endpoints}))


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_cases(root: Path) -> list[dict]:
    data = json.loads((root / "evals" / "evals.json").read_text(encoding="utf-8"))
    return data.get("cases", [])


def read_text(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


def is_sequence_case(case: dict) -> bool:
    return "expected_sequence_relation" in case or case.get("critical") is True


def responder_context(root: Path, case: dict) -> str:
    parts = ["# Skill: seedance-20 (root router)", read_text(root / "SKILL.md")]
    for name in case.get("skills_expected_to_activate", []):
        if name == "seedance-20":
            continue  # the root router is already included above
        body = read_text(root / "skills" / name / "SKILL.md", limit=8000)
        if body:
            parts.append(f"\n# Sub-skill: {name}\n{body}")
    fixture = case.get("state_fixture")
    if fixture and (root / fixture).exists():
        parts.append(f"\n# Project state fixture ({fixture})\n{read_text(root / fixture, limit=6000)}")
    return "\n\n".join(parts)


def resolve_provider(
    provider_name: str,
    region: str,
    requested_model: str | None,
) -> tuple[ProviderConfig, str, str]:
    config = PROVIDER_CONFIGS[provider_name]
    endpoint = config.endpoints.get(region)
    if not endpoint:
        supported = ", ".join(sorted(config.endpoints))
        raise ValueError(f"region '{region}' is not supported by provider '{provider_name}' (choose {supported})")
    model = requested_model or config.default_model
    validate_model(provider_name, config, model)
    return config, endpoint, model


def validate_model(provider_name: str, config: ProviderConfig, model: str) -> None:
    if config.models and model not in config.models:
        supported = ", ".join(config.models)
        raise ValueError(f"model '{model}' is not supported by provider '{provider_name}' (choose {supported})")


def call_api(
    system: str,
    user: str,
    model: str,
    api_key: str,
    provider: ProviderConfig,
    endpoint: str,
    max_tokens: int = 1500,
) -> str:
    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(endpoint, data=payload, method="POST")
    req.add_header(provider.auth_header, provider.auth_prefix + api_key)
    req.add_header("anthropic-version", ANTHROPIC_VERSION)
    req.add_header("content-type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return "".join(block.get("text", "") for block in body.get("content", []) if block.get("type") == "text")


def judge(
    case: dict,
    response: str,
    model: str,
    api_key: str,
    rubric: str,
    provider: ProviderConfig,
    endpoint: str,
) -> dict:
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
    raw = call_api(system, user, model, api_key, provider, endpoint, max_tokens=900)
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {"overall_score": 0, "pass": False, "notes": "judge returned no JSON", "assertion_scores": []}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"overall_score": 0, "pass": False, "notes": "unparseable judge JSON", "assertion_scores": []}


def self_test(root: Path) -> int:
    errors: list[str] = []
    cases = load_cases(root)
    if len(cases) < 16:
        errors.append("fewer than 16 cases")
    rubric = read_text(root / "references" / "eval-rubric.md")
    if "0 to 3" not in rubric or "0-4" not in rubric:
        errors.append("eval-rubric.md missing the 0-3 and 0-4 scales")
    seq = 0
    for case in cases:
        cid = case.get("id", "?")
        if not case.get("assertions"):
            errors.append(f"{cid}: no assertions")
        for name in case.get("skills_expected_to_activate", []):
            if name != "seedance-20" and not (root / "skills" / name).is_dir():
                errors.append(f"{cid}: skill '{name}' does not resolve")
        if not responder_context(root, case).strip():
            errors.append(f"{cid}: empty responder context")
        if is_sequence_case(case):
            seq += 1
    if errors:
        print("eval_run self-test FAILED:")
        for e in errors[:40]:
            print(f"- {e}")
        return 1
    print(f"eval_run self-test passed: {len(cases)} cases wired, {seq} on the 0-4 sequence scale, rubric parsed, all skills resolve.")
    return 0


def aggregate(scored: list[dict]) -> int:
    legacy = [s for s in scored if not s["sequence"]]
    seq = [s for s in scored if s["sequence"]]
    ok = True
    if legacy:
        avg = sum(s["score"] for s in legacy) / len(legacy)
        below = [s["id"] for s in legacy if s["score"] < LEGACY_MIN]
        print(f"\nLegacy (0-3): {len(legacy)} cases, avg {avg:.2f} (need >= {LEGACY_AVG}); {len(below)} below {LEGACY_MIN}")
        if avg < LEGACY_AVG or below:
            ok = False
            if below:
                print("  below floor:", ", ".join(below))
    if seq:
        avg = sum(s["score"] for s in seq) / len(seq)
        crit_fail = [s["id"] for s in seq if s.get("critical") and s["score"] < SEQUENCE_CRIT]
        floor_fail = [s["id"] for s in seq if s["score"] < SEQUENCE_FLOOR]
        print(f"Sequence (0-4): {len(seq)} cases, avg {avg:.2f} (need >= {SEQUENCE_AVG}); "
              f"{len(crit_fail)} critical below {SEQUENCE_CRIT}; {len(floor_fail)} below floor {SEQUENCE_FLOOR}")
        if avg < SEQUENCE_AVG or crit_fail or floor_fail:
            ok = False
            if crit_fail:
                print("  critical not at 4:", ", ".join(crit_fail))
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def write_ledger(
    path: Path,
    scored: list[dict],
    model: str,
    stamp: str,
    provider_name: str,
    region: str,
) -> None:
    lines = [
        "# Eval Run Ledger", "",
        f"Last scored: **{stamp}** with responder+judge model `{model}` via provider `{provider_name}` "
        f"in region `{region}` and `scripts/eval_run.py`.",
        "This is the evidence layer for the rubric in `references/eval-rubric.md`; the deterministic",
        "CI validators check shape, this checks output quality. Regenerate with",
        f"`python scripts/eval_run.py --provider {provider_name} --region {region} --model {model} "
        "--ledger evals/eval-run-ledger.md`.", "",
        "| id | scale | score | pass | notes |", "|---|---|---|---|---|",
    ]
    for s in sorted(scored, key=lambda x: (x["sequence"], x["id"])):
        scale = "0-4" if s["sequence"] else "0-3"
        note = (s.get("notes") or "").replace("|", "/").replace("\n", " ")[:80]
        lines.append(f"| {s['id']} | {scale} | {s['score']} | {'yes' if s['pass'] else 'NO'} | {note} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nLedger written to {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Model-in-the-loop eval harness for seedance-20.")
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--self-test", action="store_true", help="offline wiring check, no network")
    parser.add_argument("--strict", action="store_true", help="accepted for parity with other validators")
    parser.add_argument("--provider", choices=sorted(PROVIDER_CONFIGS), default="anthropic")
    parser.add_argument("--region", choices=REGIONS, default="global_en")
    parser.add_argument("--model", default=None, help="responder model id (defaults to the provider's current model)")
    parser.add_argument("--judge-model", default=None, help="override judge model (defaults to --model)")
    parser.add_argument("--id", action="append", help="run only these case ids")
    parser.add_argument("--limit", type=int, default=0, help="cap number of cases (0 = all)")
    parser.add_argument("--ledger", default=None, help="write a markdown score ledger to this path")
    parser.add_argument("--stamp", default="unstamped", help="date label for the ledger (pass an ISO date)")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    if args.self_test:
        return self_test(root)

    try:
        provider, endpoint, model = resolve_provider(args.provider, args.region, args.model)
        judge_model = args.judge_model or model
        validate_model(args.provider, provider, judge_model)
    except ValueError as exc:
        parser.error(str(exc))

    api_key = os.environ.get(provider.api_key_env)
    if not api_key:
        print(f"{provider.api_key_env} not set. Use --self-test for an offline wiring check, "
              "or export a key to run a live scored pass.")
        return 2

    rubric = read_text(root / "references" / "eval-rubric.md")
    cases = load_cases(root)
    if args.id:
        wanted = set(args.id)
        cases = [c for c in cases if c.get("id") in wanted]
    if args.limit:
        cases = cases[: args.limit]

    scored: list[dict] = []
    for case in cases:
        cid = case.get("id", "?")
        try:
            response = call_api(
                responder_context(root, case), case["prompt"], model, api_key, provider, endpoint
            )
            verdict = judge(case, response, judge_model, api_key, rubric, provider, endpoint)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            print(f"[{cid}] API error: {exc}")
            verdict = {"overall_score": 0, "pass": False, "notes": f"api error: {exc}"}
        score = int(verdict.get("overall_score", 0) or 0)
        passed = bool(verdict.get("pass"))
        scored.append({"id": cid, "score": score, "pass": passed,
                       "sequence": is_sequence_case(case), "critical": case.get("critical"),
                       "notes": verdict.get("notes", "")})
        print(f"[{cid}] {'PASS' if passed else 'FAIL'} score={score} :: {str(verdict.get('notes',''))[:70]}")

    if args.ledger:
        write_ledger(Path(args.ledger), scored, model, args.stamp, args.provider, args.region)
    return aggregate(scored)


if __name__ == "__main__":
    raise SystemExit(main())
