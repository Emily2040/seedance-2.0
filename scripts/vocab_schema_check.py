#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

LANGS = ["en", "zh", "ru", "ja", "ko", "es"]
ALLOWED_FUNCTIONS = {
    "Role", "FirstLastFrame", "Camera", "Shot", "Lens", "Lighting", "Motion",
    "VFX", "Audio", "Text", "Editing", "Constraint", "Constraints", "Safety",
}
STRICT_REQUIRED_FUNCTIONS = {"Role", "FirstLastFrame", "Camera", "Audio", "Text", "Editing", "Constraint", "Safety"}
PROTECTED_TERMS = ["Studio Ghibli", "Ghibli", "Spider-Man", "Disney", "Marvel"]


def table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        if "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 3 and cells[0] != "Function":
            rows.append(cells)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require at least 40 rows and the complete production-function set",
    )
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    errors: list[str] = []

    for lang in LANGS:
        path = root / "references" / "vocab" / f"{lang}.md"
        if not path.exists():
            errors.append(f"missing {path.relative_to(root).as_posix()}")
            continue

        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        if not text.startswith("# "):
            errors.append(f"{rel}: missing H1")
        if "Keep reference tags unchanged" not in text and "reference tags unchanged" not in text:
            errors.append(f"{rel}: missing reference-tag preservation note")
        if "| Function |" not in text:
            errors.append(f"{rel}: missing Function vocabulary table")
        if "## Slop Traps" not in text:
            errors.append(f"{rel}: missing Slop Traps section (language-specific empty-quality words)")

        rows = table_rows(text)
        min_rows = 40
        if args.strict and len(rows) < min_rows:
            errors.append(f"{rel}: expected at least {min_rows} rows, found {len(rows)}")

        functions = set()
        for i, row in enumerate(rows, start=1):
            function, term, meaning = row[0], row[1], row[2]
            functions.add(function)
            if function not in ALLOWED_FUNCTIONS:
                errors.append(f"{rel}: row {i} has unsupported function `{function}`")
            if not function or not term or not meaning:
                errors.append(f"{rel}: row {i} has an empty cell")

        if args.strict:
            missing = STRICT_REQUIRED_FUNCTIONS - functions
            if missing:
                errors.append(f"{rel}: missing strict functions " + ", ".join(sorted(missing)))

        for protected in PROTECTED_TERMS:
            if protected in text:
                errors.append(f"{rel}: protected term `{protected}` should not appear in active vocab")

        if not re.search(r"@Image1.*@Video1|@Image1.*@Audio1", text, re.S):
            errors.append(f"{rel}: expected unchanged reference tag examples")

    if errors:
        print("Vocab schema errors:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Vocab schema check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
