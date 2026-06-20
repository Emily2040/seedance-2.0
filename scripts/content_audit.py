#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

RISK_PHRASES = {
    "Feb 2026 Status": "stale platform status",
    "API global release was delayed": "stale API status",
    "real-person face uploads paused": "stale likeness status",
    "face uploads paused": "stale likeness status",
    "Blocked as of Feb 15": "stale absolute likeness claim",
    "always refused": "over-absolute policy claim",
    "37% block rate": "unsourced statistic",
    "37% block-rate": "unsourced statistic",
    "in the style of Studio Trigger": "studio-name style request",
    "Studio Ghibli": "studio-name style request",
    "Ghibli-style": "studio-name style request",
    "Ghibli style": "studio-name style request",
    "Spider-Man swings": "named franchise character in active example",
    "rhythm clone": "copyright-sensitive clone wording",
    "performance clone": "copyright-sensitive clone wording",
    "dance performance clone": "copyright-sensitive clone wording",
    "绕过审核": "Chinese filter-bypass wording",
    "绕过安全": "Chinese safety-bypass wording",
    "名人换脸": "Chinese celebrity face-swap wording",
    "复制真人脸": "Chinese real-person cloning wording",
    "обойти фильтр": "Russian filter-bypass wording",
    "обход фильтра": "Russian filter-bypass wording",
    "клонировать лицо": "Russian face-cloning wording",
    "голос знаменитости": "Russian celebrity voice wording",
}

IGNORE_PREFIXES = [
    ".git/",
    ".seedance_backups/",
    "references/migrated/",
]

IGNORE_FILES = {
    "CHANGELOG.md",
}


def should_scan(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if path.name in IGNORE_FILES:
        return False
    if any(rel.startswith(prefix) for prefix in IGNORE_PREFIXES):
        return False
    return path.suffix == ".md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    findings = []
    archived_findings = []

    for path in root.rglob("*"):
        if path.is_file() and should_scan(path, root):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for phrase, reason in RISK_PHRASES.items():
                if phrase in text:
                    findings.append((path.relative_to(root).as_posix(), phrase, reason))

    migrated_root = root / "references" / "migrated"
    if migrated_root.exists():
        for path in migrated_root.rglob("*.md"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for phrase, reason in RISK_PHRASES.items():
                if phrase in text:
                    archived_findings.append((path.relative_to(root).as_posix(), phrase, reason))

    if archived_findings:
        print("Archived migrated warnings:")
        for rel, phrase, reason in archived_findings[:20]:
            print(f"- {rel}: `{phrase}` ({reason})")
        print("Archived findings are warning-only; active guidance must not rely on migrated claims.")
        print()

    if findings:
        print("Content audit findings:")
        for rel, phrase, reason in findings:
            print(f"- {rel}: `{phrase}` ({reason})")
        return 1

    print("Content audit passed: no active stale/risky phrases found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
