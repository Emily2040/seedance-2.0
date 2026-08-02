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
import html
import http.client
import json
import os
import re
import shlex
import stat
import sys
import tempfile
import unicodedata
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Mapping

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-6"
MINIMAX_MODELS = (
    "MiniMax-M3",
    "MiniMax-M2.7",
    "MiniMax-M2.7-highspeed",
    "MiniMax-M2.5",
    "MiniMax-M2.5-highspeed",
    "MiniMax-M2.1",
    "MiniMax-M2.1-highspeed",
    "MiniMax-M2",
)
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
REQUIRED_COMPLETION_FIELDS = (
    "id",
    "type",
    "role",
    "model",
    "content",
    "stop_reason",
    "usage",
)
TRUNCATION_STOP_REASONS = {
    "length",
    "max_output_tokens",
    "max_tokens",
    "model_context_window_exceeded",
}
USAGE_REQUIRED_TOKEN_FIELDS = {"input_tokens", "output_tokens"}
USAGE_NULLABLE_TOKEN_FIELDS = {
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
}
USAGE_STRING_FIELDS = {"service_tier", "inference_geo"}
USAGE_OBJECT_FIELDS = {
    "cache_creation",
    "server_tool_use",
    "output_tokens_details",
}
ANTHROPIC_SERVICE_TIERS = {"standard", "priority", "batch"}
ANTHROPIC_REFUSAL_CATEGORIES = {
    "cyber",
    "bio",
    "frontier_llm",
    "reasoning_extraction",
    "general_harms",
}
ANTHROPIC_SERVER_TOOL_NAMES = {
    "web_search",
    "web_fetch",
    "code_execution",
    "bash_code_execution",
    "text_editor_code_execution",
    "tool_search_tool_regex",
    "tool_search_tool_bm25",
}
SECRET_PATTERNS = (
    re.compile(
        r"(?i)((?:[\"']?authorization[\"']?)\s*[:=]\s*"
        r"(?:[\"']?)bearer\s+)([^\"'\s,;}\]]+)"
    ),
    re.compile(
        r"(?i)((?:[\"']?x-api-key[\"']?)\s*[:=]\s*(?:[\"']?))"
        r"([^\"'\s,;}\]]+)"
    ),
    re.compile(r"(?i)(\bbearer\s+)([^\"'\s,;}\]]+)"),
)

MAX_EVAL_FILE_CHARACTERS = 5_000_000
MAX_CASES = 1_000
MAX_CASE_ID_CHARACTERS = 128
MAX_PROMPT_CHARACTERS = 20_000
MAX_CASE_LIST_ITEMS = 64
MAX_CASE_LIST_ITEM_CHARACTERS = 2_000
MAX_PROVIDER_RESPONSE_BYTES = 1_000_000


@dataclass(frozen=True)
class ProviderConfig:
    api_key_env: str
    default_model: str
    endpoints: Mapping[str, str]
    models: tuple[str, ...] = ()
    auth_header: str = "x-api-key"
    auth_prefix: str = ""
    response_schema: str = "anthropic"


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
        response_schema="minimax",
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
    try:
        value = json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
        _validate_json_strings(value)
    except RecursionError:
        raise ValueError("JSON nesting exceeds the supported depth") from None
    return value


def _safe_exception_detail(
    exc: BaseException,
    api_key: str,
    limit: int = 240,
) -> str:
    """Redact credentials and keep a bounded, single-line transport reason."""
    try:
        detail = str(exc) or type(exc).__name__
    except Exception:
        detail = type(exc).__name__
    if not _is_utf8_encodable(detail):
        detail = detail.encode("utf-8", errors="backslashreplace").decode("utf-8")
    redaction_sentinel = '"<seedance-redacted>"'
    if api_key:
        detail = re.sub(
            re.escape(api_key), redaction_sentinel, detail, flags=re.I
        )
    for pattern in SECRET_PATTERNS:
        detail = pattern.sub(
            lambda match: match.group(1) + redaction_sentinel,
            detail,
        )
    detail = detail.replace(redaction_sentinel, "[REDACTED]")
    detail = re.sub(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]+", " ", detail).strip()
    return (detail or type(exc).__name__)[:limit]


def _transport_failure(
    phase: str,
    exc: BaseException,
    api_key: str,
) -> ProviderResponseError:
    detail = _safe_exception_detail(exc, api_key)
    return ProviderResponseError(
        f"model API transport {phase} failed ({type(exc).__name__}): {detail}"
    )


def _read_api_response(
    request: urllib.request.Request,
    api_key: str,
) -> bytes:
    """Open, enter, read, and close with phase-specific sanitized failures."""
    try:
        manager = urllib.request.urlopen(request, timeout=120)
    except Exception as exc:
        raise _transport_failure("open", exc, api_key) from None
    try:
        response = manager.__enter__()
    except Exception as exc:
        raise _transport_failure("enter", exc, api_key) from None
    try:
        raw_body = response.read(MAX_PROVIDER_RESPONSE_BYTES + 1)
    except Exception as exc:
        try:
            manager.__exit__(type(exc), exc, exc.__traceback__)
        except Exception:
            pass
        raise _transport_failure("read", exc, api_key) from None
    try:
        manager.__exit__(None, None, None)
    except Exception as exc:
        raise _transport_failure("exit", exc, api_key) from None
    if not isinstance(raw_body, bytes):
        raise ProviderResponseError("model API response body must be bytes")
    if len(raw_body) > MAX_PROVIDER_RESPONSE_BYTES:
        raise ProviderResponseError(
            f"model API response exceeded {MAX_PROVIDER_RESPONSE_BYTES} bytes"
        )
    return raw_body


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_cases(root: Path) -> list[dict]:
    data = strict_json_loads(
        _read_repo_text(
            root,
            "evals/evals.json",
            "evals/evals.json",
            limit=MAX_EVAL_FILE_CHARACTERS,
            truncate=False,
        )
    )
    if not isinstance(data, dict):
        raise ValueError("evals.json root must be a JSON object")
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("evals.json 'cases' must be a JSON list")
    if any(not isinstance(case, dict) for case in cases):
        raise ValueError("every eval case must be a JSON object")
    if len(cases) > MAX_CASES:
        raise ValueError(f"evals.json may contain at most {MAX_CASES} cases")
    return cases


def is_sequence_case(case: dict) -> bool:
    return "expected_sequence_relation" in case or case.get("critical") is True


def _case_string_list(case: dict, field: str) -> list[str]:
    """Return a case list only after every item is safe to iterate and hash."""

    value = case.get(field, [])
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list of non-empty UTF-8 strings")
    if any(
        not isinstance(item, str)
        or not item.strip()
        or not _is_utf8_encodable(item)
        or len(item) > MAX_CASE_LIST_ITEM_CHARACTERS
        for item in value
    ):
        raise ValueError(
            f"{field} must contain only non-empty UTF-8 strings of at most "
            f"{MAX_CASE_LIST_ITEM_CHARACTERS} characters"
        )
    if len(value) > MAX_CASE_LIST_ITEMS:
        raise ValueError(f"{field} may contain at most {MAX_CASE_LIST_ITEMS} items")
    return value


def _safe_skill_name(name: str) -> str:
    """Reject path syntax where the case contract expects one skill slug."""

    if len(name) > MAX_CASE_ID_CHARACTERS or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]*", name
    ) or name in {
        ".",
        "..",
    } or not _portable_windows_segment(name):
        raise ValueError(
            "skills_expected_to_activate entries must be portable skill names, not paths"
        )
    return name


_WINDOWS_FORBIDDEN_PATH_CHARACTERS = frozenset('<>:"|?*')
_WINDOWS_RESERVED_STEMS = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"}
    | {f"COM{number}" for number in "123456789"}
    | {f"LPT{number}" for number in "123456789"}
    | {f"COM{number}" for number in "¹²³"}
    | {f"LPT{number}" for number in "¹²³"}
)
_DEFAULT_IGNORABLE_RANGES = (
    (0x034F, 0x034F),
    (0x115F, 0x1160),
    (0x17B4, 0x17B5),
    (0x180B, 0x180F),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFFA0, 0xFFA0),
    (0xFFF0, 0xFFF8),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)


def _safe_repo_character(character: str) -> bool:
    if unicodedata.category(character).startswith("C"):
        return False
    codepoint = ord(character)
    return not any(start <= codepoint <= end for start, end in _DEFAULT_IGNORABLE_RANGES)


def _portable_windows_segment(segment: str) -> bool:
    """Return whether one component has one portable cross-platform spelling."""

    if (
        not segment
        or segment in {".", ".."}
        or segment.endswith((" ", "."))
        or unicodedata.normalize("NFC", segment) != segment
        or any(not _safe_repo_character(character) for character in segment)
        or any(character in _WINDOWS_FORBIDDEN_PATH_CHARACTERS for character in segment)
    ):
        return False
    stem = segment.split(".", 1)[0].rstrip(" ").upper()
    return stem not in _WINDOWS_RESERVED_STEMS


def _portable_repo_parts(relative: str, field: str) -> tuple[str, ...]:
    """Parse a repository path without accepting platform-normalized aliases."""

    if not relative or not _is_utf8_encodable(relative):
        raise ValueError(f"{field} must be a non-empty UTF-8 repository-relative file")
    portable = relative.replace("\\", "/")
    raw_parts = tuple(portable.split("/"))
    posix = PurePosixPath(portable)
    windows = PureWindowsPath(relative)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or bool(windows.root)
        or any(part in {"", ".", ".."} for part in raw_parts)
    ):
        raise ValueError(f"{field} must stay inside the repository")
    if any(not _portable_windows_segment(part) for part in raw_parts):
        raise ValueError(
            f"{field} must use portable path components without aliases"
        )
    return raw_parts


def _exact_declared_path(root: Path, parts: tuple[str, ...], field: str) -> Path:
    """Resolve components by exact stored spelling, even on case-insensitive hosts."""

    cursor = root
    for part in parts:
        try:
            with os.scandir(cursor) as entries:
                exact = next((entry.name for entry in entries if entry.name == part), None)
        except OSError:
            raise ValueError(
                f"{field} must name an existing file inside the repository"
            ) from None
        if exact is None:
            raise ValueError(f"{field} must use the exact checked-in path spelling")
        cursor = cursor / exact
    return cursor


def _resolve_repo_file(root: Path, relative: str, field: str) -> Path:
    """Resolve one declared input to an existing regular file inside ``root``."""

    parts = _portable_repo_parts(relative, field)
    try:
        resolved_root = root.resolve(strict=True)
        resolved = resolved_root.joinpath(*parts).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError):
        raise ValueError(
            f"{field} must name an existing file inside the repository"
        ) from None
    exact = _exact_declared_path(resolved_root, parts, field)
    try:
        resolved = exact.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError):
        raise ValueError(
            f"{field} must name an existing file inside the repository"
        ) from None
    if not resolved.is_file():
        raise ValueError(f"{field} must name a regular file inside the repository")
    return resolved


def _read_repo_text(
    root: Path,
    relative: str,
    field: str,
    limit: int = 12000,
    *,
    truncate: bool = True,
) -> str:
    """Read one stable contained regular file or return a contract error."""

    path = _resolve_repo_file(root, relative, field)
    try:
        with path.open("r", encoding="utf-8") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError(f"{field} must name a regular file inside the repository")
            text = handle.read(limit + 1)
            after = os.fstat(handle.fileno())
        def fingerprint(info: os.stat_result) -> tuple[int, int, int, int]:
            return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if fingerprint(before) != fingerprint(after):
            raise ValueError(f"{field} changed while it was being read")
        current = _resolve_repo_file(root, relative, field)
        current_stat = current.stat()
        if (before.st_dev, before.st_ino) != (
            current_stat.st_dev,
            current_stat.st_ino,
        ):
            raise ValueError(f"{field} changed while it was being read")
        if len(text) <= limit:
            return text
        if not truncate:
            raise ValueError(f"{field} exceeds {limit} characters")
        return text[:limit] + "\n...[truncated]"
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"{field} cannot be read as UTF-8: {exc}") from None


def _state_fixture_path(root: Path, case: dict) -> Path | None:
    if "state_fixture" not in case or case["state_fixture"] is None:
        return None
    fixture = case["state_fixture"]
    if not isinstance(fixture, str):
        raise ValueError("state_fixture must be a non-empty UTF-8 repository-relative file")
    return _resolve_repo_file(root, fixture, "state_fixture")


def _skill_file(root: Path, name: str) -> Path:
    name = _safe_skill_name(name)
    relative = "SKILL.md" if name == "seedance-20" else f"skills/{name}/SKILL.md"
    return _resolve_repo_file(root, relative, f"skill '{name}'")


def expected_judge_checks(case: dict) -> list[str]:
    """Return every case criterion that the judge must score exactly once."""
    checks = list(_case_string_list(case, "assertions"))
    checks.extend(
        f"[required_output_section] {section}"
        for section in _case_string_list(case, "required_output_sections")
    )
    checks.extend(
        f"[forbidden_behavior_absent] {behavior}"
        for behavior in _case_string_list(case, "forbidden_behaviors")
    )
    return checks


def responder_context(root: Path, case: dict) -> str:
    parts = [
        "# Skill: seedance-20 (root router)",
        _read_repo_text(root, "SKILL.md", "skill 'seedance-20'"),
    ]
    for name in _case_string_list(case, "skills_expected_to_activate"):
        if name == "seedance-20":
            continue  # the root router is already included above
        _safe_skill_name(name)
        body = _read_repo_text(
            root,
            f"skills/{name}/SKILL.md",
            f"skill '{name}'",
            limit=8000,
        )
        if body:
            parts.append(f"\n# Sub-skill: {name}\n{body}")
    fixture_path = _state_fixture_path(root, case)
    if fixture_path is not None:
        fixture = case["state_fixture"]
        parts.append(
            f"\n# Project state fixture ({fixture})\n"
            f"{_read_repo_text(root, fixture, 'state_fixture', limit=6000)}"
        )
    return "\n\n".join(parts)


def case_contract_errors(root: Path, case: dict, index: int) -> tuple[str, list[str]]:
    """Validate every case field used before live provider calls."""

    errors: list[str] = []
    raw_id = case.get("id")
    if (
        not isinstance(raw_id, str)
        or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", raw_id)
        or len(raw_id) > MAX_CASE_ID_CHARACTERS
    ):
        label = f"case {index + 1}"
        errors.append(
            f"{label}: id must be a non-empty UTF-8 string using a lowercase "
            f"ASCII slug of at most "
            f"{MAX_CASE_ID_CHARACTERS} characters"
        )
    else:
        label = raw_id

    prompt = case.get("prompt")
    if (
        not isinstance(prompt, str)
        or not prompt.strip()
        or not _is_utf8_encodable(prompt)
        or len(prompt) > MAX_PROMPT_CHARACTERS
    ):
        errors.append(
            f"{label}: prompt must be a non-empty UTF-8 string of at most "
            f"{MAX_PROMPT_CHARACTERS} characters"
        )

    judge_fields: dict[str, list[str]] = {}
    for field in ("assertions", "required_output_sections", "forbidden_behaviors"):
        try:
            judge_fields[field] = _case_string_list(case, field)
        except ValueError as exc:
            errors.append(f"{label}: {exc}")
        else:
            if len(judge_fields[field]) != len(set(judge_fields[field])):
                errors.append(f"{label}: duplicate {field} entry")
    assertions = judge_fields.get("assertions", [])
    if not assertions:
        errors.append(f"{label}: no assertions")
    if len(judge_fields) == 3:
        judge_checks = expected_judge_checks(case)
        if len(judge_checks) != len(set(judge_checks)):
            errors.append(f"{label}: duplicate judge check")

    try:
        skills = _case_string_list(case, "skills_expected_to_activate")
        if len(skills) != len(set(skills)):
            errors.append(f"{label}: duplicate skills_expected_to_activate entry")
        for name in skills:
            _skill_file(root, name)
    except ValueError as exc:
        errors.append(f"{label}: {exc}")

    try:
        _state_fixture_path(root, case)
    except ValueError as exc:
        errors.append(f"{label}: {exc}")

    critical = case.get("critical", False)
    if type(critical) is not bool:
        errors.append(f"{label}: critical must be a boolean when present")
    relation = case.get("expected_sequence_relation")
    if "expected_sequence_relation" in case and (
        not isinstance(relation, str)
        or not relation.strip()
        or not _is_utf8_encodable(relation)
    ):
        errors.append(
            f"{label}: expected_sequence_relation must be a non-empty UTF-8 string"
        )

    return label, errors


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


def _reject_extra_keys(value: dict, allowed: set[str], label: str) -> None:
    extras = sorted(set(value) - allowed)
    if extras:
        raise ProviderResponseError(
            f"{label} contains undocumented fields: {', '.join(extras)}"
        )


def _non_negative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _is_rfc3339(value: object) -> bool:
    if not isinstance(value, str) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
        value,
    ) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.utcoffset() is not None


def _validate_usage(usage: object, provider: ProviderConfig) -> None:
    if not isinstance(usage, dict):
        raise ProviderResponseError("model API response has invalid usage")
    if provider.response_schema == "minimax":
        allowed_fields = USAGE_REQUIRED_TOKEN_FIELDS | USAGE_NULLABLE_TOKEN_FIELDS
    elif provider.response_schema == "anthropic":
        allowed_fields = (
            USAGE_REQUIRED_TOKEN_FIELDS
            | USAGE_NULLABLE_TOKEN_FIELDS
            | USAGE_STRING_FIELDS
            | USAGE_OBJECT_FIELDS
        )
    else:
        raise ProviderResponseError(
            f"unsupported provider response schema: {provider.response_schema!r}"
        )
    _reject_extra_keys(
        usage,
        allowed_fields,
        "model API response usage",
    )
    for field in USAGE_REQUIRED_TOKEN_FIELDS:
        if field not in usage or not _non_negative_int(usage[field]):
            raise ProviderResponseError(
                f"model API response has invalid usage.{field}"
            )
    for field in USAGE_NULLABLE_TOKEN_FIELDS:
        if (
            field in usage
            and (
                (usage[field] is None and provider.response_schema != "anthropic")
                or (
                    usage[field] is not None
                    and not _non_negative_int(usage[field])
                )
            )
        ):
            raise ProviderResponseError(
                f"model API response has invalid usage.{field}"
            )
    if provider.response_schema == "minimax":
        return
    for field in USAGE_STRING_FIELDS:
        if field not in usage or usage[field] is None:
            continue
        if not isinstance(usage[field], str) or not usage[field].strip():
            raise ProviderResponseError(
                f"model API response has invalid usage.{field}"
            )
    if (
        "service_tier" in usage
        and usage["service_tier"] is not None
        and usage["service_tier"] not in ANTHROPIC_SERVICE_TIERS
    ):
        raise ProviderResponseError(
            "model API response has invalid usage.service_tier"
        )
    if "cache_creation" in usage:
        cache = usage["cache_creation"]
        if cache is None:
            pass
        elif not isinstance(cache, dict):
            raise ProviderResponseError(
                "model API response has invalid usage.cache_creation"
            )
        else:
            required = {
                "ephemeral_5m_input_tokens",
                "ephemeral_1h_input_tokens",
            }
            _reject_extra_keys(cache, required, "usage.cache_creation")
            if set(cache) != required or any(
                not _non_negative_int(value) for value in cache.values()
            ):
                raise ProviderResponseError(
                    "model API response has invalid usage.cache_creation"
                )
    if "server_tool_use" in usage:
        tools = usage["server_tool_use"]
        if tools is None:
            pass
        elif not isinstance(tools, dict):
            raise ProviderResponseError(
                "model API response has invalid usage.server_tool_use"
            )
        else:
            allowed = {"web_search_requests", "web_fetch_requests"}
            _reject_extra_keys(tools, allowed, "usage.server_tool_use")
            if set(tools) != allowed or any(
                not _non_negative_int(value) for value in tools.values()
            ):
                raise ProviderResponseError(
                    "model API response has invalid usage.server_tool_use"
                )
    if "output_tokens_details" in usage:
        details = usage["output_tokens_details"]
        if details is None:
            return
        if not isinstance(details, dict):
            raise ProviderResponseError(
                "model API response has invalid usage.output_tokens_details"
            )
        _reject_extra_keys(
            details,
            {"thinking_tokens"},
            "usage.output_tokens_details",
        )
        if (
            set(details) != {"thinking_tokens"}
            or not _non_negative_int(details["thinking_tokens"])
            or details["thinking_tokens"] > usage["output_tokens"]
        ):
            raise ProviderResponseError(
                "model API response has invalid usage.output_tokens_details"
            )


def _validate_citation(citation: object, block_index: int, index: int) -> None:
    label = f"content block {block_index} citation {index}"
    if not isinstance(citation, dict):
        raise ProviderResponseError(f"{label} must be an object")
    citation_type = citation.get("type")
    if not isinstance(citation_type, str):
        raise ProviderResponseError(f"{label} has an invalid type")
    common = {"type", "cited_text"}
    schemas = {
        "char_location": common
        | {
            "document_index",
            "document_title",
            "start_char_index",
            "end_char_index",
            "file_id",
        },
        "page_location": common
        | {
            "document_index",
            "document_title",
            "start_page_number",
            "end_page_number",
            "file_id",
        },
        "content_block_location": common
        | {
            "document_index",
            "document_title",
            "start_block_index",
            "end_block_index",
            "file_id",
        },
        "web_search_result_location": common
        | {"encrypted_index", "title", "url"},
        "search_result_location": common
        | {
            "source",
            "title",
            "search_result_index",
            "start_block_index",
            "end_block_index",
        },
    }
    allowed = schemas.get(citation_type)
    if allowed is None:
        raise ProviderResponseError(f"{label} has unsupported type: {citation_type!r}")
    optional_by_type = {
        "char_location": {"document_title", "file_id"},
        "page_location": {"document_title", "file_id"},
        "content_block_location": {"document_title", "file_id"},
        "web_search_result_location": {"title"},
        "search_result_location": {"title"},
    }
    optional = optional_by_type[citation_type]
    required = allowed - optional
    missing = sorted(required - set(citation))
    if missing:
        raise ProviderResponseError(f"{label} is missing fields: {', '.join(missing)}")
    _reject_extra_keys(citation, allowed, label)
    string_fields = required - {
        "document_index",
        "start_char_index",
        "end_char_index",
        "start_page_number",
        "end_page_number",
        "start_block_index",
        "end_block_index",
        "search_result_index",
    }
    if any(not isinstance(citation[field], str) for field in string_fields):
        raise ProviderResponseError(f"{label} has an invalid string field")
    for field in optional:
        if (
            field in citation
            and citation[field] is not None
            and not isinstance(citation[field], str)
        ):
            raise ProviderResponseError(f"{label} has an invalid {field}")
    integer_fields = required - string_fields
    if any(not _non_negative_int(citation[field]) for field in integer_fields):
        raise ProviderResponseError(f"{label} has an invalid index")
    for start, end in (
        ("start_char_index", "end_char_index"),
        ("start_page_number", "end_page_number"),
        ("start_block_index", "end_block_index"),
    ):
        if start in citation and citation[end] <= citation[start]:
            raise ProviderResponseError(f"{label} has an invalid range")
    if "start_page_number" in citation and citation["start_page_number"] < 1:
        raise ProviderResponseError(f"{label} has an invalid page range")


def _validate_tool_caller(caller: object, block_index: int) -> None:
    label = f"model API response tool_use block {block_index} caller"
    if not isinstance(caller, dict):
        raise ProviderResponseError(f"{label} must be an object")
    caller_type = caller.get("type")
    if not isinstance(caller_type, str):
        raise ProviderResponseError(f"{label} has an invalid type")
    if caller_type == "direct":
        allowed = {"type"}
    elif caller_type in {
        "code_execution_20250825",
        "code_execution_20260120",
    }:
        allowed = {"type", "tool_id"}
        if not isinstance(caller.get("tool_id"), str) or not caller["tool_id"]:
            raise ProviderResponseError(f"{label} has an invalid tool_id")
    else:
        raise ProviderResponseError(f"{label} has unsupported type: {caller_type!r}")
    _reject_extra_keys(caller, allowed, label)


def _validate_content_blocks(
    provider: ProviderConfig,
    model: str,
    content: object,
) -> str:
    if not isinstance(content, list):
        raise ProviderResponseError("model API response has invalid content blocks")
    text_parts: list[str] = []
    for index, block in enumerate(content):
        if not isinstance(block, dict):
            raise ProviderResponseError(
                f"model API response content block {index} must be an object"
            )
        block_type = block.get("type")
        if block_type == "text":
            allowed = {"type", "text"}
            if provider.response_schema == "anthropic":
                allowed.add("citations")
            _reject_extra_keys(block, allowed, f"content text block {index}")
            block_text = block.get("text")
            if not isinstance(block_text, str):
                raise ProviderResponseError(
                    f"model API response text block {index} has invalid text"
                )
            if "citations" in block:
                citations = block["citations"]
                if citations is None:
                    citations = []
                elif not isinstance(citations, list):
                    raise ProviderResponseError(
                        f"model API response text block {index} has invalid citations"
                    )
                for citation_index, citation in enumerate(citations):
                    _validate_citation(citation, index, citation_index)
            text_parts.append(block_text)
            continue
        if block_type == "thinking":
            _reject_extra_keys(
                block,
                {"type", "thinking", "signature"},
                f"content thinking block {index}",
            )
            thinking = block.get("thinking")
            signature = block.get("signature")
            if (
                not isinstance(thinking, str)
                or not thinking.strip()
                or not isinstance(signature, str)
                or not signature.strip()
            ):
                raise ProviderResponseError(
                    f"model API response thinking block {index} is malformed"
                )
            if provider.response_schema == "minimax" and model != "MiniMax-M3":
                continue
            raise ProviderResponseError(
                f"model API response thinking block {index} was not requested"
            )
        if block_type == "redacted_thinking":
            _reject_extra_keys(
                block,
                {"type", "data"},
                f"content redacted_thinking block {index}",
            )
            if not isinstance(block.get("data"), str) or not block["data"]:
                raise ProviderResponseError(
                    f"model API response redacted_thinking block {index} is malformed"
                )
            raise ProviderResponseError(
                f"model API response redacted_thinking block {index} was not requested"
            )
        if block_type == "tool_use":
            _reject_extra_keys(
                block,
                {"type", "id", "name", "input", "caller"},
                f"content tool_use block {index}",
            )
            if (
                not isinstance(block.get("id"), str)
                or not block["id"]
                or not isinstance(block.get("name"), str)
                or not block["name"]
                or not isinstance(block.get("input"), dict)
            ):
                raise ProviderResponseError(
                    f"model API response tool_use block {index} is malformed"
                )
            if "caller" in block:
                _validate_tool_caller(block["caller"], index)
            raise ProviderResponseError(
                f"model API response tool_use block {index} was not requested"
            )
        if block_type == "server_tool_use":
            _reject_extra_keys(
                block,
                {"type", "id", "name", "input", "caller"},
                f"content server_tool_use block {index}",
            )
            if (
                not isinstance(block.get("id"), str)
                or not block["id"]
                or not isinstance(block.get("name"), str)
                or not block["name"]
                or not isinstance(block.get("input"), dict)
            ):
                raise ProviderResponseError(
                    f"model API response server_tool_use block {index} is malformed"
                )
            if block["name"] not in ANTHROPIC_SERVER_TOOL_NAMES:
                raise ProviderResponseError(
                    f"model API response server_tool_use block {index} has "
                    f"unsupported name: {block['name']!r}"
                )
            if "caller" in block:
                _validate_tool_caller(block["caller"], index)
            raise ProviderResponseError(
                f"model API response server_tool_use block {index} was not requested"
            )
        raise ProviderResponseError(
            f"model API response content block {index} has unsupported type: "
            f"{block_type!r}"
        )
    text = "".join(text_parts)
    if not text.strip():
        raise ProviderResponseError("model API response contained no text")
    return text


def _validate_provider_legacy_fields(
    provider: ProviderConfig,
    body: dict,
) -> None:
    common = set(REQUIRED_COMPLETION_FIELDS)
    if provider.response_schema == "anthropic":
        _reject_extra_keys(
            body,
            common | {"stop_sequence", "container", "stop_details"},
            "Anthropic response",
        )
        if "base_resp" in body:
            raise ProviderResponseError("Anthropic response contains foreign base_resp")
        if "stop_sequence" not in body:
            raise ProviderResponseError(
                "Anthropic response is missing completion field: stop_sequence"
            )
        stop_sequence = body["stop_sequence"]
        if stop_sequence is not None and not isinstance(stop_sequence, str):
            raise ProviderResponseError("Anthropic response has invalid stop_sequence")
        if "container" in body and body["container"] is not None:
            container = body["container"]
            if not isinstance(container, dict):
                raise ProviderResponseError("Anthropic response has invalid container")
            _reject_extra_keys(container, {"id", "expires_at"}, "Anthropic container")
            if (
                set(container) != {"id", "expires_at"}
                or not isinstance(container["id"], str)
                or not container["id"]
                or not _is_rfc3339(container["expires_at"])
            ):
                raise ProviderResponseError("Anthropic response has invalid container")
        if "stop_details" in body and body["stop_details"] is not None:
            stop_details = body["stop_details"]
            if not isinstance(stop_details, dict):
                raise ProviderResponseError("Anthropic response has invalid stop_details")
            _reject_extra_keys(
                stop_details,
                {"type", "category", "explanation"},
                "Anthropic stop_details",
            )
            if stop_details.get("type") != "refusal":
                raise ProviderResponseError(
                    "Anthropic response has invalid stop_details"
                )
            category = stop_details.get("category")
            explanation = stop_details.get("explanation")
            if (
                category is not None
                and (
                    not isinstance(category, str)
                    or category not in ANTHROPIC_REFUSAL_CATEGORIES
                )
            ) or (
                explanation is not None and not isinstance(explanation, str)
            ):
                raise ProviderResponseError(
                    "Anthropic response has invalid stop_details"
                )
        return
    if provider.response_schema != "minimax":
        raise ProviderResponseError(
            f"unsupported provider response schema: {provider.response_schema!r}"
        )
    _reject_extra_keys(
        body,
        common | {"stop_sequence", "base_resp"},
        "MiniMax response",
    )
    if "stop_sequence" in body and body["stop_sequence"] is not None:
        raise ProviderResponseError("MiniMax response has invalid stop_sequence")
    if "base_resp" not in body:
        return
    base_response = body["base_resp"]
    if not isinstance(base_response, dict):
        raise ProviderResponseError("MiniMax response has invalid base_resp")
    _reject_extra_keys(
        base_response,
        {"status_code", "status_msg"},
        "MiniMax base_resp",
    )
    if (
        type(base_response.get("status_code")) is not int
        or not isinstance(base_response.get("status_msg"), str)
    ):
        raise ProviderResponseError("MiniMax response has invalid base_resp")
    status_message = base_response["status_msg"].strip().casefold()
    if base_response["status_code"] != 0 or status_message not in {"", "success"}:
        raise ProviderResponseError(
            "MiniMax response reports an error: "
            f"status_code={base_response['status_code']!r}, "
            f"status_msg={base_response['status_msg']!r}"
        )


def _call_api_unredacted(
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
        "stream": False,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(endpoint, data=payload, method="POST")
    req.add_header(provider.auth_header, provider.auth_prefix + api_key)
    req.add_header("anthropic-version", ANTHROPIC_VERSION)
    req.add_header("content-type", "application/json")
    raw_body = _read_api_response(req, api_key)
    try:
        body = strict_json_loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProviderResponseError("model API returned invalid JSON") from exc
    if not isinstance(body, dict):
        raise ProviderResponseError("model API response must be a JSON object")

    _validate_provider_legacy_fields(provider, body)

    missing = [field for field in REQUIRED_COMPLETION_FIELDS if field not in body]
    if missing:
        raise ProviderResponseError(
            "model API response is missing completion fields: " + ", ".join(missing)
        )
    if not isinstance(body["id"], str) or not body["id"].strip():
        raise ProviderResponseError("model API response has an invalid id")
    if body["type"] != "message":
        raise ProviderResponseError("model API response type must be message")
    if body["role"] != "assistant":
        raise ProviderResponseError("model API response role must be assistant")
    if body["model"] != model:
        raise ProviderResponseError(
            "model API response model does not match the requested model: "
            f"expected {model!r}, got {body['model']!r}"
        )

    stop_reason = body["stop_reason"]
    if not isinstance(stop_reason, str) or not stop_reason.strip():
        raise ProviderResponseError(
            "model API response requires a non-null stop_reason"
        )
    normalized_reason = stop_reason.strip().casefold()
    context_limited = "context" in normalized_reason and any(
        marker in normalized_reason for marker in ("exceed", "limit", "window")
    )
    token_limited = "token" in normalized_reason and any(
        marker in normalized_reason for marker in ("max", "limit", "length")
    )
    if (
        normalized_reason in TRUNCATION_STOP_REASONS
        or context_limited
        or token_limited
    ):
        raise ProviderResponseError(
            f"model response stopped with {stop_reason!r}; refusing truncated evidence"
        )
    if stop_reason != "end_turn":
        raise ProviderResponseError(
            "model response did not complete normally: "
            f"stop_reason={stop_reason!r}"
        )
    if provider.response_schema == "anthropic" and body["stop_sequence"] is not None:
        raise ProviderResponseError(
            "Anthropic end_turn response must have a null stop_sequence"
        )
    if provider.response_schema == "anthropic" and body.get("stop_details") is not None:
        raise ProviderResponseError(
            "Anthropic end_turn response must have null stop_details"
        )

    _validate_usage(body["usage"], provider)
    return _validate_content_blocks(provider, model, body["content"])


def call_api(
    system: str,
    user: str,
    model: str,
    api_key: str,
    provider: ProviderConfig,
    endpoint: str,
    max_tokens: int = 1500,
) -> str:
    """Call a provider without allowing credentials into public error text."""
    try:
        return _call_api_unredacted(
            system,
            user,
            model,
            api_key,
            provider,
            endpoint,
            max_tokens,
        )
    except ProviderResponseError as exc:
        raise ProviderResponseError(
            _safe_exception_detail(exc, api_key, limit=500)
        ) from None


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
    try:
        rubric = _read_repo_text(
            root,
            "references/eval-rubric.md",
            "references/eval-rubric.md",
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print("eval_run self-test FAILED:")
        print(f"- invalid references/eval-rubric.md: {exc}")
        return 1
    if "0 to 3" not in rubric or "0-4" not in rubric:
        errors.append("eval-rubric.md missing the 0-3 and 0-4 scales")
    try:
        validate_sequence_dimension_contract(rubric)
    except ValueError as exc:
        errors.append(str(exc))
    seq = 0
    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        cid, contract_errors = case_contract_errors(root, case, index)
        errors.extend(contract_errors)
        raw_id = case.get("id")
        if (
            isinstance(raw_id, str)
            and re.fullmatch(r"[a-z0-9][a-z0-9_-]*", raw_id)
            and len(raw_id) <= MAX_CASE_ID_CHARACTERS
        ):
            if cid in seen_ids:
                errors.append(f"{cid}: duplicate case id")
            seen_ids.add(cid)
        if not contract_errors:
            try:
                context = responder_context(root, case)
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(f"{cid}: repository input cannot be read: {exc}")
                context = ""
            if not context.strip():
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


def _safe_markdown_code(value: str, limit: int = 80) -> str:
    """Sanitize values interpolated into Markdown code spans or fences."""
    return _safe_ledger_text(value, limit=limit).replace("`", "'")


def _safe_markdown_text(value: str, limit: int = 80) -> str:
    """Make untrusted text inert when it is rendered outside a code span."""
    sanitized = html.escape(_safe_ledger_text(value, limit=limit), quote=False)
    return re.sub(r"([\\`*_\[\]()#!~>])", r"\\\1", sanitized)


COMMAND_VALUE_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:/+-]{0,199}\Z")


def _regeneration_argv(
    provider_name: str,
    region: str,
    model: str,
    judge_model: str,
) -> list[str] | None:
    values = (provider_name, region, model, judge_model)
    if any(
        not _is_utf8_encodable(value) or COMMAND_VALUE_RE.fullmatch(value) is None
        for value in values
    ):
        return None
    return [
        "python",
        "scripts/eval_run.py",
        "--provider",
        provider_name,
        "--region",
        region,
        "--model",
        model,
        "--judge-model",
        judge_model,
        "--ledger",
        "evals/eval-run-ledger.md",
    ]


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _regeneration_command_lines(argv: list[str] | None) -> list[str]:
    if argv is None:
        return [
            "Regeneration commands omitted because CLI metadata contains unsafe shell or ",
            "Markdown characters; re-enter those values manually.",
        ]
    return [
        "Regenerate from a POSIX shell:",
        "",
        "```sh",
        shlex.join(argv),
        "```",
        "",
        "Regenerate from PowerShell:",
        "",
        "```powershell",
        "& " + " ".join(_powershell_quote(value) for value in argv),
        "```",
    ]


def _render_ledger_row(index: int, row: object) -> str:
    """Render even malformed evidence rows without preserving a stale ledger."""
    if not isinstance(row, dict):
        return (
            f"| [invalid row {index + 1}] | invalid | invalid | invalid | INVALID | "
            "result is not an object |"
        )

    raw_id = row.get("id")
    case_id = (
        _safe_markdown_text(raw_id)
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
                f"{_safe_markdown_text(dimension)}={dimension_score}"
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
        _safe_markdown_text(raw_note)
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
    safe_stamp = _safe_markdown_text(stamp, limit=120)
    safe_model = _safe_markdown_code(model, limit=200)
    safe_judge_model = _safe_markdown_code(judge_model, limit=200)
    safe_provider_name = _safe_markdown_code(provider_name, limit=120)
    safe_region = _safe_markdown_code(region, limit=120)
    command_lines = _regeneration_command_lines(
        _regeneration_argv(provider_name, region, model, judge_model)
    )
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
        "CI validators check shape; this checks output quality.",
        "",
    ]
    lines.extend(command_lines)
    lines.append("")
    if report["integrity_errors"]:
        lines.extend(["## Integrity errors", ""])
        lines.extend(
            f"- {_safe_markdown_text(error, limit=500)}"
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
    contract_errors: list[str] = []
    for index, case in enumerate(all_cases):
        _, case_errors = case_contract_errors(root, case, index)
        contract_errors.extend(case_errors)
    if contract_errors:
        print("Could not load eval cases: case contract validation failed")
        for error in contract_errors[:40]:
            print(f"- {error}")
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

    try:
        rubric = _read_repo_text(
            root,
            "references/eval-rubric.md",
            "references/eval-rubric.md",
        )
        validate_sequence_dimension_contract(rubric)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Could not load eval rubric: {exc}")
        return 2

    contexts: list[str] = []
    try:
        for case in cases:
            contexts.append(responder_context(root, case))
    except (OSError, UnicodeError, ValueError) as exc:
        cid = case.get("id", "?")
        print(f"[{cid}] repository input error: {exc}")
        return 2

    scored: list[dict] = []
    for case, context in zip(cases, contexts, strict=True):
        cid = case.get("id", "?")
        try:
            response = call_api(
                context,
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
