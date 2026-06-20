#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


JSON_START = re.compile(r"^\s*\{")
REQUIRED_GOLDEN_SECTIONS = [
    "## Source Brief",
    "## Internal Prompt Specification",
    "## Compiled Natural-Language Prompt",
    "## Lint Result",
    "## Control-Critical Sentences",
]
BLOCKED_MARKERS = ("TO" "DO", "PLACE" "HOLDER")


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


def lint_markdown(path: Path, root: Path) -> list[str]:
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
        elif JSON_START.match(prompt):
            errors.append(f"{rel}: compiled prompt must be natural language, not JSON/YAML")
        if "lint: pass" not in text.lower():
            errors.append(f"{rel}: missing lint: pass result")
        if "why this remains" not in text.lower():
            errors.append(f"{rel}: missing control-critical explanation")

    return errors


def scan(root: Path) -> list[str]:
    errors: list[str] = []
    for base in [root / "examples"]:
        if not base.exists():
            errors.append(f"missing {base.relative_to(root).as_posix()}")
            continue
        for path in base.rglob("*.md"):
            errors.extend(lint_markdown(path, root))
    return errors


def self_test() -> list[str]:
    sample = """
## Source Brief
x
## Internal Prompt Specification
x
## Compiled Natural-Language Prompt
Begin with the accepted final frame and stop at the door.
## Lint Result
lint: pass
## Control-Critical Sentences
why this remains: it preserves the observed opening.
"""
    if JSON_START.match(compiled_prompt(sample)):
        return ["self-test failed: prose prompt detected as JSON"]
    bad = sample.replace("Begin with", "{")
    if not JSON_START.match(compiled_prompt(bad)):
        return ["self-test failed: JSON prompt not detected"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    errors = self_test() if args.self_test else []
    root = Path(args.repo).resolve()
    errors.extend(scan(root))

    if errors:
        print("Prompt lint errors:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Prompt lint passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
