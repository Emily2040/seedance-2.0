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
import http.client
import json
import os
import re
import sys
import tempfile
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
SEQUENCE_DIMENSIONS = (
    "routing correctness",
    "story architecture",
    "clip-scope control",
    "actual-state grounding",
    "continuity integrity",
    "reference binding",
    "mode and surface selection",
    "endpoint quality",
    "prompt architecture",
    "uncertainty handling",
    "safety and rights",
)


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
REGIONS = tuple(
    sorted({region for config in PROVIDER_CONFIGS.values() for region in config.endpoints})
)


class ProviderResponseError(RuntimeError):
    """A successful HTTP response did not contain usable model evidence."""


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _is_utf8_encodable(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _validate_json_strings(value: object) -> None:
    if isinstance(value, str):
        if not _is_utf8_encodable(value):
            raise ValueError("JSON contains an unpaired surrogate")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_strings(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_json_strings(key)
            _validate_json_strings(item)


def strict_json_loads(text: str) -> object:
    """Decode standards-compliant JSON and reject ambiguous object keys."""
    value = json.loads(
        text,
        parse_constant=_reject_json_constant,
        object_pairs_hook=_reject_duplicate_json_keys,
    )
    _validate_json_strings(value)
    return value


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_cases(root: Path) -> list[dict]:
    data = strict_json_loads(
        (root / "evals" / "evals.json").read_text(encoding="utf-8")
    )
    if not isinstance(data, dict):
        raise ValueError("evals.json root must be a JSON object")
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("evals.json 'cases' must be a JSON list")
    if any(not isinstance(case, dict) for case in cases):
        raise ValueError("every eval case must be a JSON object")
    return cases


def read_text(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


def is_sequence_case(case: dict) -> bool:
    return "expected_sequence_relation" in case or case.get("critical") is True


def expected_judge_checks(case: dict) -> list[str]:
    """Return every case criterion that the judge must score exactly once."""
    checks = list(case.get("assertions", []))
    checks.extend(
        f"[required_output_section] {section}"
        for section in case.get("required_output_sections", [])
    )
    checks.extend(
        f"[forbidden_behavior_absent] {behavior}"
        for behavior in case.get("forbidden_behaviors", [])
    )
    return checks


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
        raise ValueError(
            f"region '{region}' is not supported by provider '{provider_name}' "
            f"(choose {supported})"
        )
    model = requested_model or config.default_model
    validate_model(provider_name, config, model)
    return config, endpoint, model


def validate_model(provider_name: str, config: ProviderConfig, model: str) -> None:
    if config.models and model not in config.models:
        supported = ", ".join(config.models)
        raise ValueError(
            f"model '{model}' is not supported by provider '{provider_name}' "
            f"(choose {supported})"
        )


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
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw_body = resp.read()
    except (urllib.error.HTTPError, urllib.error.URLError):
        raise
    except (http.client.HTTPException, OSError) as exc:
        raise ProviderResponseError("model API response body could not be read") from exc
    try:
        body = strict_json_loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProviderResponseError("model API returned invalid JSON") from exc
    if not isinstance(body, dict):
        raise ProviderResponseError("model API response must be a JSON object")
    content = body.get("content")
    if not isinstance(content, list) or any(not isinstance(block, dict) for block in content):
        raise ProviderResponseError("model API response has invalid content blocks")
    if any(
        block.get("type") == "text" and not isinstance(block.get("text"), str)
        for block in content
    ):
        raise ProviderResponseError("model API response has an invalid text block")
    text = "".join(
        block["text"]
        for block in content
        if block.get("type") == "text"
    )
    if not text:
        raise ProviderResponseError("model API response contained no text")
    return text


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
    checks = expected_judge_checks(case)
    if is_sequence_case(case):
        dimension_instruction = (
            " Also return dimension_scores with every dimension copied exactly once "
            "from this list and an integer score from 0 to 4: "
            + json.dumps(SEQUENCE_DIMENSIONS)
            + "."
        )
    else:
        dimension_instruction = " Return dimension_scores as an empty list."
    system = (
        "You are a strict eval judge for an AI video-prompting skill. Apply the rubric exactly and "
        "return ONLY a JSON object, no prose. Be skeptical: reward only behavior that is actually "
        "present. Copy every check string exactly into assertion_scores. A "
        "[forbidden_behavior_absent] check is met only when that behavior is absent."
    )
    user = (
        f"RUBRIC:\n{rubric}\n\n"
        f"Use the {scale} scale for this case.\n"
        f"CASE PROMPT:\n{case['prompt']}\n\n"
        f"CHECKS (each must be satisfied):\n- " + "\n- ".join(checks) + "\n\n"
        f"CANDIDATE RESPONSE TO GRADE:\n{response}\n\n"
        'Return JSON: {"assertion_scores":[{"assertion":str,"met":bool}],'
        '"dimension_scores":[{"dimension":str,"score":int}],'
        '"overall_score":int,"pass":bool,"notes":str}. '
        f'overall_score is on the {scale} scale.' + dimension_instruction
    )
    raw = call_api(
        system,
        user,
        model,
        api_key,
        provider,
        endpoint,
        max_tokens=900,
    )
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {"overall_score": 0, "pass": False, "notes": "judge returned no JSON", "assertion_scores": []}
    try:
        return strict_json_loads(match.group(0))
    except (json.JSONDecodeError, ValueError):
        return {"overall_score": 0, "pass": False, "notes": "unparseable judge JSON", "assertion_scores": []}


def normalize_verdict(case: dict, verdict: object) -> dict:
    """Turn one untrusted judge reply into a strictly typed result."""
    problems: list[str] = []
    try:
        _validate_json_strings(verdict)
    except ValueError as exc:
        return {
            "overall_score": 0,
            "pass": False,
            "notes": f"invalid judge verdict: {exc}",
            "assertion_scores": [],
            "dimension_scores": [],
        }
    if not isinstance(verdict, dict):
        verdict = {}
        problems.append("verdict is not an object")

    score = verdict.get("overall_score")
    maximum = 4 if is_sequence_case(case) else 3
    if type(score) is not int:  # bool is an int subclass and must be rejected.
        problems.append(f"overall_score must be an integer, got {type(score).__name__}")
    elif not 0 <= score <= maximum:
        problems.append(f"overall_score {score} is outside the 0-{maximum} scale")

    passed = verdict.get("pass")
    if type(passed) is not bool:
        problems.append(f"pass must be a boolean, got {type(passed).__name__}")

    notes = verdict.get("notes", "")
    if not isinstance(notes, str):
        problems.append(f"notes must be a string, got {type(notes).__name__}")
        notes = repr(notes)

    expected_assertions = expected_judge_checks(case)
    assertion_scores = verdict.get("assertion_scores")
    if not isinstance(assertion_scores, list):
        problems.append("assertion_scores must be a list")
        assertion_scores = []

    seen: dict[str, bool] = {}
    for row in assertion_scores:
        if not isinstance(row, dict):
            problems.append("each assertion score must be an object")
            continue
        assertion = row.get("assertion")
        met = row.get("met")
        if not isinstance(assertion, str) or type(met) is not bool:
            problems.append(
                "assertion score entries require string assertion and boolean met"
            )
            continue
        if assertion in seen:
            problems.append(f"duplicate assertion score: {assertion}")
        seen[assertion] = met

    if set(seen) != set(expected_assertions) or len(assertion_scores) != len(expected_assertions):
        problems.append("assertion_scores must cover every judge check exactly once")
    if passed is True and any(not seen.get(assertion, False) for assertion in expected_assertions):
        problems.append("pass cannot be true while an assertion is unmet")

    dimension_scores = verdict.get("dimension_scores", [])
    if not isinstance(dimension_scores, list):
        problems.append("dimension_scores must be a list")
        dimension_scores = []
    seen_dimensions: dict[str, int] = {}
    for row in dimension_scores:
        if not isinstance(row, dict):
            problems.append("each dimension score must be an object")
            continue
        dimension = row.get("dimension")
        dimension_score = row.get("score")
        if not isinstance(dimension, str) or type(dimension_score) is not int:
            problems.append(
                "dimension score entries require string dimension and integer score"
            )
            continue
        if not 0 <= dimension_score <= 4:
            problems.append(f"dimension score for {dimension!r} is outside the 0-4 scale")
        if dimension in seen_dimensions:
            problems.append(f"duplicate dimension score: {dimension}")
        seen_dimensions[dimension] = dimension_score

    if is_sequence_case(case):
        if (
            set(seen_dimensions) != set(SEQUENCE_DIMENSIONS)
            or len(dimension_scores) != len(SEQUENCE_DIMENSIONS)
        ):
            problems.append(
                "dimension_scores must cover every sequence dimension exactly once"
            )
    elif dimension_scores:
        problems.append("legacy verdicts must not contain sequence dimension scores")

    if problems:
        detail = "; ".join(dict.fromkeys(problems))
        suffix = f"; judge notes: {notes}" if notes else ""
        return {
            "overall_score": 0,
            "pass": False,
            "notes": f"invalid judge verdict: {detail}{suffix}",
            "assertion_scores": [],
            "dimension_scores": [],
        }
    return {
        "overall_score": score,
        "pass": passed,
        "notes": notes,
        "assertion_scores": assertion_scores,
        "dimension_scores": dimension_scores,
    }


def parse_sequence_dimensions(rubric: str) -> tuple[str, ...]:
    declarations = re.findall(r"^Dimensions:\s*(.+?)\s*$", rubric, re.MULTILINE)
    if len(declarations) != 1:
        raise ValueError("eval-rubric.md must contain exactly one Dimensions declaration")
    declaration = declarations[0].strip()
    if declaration.endswith("."):
        declaration = declaration[:-1]
    dimensions = tuple(part.strip() for part in declaration.split(","))
    if not dimensions or any(not dimension for dimension in dimensions):
        raise ValueError("eval-rubric.md has an invalid Dimensions declaration")
    return dimensions


def validate_sequence_dimension_contract(rubric: str) -> tuple[str, ...]:
    dimensions = parse_sequence_dimensions(rubric)
    if dimensions != SEQUENCE_DIMENSIONS:
        raise ValueError(
            "eval-rubric.md Dimensions must exactly match the evaluator's ordered "
            "sequence dimension contract"
        )
    return dimensions


def self_test(root: Path) -> int:
    errors: list[str] = []
    try:
        cases = load_cases(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print("eval_run self-test FAILED:")
        print(f"- invalid evals/evals.json: {exc}")
        return 1
    if len(cases) < 16:
        errors.append("fewer than 16 cases")
    rubric = read_text(root / "references" / "eval-rubric.md")
    if "0 to 3" not in rubric or "0-4" not in rubric:
        errors.append("eval-rubric.md missing the 0-3 and 0-4 scales")
    try:
        validate_sequence_dimension_contract(rubric)
    except ValueError as exc:
        errors.append(str(exc))
    seq = 0
    seen_ids: set[str] = set()
    for case in cases:
        cid = case.get("id", "?")
        if cid in seen_ids:
            errors.append(f"{cid}: duplicate case id")
        seen_ids.add(cid)
        if not case.get("assertions"):
            errors.append(f"{cid}: no assertions")
        judge_checks = expected_judge_checks(case)
        if any(not isinstance(check, str) or not check for check in judge_checks):
            errors.append(f"{cid}: judge checks must be non-empty strings")
        if len(judge_checks) != len(set(judge_checks)):
            errors.append(f"{cid}: duplicate judge check")
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


def _row_integrity_errors(row: object, index: int) -> list[str]:
    label = f"row {index + 1}"
    if not isinstance(row, dict):
        return [f"{label}: result is not an object"]

    errors: list[str] = []
    case_id = row.get("id")
    if not isinstance(case_id, str) or not case_id.strip():
        errors.append(f"{label}: id must be a non-empty string")
    elif not _is_utf8_encodable(case_id):
        errors.append(f"{label}: id contains an unpaired surrogate")
    else:
        label = case_id

    sequence = row.get("sequence")
    if type(sequence) is not bool:
        errors.append(f"{label}: sequence must be a boolean")

    score = row.get("score")
    maximum = 4 if sequence is True else 3
    if type(score) is not int or not 0 <= score <= maximum:
        errors.append(
            f"{label}: invalid score {score!r}; expected an integer on the 0-{maximum} scale"
        )

    if type(row.get("pass")) is not bool:
        errors.append(f"{label}: pass must be a boolean")
    critical = row.get("critical")
    if type(critical) is not bool:
        errors.append(f"{label}: critical must be a boolean")
    if critical is True and sequence is not True:
        errors.append(f"{label}: critical cases must be sequence cases")

    notes = row.get("notes", "")
    if not isinstance(notes, str):
        errors.append(f"{label}: notes must be a string")
    elif not _is_utf8_encodable(notes):
        errors.append(f"{label}: notes contain an unpaired surrogate")

    dimension_scores = row.get("dimension_scores", [])
    if not isinstance(dimension_scores, list):
        errors.append(f"{label}: dimension_scores must be a list")
        dimension_scores = []
    seen_dimensions: dict[str, int] = {}
    for dimension_row in dimension_scores:
        if not isinstance(dimension_row, dict):
            errors.append(f"{label}: each dimension score must be an object")
            continue
        dimension = dimension_row.get("dimension")
        dimension_score = dimension_row.get("score")
        if not isinstance(dimension, str) or type(dimension_score) is not int:
            errors.append(
                f"{label}: dimension scores require UTF-8 string dimension and integer score"
            )
            continue
        if not _is_utf8_encodable(dimension):
            errors.append(f"{label}: dimension name contains an unpaired surrogate")
            continue
        if not 0 <= dimension_score <= 4:
            errors.append(f"{label}: dimension score {dimension_score!r} is outside 0-4")
        if dimension in seen_dimensions:
            errors.append(f"{label}: duplicate dimension score {dimension}")
        seen_dimensions[dimension] = dimension_score
    if sequence is True and (
        set(seen_dimensions) != set(SEQUENCE_DIMENSIONS)
        or len(dimension_scores) != len(SEQUENCE_DIMENSIONS)
    ):
        errors.append(f"{label}: sequence dimension coverage is incomplete")
    if sequence is False and dimension_scores:
        errors.append(f"{label}: legacy row contains sequence dimension scores")
    return errors


def build_expected_case_metadata(cases: list[dict]) -> dict[str, dict[str, bool]]:
    """Derive release descriptors from canonical eval cases.

    The returned map is the assessment boundary: result rows are checked against
    these canonical sequence/critical flags instead of being trusted to classify
    themselves.
    """
    metadata: dict[str, dict[str, bool]] = {}
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"expected case {index + 1} is not an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"expected case {index + 1} has an invalid id")
        if not _is_utf8_encodable(case_id):
            raise ValueError(
                f"expected case {index + 1} id contains an unpaired surrogate"
            )
        if case_id in metadata:
            raise ValueError(f"duplicate expected case id: {case_id}")
        critical = case.get("critical", False)
        if type(critical) is not bool:
            raise ValueError(f"{case_id}: critical must be a boolean when present")
        sequence = is_sequence_case(case)
        if critical and not sequence:
            raise ValueError(f"{case_id}: critical cases must be sequence cases")
        metadata[case_id] = {"sequence": sequence, "critical": critical}
    return metadata


def _expected_metadata_errors(
    expected_cases: Mapping[str, object],
) -> list[str]:
    errors: list[str] = []
    for case_id, descriptor in expected_cases.items():
        if (
            not isinstance(case_id, str)
            or not case_id.strip()
            or not _is_utf8_encodable(case_id)
        ):
            errors.append("expected case metadata ids must be non-empty UTF-8 strings")
            continue
        if not isinstance(descriptor, Mapping):
            errors.append(f"{case_id}: expected case metadata must be an object")
            continue
        sequence = descriptor.get("sequence")
        critical = descriptor.get("critical")
        if type(sequence) is not bool:
            errors.append(f"{case_id}: expected sequence flag must be a boolean")
        if type(critical) is not bool:
            errors.append(f"{case_id}: expected critical flag must be a boolean")
        if critical is True and sequence is not True:
            errors.append(f"{case_id}: critical expected cases must be sequence cases")
    return errors


def assess_run(
    scored: list[object],
    *,
    expected_ids: list[str] | None = None,
    expected_cases: Mapping[str, object] | None = None,
    release_eligible: bool = True,
    total_expected: int | None = None,
) -> dict:
    """Validate completeness and calculate a release verdict without printing.

    A release PASS requires both an explicit ``total_expected`` and canonical
    ``expected_cases`` metadata. IDs alone can prove identity coverage, but not
    whether a result row forged its sequence or critical classification.
    """
    integrity_errors: list[str] = []
    if type(release_eligible) is not bool:
        integrity_errors.append("release_eligible must be a boolean")
        release_eligible = False
    if not scored:
        integrity_errors.append("no scored results were produced")

    for index, row in enumerate(scored):
        integrity_errors.extend(_row_integrity_errors(row, index))

    actual_ids = [
        row.get("id")
        for row in scored
        if (
            isinstance(row, dict)
            and isinstance(row.get("id"), str)
            and _is_utf8_encodable(row["id"])
        )
    ]
    duplicate_ids = sorted({case_id for case_id in actual_ids if actual_ids.count(case_id) > 1})
    if duplicate_ids:
        integrity_errors.append("duplicate result ids: " + ", ".join(duplicate_ids))

    metadata_errors: list[str] = []
    if expected_cases is not None:
        if not isinstance(expected_cases, Mapping):
            metadata_errors.append("expected_cases must be a metadata map")
            canonical_ids: list[str] = []
        else:
            metadata_errors.extend(_expected_metadata_errors(expected_cases))
            canonical_ids = [
                case_id
                for case_id in expected_cases
                if isinstance(case_id, str)
                and case_id.strip()
                and _is_utf8_encodable(case_id)
            ]
        integrity_errors.extend(metadata_errors)
    else:
        canonical_ids = []

    if expected_ids is not None:
        invalid_expected_ids = [
            case_id
            for case_id in expected_ids
            if (
                not isinstance(case_id, str)
                or not case_id.strip()
                or not _is_utf8_encodable(case_id)
            )
        ]
        if invalid_expected_ids:
            integrity_errors.append("expected ids must be non-empty UTF-8 strings")
        identity_ids = [
            case_id
            for case_id in expected_ids
            if isinstance(case_id, str) and _is_utf8_encodable(case_id)
        ]
        duplicate_identity_ids = sorted(
            {
                case_id
                for case_id in identity_ids
                if identity_ids.count(case_id) > 1
            }
        )
        if duplicate_identity_ids:
            integrity_errors.append(
                "duplicate expected ids: " + ", ".join(duplicate_identity_ids)
            )
            release_eligible = False
    else:
        identity_ids = []

    if expected_cases is not None:
        selected_ids = list(canonical_ids)
        if expected_ids is not None and set(identity_ids) != set(canonical_ids):
            integrity_errors.append(
                "expected_ids do not match the canonical expected case metadata"
            )
            release_eligible = False
    elif expected_ids is not None:
        selected_ids = list(identity_ids)
    else:
        selected_ids = list(actual_ids)

    if expected_ids is None:
        duplicate_expected = sorted(
            {case_id for case_id in selected_ids if selected_ids.count(case_id) > 1}
        )
        if duplicate_expected:
            integrity_errors.append(
                "duplicate expected ids: " + ", ".join(duplicate_expected)
            )
            release_eligible = False

    missing = sorted(set(selected_ids) - set(actual_ids))
    unexpected = sorted(set(actual_ids) - set(selected_ids))
    if missing:
        integrity_errors.append("missing result ids: " + ", ".join(missing))
    if unexpected:
        integrity_errors.append("unexpected result ids: " + ", ".join(unexpected))

    if expected_cases is not None and isinstance(expected_cases, Mapping):
        for index, row in enumerate(scored):
            if not isinstance(row, dict):
                continue
            case_id = row.get("id")
            descriptor = (
                expected_cases.get(case_id)
                if isinstance(case_id, str) and _is_utf8_encodable(case_id)
                else None
            )
            if not isinstance(descriptor, Mapping):
                continue
            expected_sequence = descriptor.get("sequence")
            expected_critical = descriptor.get("critical")
            if type(expected_sequence) is bool and row.get("sequence") is not expected_sequence:
                integrity_errors.append(
                    f"{case_id}: sequence flag does not match canonical case metadata"
                )
            if type(expected_critical) is bool and row.get("critical") is not expected_critical:
                integrity_errors.append(
                    f"{case_id}: critical flag does not match canonical case metadata"
                )

    selected_count = len(selected_ids)
    if total_expected is not None and (
        type(total_expected) is not int or total_expected < 0
    ):
        integrity_errors.append("total_expected must be a non-negative integer")
        total_expected = None
        release_eligible = False
    canonical_scope_known = expected_cases is not None and not metadata_errors
    scope_known = canonical_scope_known and total_expected is not None
    if not scope_known:
        release_eligible = False
    elif total_expected != selected_count:
        release_eligible = False
        if selected_count > total_expected:
            integrity_errors.append(
                f"selected result universe {selected_count} exceeds total_expected "
                f"{total_expected}"
            )

    valid_rows = [
        row for index, row in enumerate(scored) if not _row_integrity_errors(row, index)
    ]
    legacy = [row for row in valid_rows if not row["sequence"]]
    sequence = [row for row in valid_rows if row["sequence"]]
    failed_verdicts = [row["id"] for row in valid_rows if row["pass"] is False]

    legacy_average = sum(row["score"] for row in legacy) / len(legacy) if legacy else None
    legacy_below = [row["id"] for row in legacy if row["score"] < LEGACY_MIN]
    sequence_average = (
        sum(row["score"] for row in sequence) / len(sequence) if sequence else None
    )
    sequence_critical_fail = [
        row["id"]
        for row in sequence
        if row.get("critical") and row["score"] < SEQUENCE_CRIT
    ]
    sequence_floor_fail = [
        row["id"]
        for row in sequence
        if any(
            dimension["score"] < SEQUENCE_FLOOR
            for dimension in row["dimension_scores"]
        )
    ]

    thresholds_pass = True
    if legacy and (legacy_average < LEGACY_AVG or legacy_below):
        thresholds_pass = False
    if sequence and (
        sequence_average < SEQUENCE_AVG
        or sequence_critical_fail
        or sequence_floor_fail
    ):
        thresholds_pass = False

    run_pass = not integrity_errors and not failed_verdicts and thresholds_pass
    release_verdict = (
        "NOT ELIGIBLE" if not release_eligible else ("PASS" if run_pass else "FAIL")
    )
    return {
        "scope": (
            "UNSCOPED"
            if not scope_known
            else ("COMPLETE" if release_eligible else "PARTIAL")
        ),
        "selected_count": selected_count,
        "total_expected": total_expected,
        "completed_count": len(scored),
        "integrity_errors": integrity_errors,
        "failed_verdicts": failed_verdicts,
        "legacy_count": len(legacy),
        "legacy_average": legacy_average,
        "legacy_below": legacy_below,
        "sequence_count": len(sequence),
        "sequence_average": sequence_average,
        "sequence_critical_fail": sequence_critical_fail,
        "sequence_floor_fail": sequence_floor_fail,
        "run_verdict": "PASS" if run_pass else "FAIL",
        "release_verdict": release_verdict,
        "exit_code": 0 if release_verdict == "PASS" else 1,
    }


def print_assessment(report: dict) -> int:
    if report["integrity_errors"]:
        print("\nIntegrity errors:")
        for error in report["integrity_errors"]:
            print(f"  - {error}")
    if report["failed_verdicts"]:
        print("\nFailed verdicts:", ", ".join(report["failed_verdicts"]))

    if report["legacy_count"]:
        print(
            f"\nLegacy (0-3): {report['legacy_count']} cases, "
            f"avg {report['legacy_average']:.2f} (need >= {LEGACY_AVG}); "
            f"{len(report['legacy_below'])} below {LEGACY_MIN}"
        )
        if report["legacy_below"]:
            print("  below floor:", ", ".join(report["legacy_below"]))
    if report["sequence_count"]:
        print(
            f"Sequence (0-4): {report['sequence_count']} cases, "
            f"avg {report['sequence_average']:.2f} (need >= {SEQUENCE_AVG}); "
            f"{len(report['sequence_critical_fail'])} critical below {SEQUENCE_CRIT}; "
            f"{len(report['sequence_floor_fail'])} below floor {SEQUENCE_FLOOR}"
        )
        if report["sequence_critical_fail"]:
            print("  critical not at 4:", ", ".join(report["sequence_critical_fail"]))

    if report["scope"] == "PARTIAL":
        print(
            f"\nRun scope: PARTIAL ({report['selected_count']} of "
            f"{report['total_expected']} cases); not release-eligible"
        )
    elif report["scope"] == "UNSCOPED":
        print(
            f"\nRun scope: UNSCOPED ({report['selected_count']} results; "
            "release universe unknown); not release-eligible"
        )
    print("\nRESULT:", "PASS" if report["exit_code"] == 0 else "FAIL")
    return report["exit_code"]


def aggregate(
    scored: list[object],
    *,
    expected_ids: list[str] | None = None,
    expected_cases: Mapping[str, object] | None = None,
    release_eligible: bool = True,
    total_expected: int | None = None,
) -> int:
    return print_assessment(
        assess_run(
            scored,
            expected_ids=expected_ids,
            expected_cases=expected_cases,
            release_eligible=release_eligible,
            total_expected=total_expected,
        )
    )


def _atomic_write_text(path: Path, text: str) -> None:
    """Replace a ledger only after its complete contents are safely written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        handle = os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")
        descriptor = -1  # ownership transferred to handle
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        if descriptor != -1:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _ledger_row_sort_key(indexed_row: tuple[int, object]) -> tuple[int, str, int]:
    index, row = indexed_row
    if not isinstance(row, dict):
        return (2, "", index)
    sequence = row.get("sequence")
    sequence_order = 0 if sequence is False else 1 if sequence is True else 2
    case_id = row.get("id")
    safe_id = (
        case_id
        if isinstance(case_id, str) and _is_utf8_encodable(case_id)
        else ""
    )
    return (sequence_order, safe_id, index)


def _safe_ledger_text(value: str, limit: int = 80) -> str:
    if not _is_utf8_encodable(value):
        return "[invalid Unicode string]"
    # Markdown treats several controls as line boundaries even when ``\n`` is
    # absent. Collapse every unsafe C0/C1 control and Unicode line separator
    # before truncation so one field can never create another ledger line.
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]+", " ", value)
    return sanitized.replace("|", "/")[:limit]


def _render_ledger_row(index: int, row: object) -> str:
    """Render even malformed evidence rows without preserving a stale ledger."""
    if not isinstance(row, dict):
        return (
            f"| [invalid row {index + 1}] | invalid | invalid | invalid | INVALID | "
            "result is not an object |"
        )

    raw_id = row.get("id")
    case_id = (
        _safe_ledger_text(raw_id)
        if isinstance(raw_id, str) and raw_id.strip()
        else f"[invalid row {index + 1}]"
    )
    sequence = row.get("sequence")
    scale = "0-4" if sequence is True else "0-3" if sequence is False else "invalid"

    raw_dimensions = row.get("dimension_scores", [])
    dimension_parts: list[str] = []
    if isinstance(raw_dimensions, list):
        for dimension_row in raw_dimensions:
            if not isinstance(dimension_row, dict):
                dimension_parts.append("[invalid dimension row]")
                continue
            dimension = dimension_row.get("dimension")
            dimension_score = dimension_row.get("score")
            if not isinstance(dimension, str) or type(dimension_score) is not int:
                dimension_parts.append("[invalid dimension row]")
                continue
            dimension_parts.append(
                f"{_safe_ledger_text(dimension)}={dimension_score}"
            )
        dimensions = ", ".join(dimension_parts) or "n/a"
    else:
        dimensions = "[invalid dimension_scores]"

    raw_score = row.get("score")
    score = str(raw_score) if type(raw_score) is int else "invalid"
    raw_pass = row.get("pass")
    passed = "yes" if raw_pass is True else "NO" if raw_pass is False else "INVALID"
    raw_note = row.get("notes", "")
    note = (
        _safe_ledger_text(raw_note)
        if isinstance(raw_note, str)
        else "[invalid non-string notes]"
    )
    return (
        f"| {case_id} | {scale} | {dimensions} | {score} | {passed} | {note} |"
    )


def write_ledger(
    path: Path,
    scored: list[object],
    model: str,
    stamp: str,
    provider_name: str,
    region: str,
    *,
    judge_model: str | None = None,
    expected_ids: list[str] | None = None,
    expected_cases: Mapping[str, object] | None = None,
    total_expected: int | None = None,
    release_eligible: bool = False,
) -> dict:
    report = assess_run(
        scored,
        expected_ids=expected_ids,
        expected_cases=expected_cases,
        total_expected=total_expected,
        release_eligible=release_eligible,
    )
    judge_model = judge_model or model
    safe_stamp = _safe_ledger_text(stamp, limit=120)
    safe_model = _safe_ledger_text(model, limit=200)
    safe_judge_model = _safe_ledger_text(judge_model, limit=200)
    safe_provider_name = _safe_ledger_text(provider_name, limit=120)
    safe_region = _safe_ledger_text(region, limit=120)
    if report["scope"] == "UNSCOPED":
        scope_line = (
            f"Run scope: **UNSCOPED** — {report['completed_count']} results recorded; "
            "the release universe was not supplied."
        )
    else:
        scope_line = (
            f"Run scope: **{report['scope']}** — {report['selected_count']} of "
            f"{report['total_expected']} release cases selected; "
            f"{report['completed_count']} results recorded."
        )
    lines = [
        "# Eval Run Ledger",
        "",
        f"Last scored: **{safe_stamp}** with responder model `{safe_model}` and judge model "
        f"`{safe_judge_model}` via provider `{safe_provider_name}` in region `{safe_region}` and "
        "`scripts/eval_run.py`.",
        scope_line,
        f"Run verdict: **{report['run_verdict']}**. Release verdict: "
        f"**{report['release_verdict']}**.",
        "This is the evidence layer for the rubric in `references/eval-rubric.md`; the deterministic",
        "CI validators check shape, this checks output quality. Regenerate with",
        f"`python scripts/eval_run.py --provider {safe_provider_name} --region {safe_region} "
        f"--model {safe_model} --judge-model {safe_judge_model} "
        "--ledger evals/eval-run-ledger.md`.",
        "",
    ]
    if report["integrity_errors"]:
        lines.extend(["## Integrity errors", ""])
        lines.extend(
            f"- {_safe_ledger_text(error, limit=500)}"
            for error in report["integrity_errors"]
        )
        lines.append("")
    lines.extend(
        [
            "| id | scale | dimension scores | score | pass | notes |",
            "|---|---|---|---|---|---|",
        ]
    )
    for index, row in sorted(enumerate(scored), key=_ledger_row_sort_key):
        lines.append(_render_ledger_row(index, row))
    _atomic_write_text(path, "\n".join(lines) + "\n")
    print(f"\nLedger written to {path}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Model-in-the-loop eval harness for seedance-20.")
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--self-test", action="store_true", help="offline wiring check, no network")
    parser.add_argument("--strict", action="store_true", help="accepted for parity with other validators")
    parser.add_argument("--provider", choices=sorted(PROVIDER_CONFIGS), default="anthropic")
    parser.add_argument("--region", choices=REGIONS, default="global_en")
    parser.add_argument(
        "--model",
        default=None,
        help="responder model id (defaults to the provider's current model)",
    )
    parser.add_argument("--judge-model", default=None, help="override judge model (defaults to --model)")
    parser.add_argument("--id", action="append", help="run only these case ids")
    parser.add_argument("--limit", type=int, default=0, help="cap number of cases (0 = all)")
    parser.add_argument("--ledger", default=None, help="write a markdown score ledger to this path")
    parser.add_argument("--stamp", default="unstamped", help="date label for the ledger (pass an ISO date)")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    if args.self_test:
        return self_test(root)

    if args.limit < 0:
        print("--limit must be zero or greater")
        return 2

    try:
        all_cases = load_cases(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"Could not load eval cases: {exc}")
        return 2
    all_case_ids = [case.get("id") for case in all_cases]
    if not all_cases:
        print("No eval cases are available; refusing an empty live run.")
        return 2
    if any(not isinstance(case_id, str) or not case_id for case_id in all_case_ids):
        print("Eval cases contain a missing or malformed id; run --self-test.")
        return 2
    duplicate_case_ids = sorted(
        {case_id for case_id in all_case_ids if all_case_ids.count(case_id) > 1}
    )
    if duplicate_case_ids:
        print("Duplicate eval case ids: " + ", ".join(duplicate_case_ids))
        return 2

    cases = list(all_cases)
    if args.id:
        wanted = set(args.id)
        unknown = sorted(wanted - set(all_case_ids))
        if unknown:
            print("Unknown eval id(s): " + ", ".join(unknown))
            return 2
        cases = [case for case in cases if case.get("id") in wanted]
    if args.limit:
        cases = cases[: args.limit]
    selected_ids = [case["id"] for case in cases]
    selected_case_metadata = build_expected_case_metadata(cases)
    if not selected_ids:
        print("No eval cases were selected; refusing an empty live run.")
        return 2
    release_eligible = selected_ids == all_case_ids

    ledger_path: Path | None = None
    if args.ledger:
        requested_ledger = Path(args.ledger)
        ledger_path = (
            requested_ledger
            if requested_ledger.is_absolute()
            else root / requested_ledger
        ).resolve()
        canonical_ledger = (root / "evals" / "eval-run-ledger.md").resolve()
        if not release_eligible and os.path.normcase(str(ledger_path)) == os.path.normcase(
            str(canonical_ledger)
        ):
            print(
                "Refusing to replace the canonical ledger with a partial run. "
                "Write focused --id/--limit evidence under eval-runs/ instead."
            )
            return 2

    try:
        provider, endpoint, model = resolve_provider(args.provider, args.region, args.model)
        judge_model = args.judge_model or model
        validate_model(args.provider, provider, judge_model)
    except ValueError as exc:
        parser.error(str(exc))

    api_key = os.environ.get(provider.api_key_env)
    if not api_key:
        print(
            f"{provider.api_key_env} not set. Use --self-test for an offline wiring check, "
            "or export a key to run a live scored pass."
        )
        return 2

    rubric = read_text(root / "references" / "eval-rubric.md")
    try:
        validate_sequence_dimension_contract(rubric)
    except ValueError as exc:
        print(f"Could not load eval rubric: {exc}")
        return 2

    scored: list[dict] = []
    for case in cases:
        cid = case.get("id", "?")
        try:
            response = call_api(
                responder_context(root, case),
                case["prompt"],
                model,
                api_key,
                provider,
                endpoint,
            )
            verdict = judge(
                case,
                response,
                judge_model,
                api_key,
                rubric,
                provider,
                endpoint,
            )
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            ProviderResponseError,
        ) as exc:
            print(f"[{cid}] API error: {exc}")
            verdict = {
                "overall_score": 0,
                "pass": False,
                "notes": f"api error: {exc}",
                "assertion_scores": [
                    {"assertion": check, "met": False}
                    for check in expected_judge_checks(case)
                ],
            }
        verdict = normalize_verdict(case, verdict)
        score = verdict["overall_score"]
        passed = verdict["pass"]
        scored.append(
            {
                "id": cid,
                "score": score,
                "pass": passed,
                "sequence": is_sequence_case(case),
                "critical": case.get("critical", False),
                "notes": verdict.get("notes", ""),
                "dimension_scores": verdict.get("dimension_scores", []),
            }
        )
        print(
            f"[{cid}] {'PASS' if passed else 'FAIL'} score={score} :: "
            f"{str(verdict.get('notes', ''))[:70]}"
        )

    report = assess_run(
        scored,
        expected_cases=selected_case_metadata,
        release_eligible=release_eligible,
        total_expected=len(all_cases),
    )
    exit_code = print_assessment(report)
    if ledger_path is not None:
        try:
            write_ledger(
                ledger_path,
                scored,
                model,
                args.stamp,
                args.provider,
                args.region,
                judge_model=judge_model,
                expected_cases=selected_case_metadata,
                total_expected=len(all_cases),
                release_eligible=release_eligible,
            )
        except OSError as exc:
            print(f"Ledger write failed; existing artifact preserved: {exc}")
            return 2
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
