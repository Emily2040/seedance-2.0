#!/usr/bin/env python3
"""Lint documented prompt structure and a bounded set of format anti-patterns.

This linter deliberately does not score semantic creativity or predict generation
quality. It checks whether golden examples keep their documented sections and
whether the compiled prompt is bare natural-language prose rather than a
serialized payload.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


REQUIRED_GOLDEN_SECTIONS = [
    "## Source Brief",
    "## Internal Prompt Specification",
    "## Compiled Natural-Language Prompt",
    "## Lint Result",
    "## Control-Critical Sentences",
]
BLOCKED_MARKERS = ("TO" "DO", "PLACE" "HOLDER")
FENCE_OPEN = re.compile(
    r"^[ ]{0,3}(?P<marker>`{3,}|~{3,})[ \t]*(?P<info>[^\r\n]*)$"
)
YAML_MAPPING_LINE = re.compile(
    r"^[ \t]*(?:-[ \t]+)?[A-Za-z_][A-Za-z0-9_-]*"
    r"(?:[ \t]+[A-Za-z0-9_-]+)*[ \t]*:[ \t]*(?:.*)$"
)
YAML_SEQUENCE_LINE = re.compile(r"^[ \t]*-[ \t]+\S.*$")
YAML_BLOCK_VALUE = re.compile(r":[ \t]*[>|][+-]?[ \t]*(?:#.*)?$")
YAML_FLOW_VALUE = re.compile(r":[ \t]*[\[{].*[\]}][ \t]*(?:#.*)?$")
YAML_WRAPPER_LINE = re.compile(
    r"^[ \t]*(?:prompt|compiled[-_ ]prompt|negative[-_ ]prompt|parameters?|"
    r"settings|metadata|input|output)[ \t]*:",
    re.IGNORECASE,
)
SELF_DECLARED_PASS = re.compile(
    r"^[ \t]*(?:[-*+][ \t]+)?(?:status[ \t]*:[ \t]*)?"
    r"(?:\*\*|__|`)?lint[ \t]*:[ \t]*pass(?:\*\*|__|`)?"
    r"[ \t]*(?:[.!]|[#;(\-][^\r\n]*)?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
BOUNDARY = (
    "Boundary: checks documented prompt format and anti-patterns; "
    "it does not assess semantic creativity or generation quality."
)


@dataclass(frozen=True)
class FencedBlock:
    label: str
    body: str
    closed: bool


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def compiled_prompt(text: str) -> str:
    marker = "## Compiled Natural-Language Prompt"
    if marker not in text:
        return ""
    tail = text.split(marker, 1)[1]
    for next_marker in ["\n## Lint Result", "\n## Control-Critical Sentences"]:
        if next_marker in tail:
            tail = tail.split(next_marker, 1)[0]
    return tail.strip()


def normalized_fence_label(info: str) -> str:
    """Return the first Markdown info-string token in a common normalized form."""
    if not info.strip():
        return ""
    token = info.strip().split(maxsplit=1)[0]
    return token.strip("{}").lstrip(".").lower()


def fenced_blocks(text: str) -> list[FencedBlock]:
    """Extract line-oriented backtick and tilde fences without executing content."""
    lines = text.splitlines()
    blocks: list[FencedBlock] = []
    index = 0
    while index < len(lines):
        opened = FENCE_OPEN.fullmatch(lines[index])
        if not opened:
            index += 1
            continue

        marker = opened.group("marker")
        marker_char = marker[0]
        minimum_close_length = len(marker)
        label = normalized_fence_label(opened.group("info"))
        body_start = index + 1
        close_index: int | None = None
        cursor = body_start
        while cursor < len(lines):
            closing = lines[cursor].strip()
            if (
                closing
                and set(closing) == {marker_char}
                and len(closing) >= minimum_close_length
            ):
                close_index = cursor
                break
            cursor += 1

        if close_index is None:
            blocks.append(FencedBlock(label, "\n".join(lines[body_start:]).strip(), False))
            break

        blocks.append(
            FencedBlock(label, "\n".join(lines[body_start:close_index]).strip(), True)
        )
        index = close_index + 1
    return blocks


def json_structure_reason(text: str) -> str | None:
    """Classify a whole object/array candidate with the standard-library parser."""
    candidate = text.lstrip("\ufeff \t\r\n")
    if not candidate or candidate[0] not in "[{":
        return None
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, RecursionError):
        if candidate[0] == "{":
            return "malformed JSON-like structured data"
        remainder = candidate[1:].lstrip()
        array_value_start = (
            not remainder
            or remainder[0] in '[{"-0123456789]'
            or remainder.startswith(("true", "false", "null"))
        )
        if array_value_start:
            return "malformed JSON-like structured data"
        # Prompt prose can legitimately begin with a reference label such as
        # ``[Video 1]``. Do not treat every leading square bracket as JSON.
        return None
    if isinstance(parsed, (dict, list)):
        return "structured JSON"
    return None


def yaml_structure_reason(text: str) -> str | None:
    """Detect clear YAML shapes conservatively, without a YAML dependency.

    A colon in ordinary prose is not enough. The detector requires a YAML
    document marker, a block-scalar value, or repeated mapping/sequence lines.
    """
    significant = [line for line in text.splitlines() if line.strip()]
    if not significant:
        return None
    if significant[0].strip() == "---" or significant[0].lstrip().startswith("%YAML "):
        return "YAML-like structured data"
    if any(
        YAML_BLOCK_VALUE.search(line) or YAML_FLOW_VALUE.search(line)
        for line in significant
    ):
        return "YAML-like structured data"
    if len(significant) == 1 and YAML_WRAPPER_LINE.match(significant[0]):
        return "YAML-like structured data"

    mapping_count = sum(bool(YAML_MAPPING_LINE.fullmatch(line)) for line in significant)
    sequence_count = sum(bool(YAML_SEQUENCE_LINE.fullmatch(line)) for line in significant)
    if mapping_count >= 2 or sequence_count >= 2 or mapping_count + sequence_count >= 2:
        return "YAML-like structured data"
    return None


def bare_structure_reason(text: str) -> str | None:
    whole_reason = json_structure_reason(text) or yaml_structure_reason(text)
    if whole_reason:
        return whole_reason
    for line in text.splitlines():
        line_reason = json_structure_reason(line)
        if line_reason:
            return line_reason
    return None


def structured_prompt_reason(prompt: str, *, strict: bool = False) -> str | None:
    """Return a bounded format violation, or ``None`` for natural-language prose."""
    blocks = fenced_blocks(prompt)
    for block in blocks:
        if block.label == "json":
            if not block.closed:
                return "malformed JSON code fence"
            try:
                json.loads(block.body)
            except (json.JSONDecodeError, RecursionError):
                return "malformed JSON in a labeled code fence"
            return "structured JSON in a labeled code fence"

        if block.label in {"yaml", "yml"}:
            if not block.closed:
                return "malformed YAML code fence"
            return "structured YAML-like data in a labeled code fence"

        nested_reason = bare_structure_reason(block.body)
        if nested_reason:
            return f"{nested_reason} in a code fence"

    if strict and blocks:
        return "code fence wrapper; strict mode requires bare natural-language prose"

    return bare_structure_reason(prompt)


def lint_markdown(path: Path, root: Path, *, strict: bool = False) -> list[str]:
    rel = path.relative_to(root).as_posix()
    text = read_text(path)
    errors: list[str] = []

    if any(marker in text for marker in BLOCKED_MARKERS):
        errors.append(f"{rel}: contains blocked draft marker")

    if "golden-prompts" in rel:
        for section in REQUIRED_GOLDEN_SECTIONS:
            if section not in text:
                errors.append(f"{rel}: missing {section}")
        prompt = compiled_prompt(text)
        if not prompt:
            errors.append(f"{rel}: missing compiled natural-language prompt")
        else:
            reason = structured_prompt_reason(prompt, strict=strict)
            if reason:
                errors.append(
                    f"{rel}: compiled prompt must be natural language, not {reason}"
                )
        if strict and SELF_DECLARED_PASS.search(text):
            errors.append(
                f"{rel}: self-declared `lint: pass` is not computed evidence; "
                "run this linter for the result"
            )
        if "why this remains" not in text.lower():
            errors.append(f"{rel}: missing control-critical explanation")

    return errors


def scan(root: Path, *, strict: bool = False) -> list[str]:
    errors: list[str] = []
    for base in [root / "examples"]:
        if not base.exists():
            errors.append(f"missing {base.relative_to(root).as_posix()}")
            continue
        for path in base.rglob("*.md"):
            errors.extend(lint_markdown(path, root, strict=strict))
    return errors


def self_test() -> list[str]:
    cases = [
        (
            "ordinary prose",
            "Beginning: hold the accepted frame. Then: stop at the door.",
            False,
            False,
        ),
        ("JSON object", '{"prompt": "stop at the door"}', False, True),
        ("JSON array", '[{"prompt": "stop at the door"}]', False, True),
        ("fenced JSON", "```json\n{\"prompt\": \"x\"}\n```", False, True),
        ("YAML mapping", "prompt: stop at door\ncamera: locked", False, True),
        ("fenced prose default", "```text\nStop at the door.\n```", False, False),
        ("fenced prose strict", "```text\nStop at the door.\n```", True, True),
    ]
    errors: list[str] = []
    for name, prompt, strict, expected_violation in cases:
        detected = structured_prompt_reason(prompt, strict=strict) is not None
        if detected != expected_violation:
            errors.append(
                f"self-test failed: {name} expected violation={expected_violation}, "
                f"got {detected}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Lint golden prompt document structure and serialized-format anti-patterns. "
            "This does not score creativity or generation quality."
        )
    )
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "require bare compiled prose and reject self-declared `lint: pass` claims; "
            "default mode permits prose-only code fences for compatibility"
        ),
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    errors = self_test() if args.self_test else []
    root = Path(args.repo).resolve()
    errors.extend(scan(root, strict=args.strict))

    if errors:
        print("Prompt structure lint errors:")
        for error in errors:
            print(f"- {error}")
        print(BOUNDARY)
        return 1
    print("Prompt structure lint passed.")
    print(BOUNDARY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
