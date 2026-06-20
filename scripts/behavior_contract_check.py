#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_SNIPPETS = {
    "SKILL.md": [
        "## Sequence Gate",
        "[skill:seedance-sequence]",
        "[skill:seedance-continuation]",
        "accepted observed state overrides planned state",
        "rejected footage",
        "exact reference tags",
    ],
    "skills/seedance-sequence/SKILL.md": [
        "Plan globally",
        "final outcome",
        "provisional intent cards",
        "Clip 01 final Seedance prompt",
    ],
    "skills/seedance-continuation/SKILL.md": [
        "Required Input Gate",
        "accepted previous clip or accepted final frame",
        "observed_end_state",
        "Do not hide this uncertainty",
    ],
    "references/prompt-compiler.md": [
        "natural-language Seedance prompt",
        "Do not emit internal JSON",
        "Do not replay completed actions",
        "Do not perform reserved later actions",
    ],
    "references/surface-prompt-profiles.md": [
        "Do not hardcode duration",
        "conservative generic profile",
    ],
}


DOMAIN_FILES = [
    "skills/seedance-camera/SKILL.md",
    "skills/seedance-motion/SKILL.md",
    "skills/seedance-characters/SKILL.md",
    "skills/seedance-audio/SKILL.md",
    "skills/seedance-lighting/SKILL.md",
    "skills/seedance-style/SKILL.md",
    "skills/seedance-recipes/SKILL.md",
    "skills/seedance-prompt-short/SKILL.md",
    "skills/seedance-troubleshoot/SKILL.md",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    errors: list[str] = []

    for rel, snippets in REQUIRED_SNIPPETS.items():
        path = root / rel
        if not path.exists():
            errors.append(f"missing {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        low = text.lower()
        for snippet in snippets:
            if snippet.lower() not in low:
                errors.append(f"{rel}: missing behavior phrase `{snippet}`")

    for rel in DOMAIN_FILES:
        path = root / rel
        if not path.exists():
            errors.append(f"missing {rel}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        if "sequence state" not in text or "reserved" not in text or "continuity locks" not in text:
            errors.append(f"{rel}: must read sequence state, continuity locks, and reserved beats when present")

    if errors:
        print("Behavior contract errors:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Behavior contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
