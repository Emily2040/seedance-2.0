"""Strict, precision-preserving JSON loading shared by repository validators."""

from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


MAX_JSON_KEY_DISPLAY_CHARS = 64
MAX_JSON_NESTING_DEPTH = 512
MAX_DIAGNOSTIC_COUNT = 50
MAX_DIAGNOSTIC_CHARS = 1024
MAX_DIAGNOSTIC_TOTAL_CHARS = 16384


def _bounded_key(key: str) -> str:
    if len(key) <= MAX_JSON_KEY_DISPLAY_CHARS:
        return repr(key)
    preview = key[:MAX_JSON_KEY_DISPLAY_CHARS] + "..."
    return f"{preview!r} ({len(key)} chars)"


def safe_diagnostic_text(value: str, limit: int = MAX_DIAGNOSTIC_CHARS) -> str:
    """Escape control characters and stop before an untrusted value can flood output."""

    suffix = "... [diagnostic truncated]"
    budget = max(0, limit - len(suffix))
    rendered: list[str] = []
    rendered_length = 0
    truncated = False
    for character in value:
        codepoint = ord(character)
        if character == "\n":
            fragment = "\\n"
        elif character == "\r":
            fragment = "\\r"
        elif character == "\t":
            fragment = "\\t"
        elif codepoint < 32 or codepoint == 127:
            fragment = f"\\x{codepoint:02x}"
        else:
            fragment = character
        if rendered_length + len(fragment) > budget:
            truncated = True
            break
        rendered.append(fragment)
        rendered_length += len(fragment)
    if truncated:
        rendered.append(suffix)
    return "".join(rendered)


def bound_diagnostics(messages: list[str], omission: str) -> list[str]:
    """Cap diagnostic count, per-message characters, and aggregate characters."""

    bounded: list[str] = []
    marker = safe_diagnostic_text(omission)
    total = 0

    def finish_with_marker() -> None:
        nonlocal total
        while bounded and total + len(marker) > MAX_DIAGNOSTIC_TOTAL_CHARS:
            total -= len(bounded.pop())
        if len(bounded) < MAX_DIAGNOSTIC_COUNT and len(marker) <= MAX_DIAGNOSTIC_TOTAL_CHARS:
            bounded.append(marker)

    for message in messages:
        candidate = safe_diagnostic_text(message)
        if len(bounded) >= MAX_DIAGNOSTIC_COUNT - 1:
            finish_with_marker()
            break
        if total + len(candidate) > MAX_DIAGNOSTIC_TOTAL_CHARS:
            finish_with_marker()
            break
        bounded.append(candidate)
        total += len(candidate)
    return bounded


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate names instead of silently accepting the last value."""

    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate object key: {_bounded_key(key)}")
        seen[key] = value
    return seen


def reject_non_json_number(value: str) -> None:
    raise ValueError(f"non-JSON numeric constant {value!r}")


def _check_nesting_depth(text: str) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_NESTING_DEPTH:
                raise ValueError("JSON nesting exceeds the supported parser depth")
        elif character in "]}":
            depth = max(0, depth - 1)


def loads(text: str) -> Any:
    """Load RFC-compatible JSON without float precision loss."""

    if text.startswith("\ufeff"):
        raise ValueError("UTF-8 BOM is not permitted")
    _check_nesting_depth(text)
    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_json_number,
            parse_float=Decimal,
        )
    except RecursionError:
        raise ValueError("JSON nesting exceeds the supported parser depth") from None
    except (InvalidOperation, OverflowError):
        raise ValueError("JSON number is outside the supported exact range") from None


def load(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8"))


def json_integer(value: object) -> int | float | Decimal | None:
    """Return exact finite JSON integers, including integral decimal tokens."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return value
    if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
        return value
    return None


def is_json_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Decimal):
        return value.is_finite()
    return False
