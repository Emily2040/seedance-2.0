#!/usr/bin/env python3
"""Scan shipped prompts for moderation cue words.

Platform classifiers react to words, not intent. This lint applies the cue lists
in ``data/moderation-cues.json`` to the prompt surfaces this repository ships
(fenced and block-quoted prompts in the example and gallery Markdown, and the
prompt fields of the front-page clip data) so a prompt that would be refused
before rendering cannot be published as an example. A hit is a review flag for
the pre-screen in ``references/moderation-prescreen.md``; it is not a verdict
about any platform, and the lists are field-observed, not published rules.

Exit status: 0 by default (report only); ``--fail-on-high`` makes any
high-severity finding (or three stacked medium classes in one prompt) exit 1.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUES_PATH = ROOT / "data" / "moderation-cues.json"
DEFAULT_TARGETS = (
    "README.md",
    "data/front-page-clips.json",
    "references/performance-example-cards.md",
    "references/product-example-cards.md",
    "references/continuity-example-cards.md",
    "references/examples-by-mode.md",
    "references/prompt-examples.md",
    "references/directing-engine-genre-library.md",
    "skills/seedance-examples-zh/SKILL.md",
    "skills/seedance-examples-ja/SKILL.md",
    "skills/seedance-examples-ko/SKILL.md",
)
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
QUOTE = re.compile(r"(?m)^> ?(.*)$")
STACK_THRESHOLD = 3


@dataclass(frozen=True)
class Finding:
    source: str
    prompt_index: int
    cue_class: str
    severity: str
    matches: tuple[str, ...]


def load_cues(path: Path = CUES_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pattern(cue: str, language: str) -> re.Pattern[str]:
    """Latin cues match whole words; Cyrillic cues match word-initial stems
    (Russian inflects), so `кровав` covers `кровавый`; CJK cues match as
    written. Nothing matches inside an unrelated Latin word such as "stable"."""
    escaped = re.escape(cue)
    if language == "en":
        return re.compile(r"(?<![A-Za-z])" + escaped + r"(?![A-Za-z])", re.I)
    if language == "ru":
        return re.compile(r"(?<![А-Яа-яЁё])" + escaped, re.I)
    return re.compile(escaped)


def compile_cues(cues: dict) -> dict[str, tuple[str, list[re.Pattern[str]]]]:
    compiled: dict[str, tuple[str, list[re.Pattern[str]]]] = {}
    for name, spec in cues["classes"].items():
        patterns = [
            _pattern(cue, language)
            for language, words in spec["cues"].items()
            for cue in words
        ]
        compiled[name] = (spec["severity"], patterns)
    return compiled


def scan_text(text: str, compiled: dict[str, tuple[str, list[re.Pattern[str]]]]) -> dict[str, tuple[str, list[str]]]:
    hits: dict[str, tuple[str, list[str]]] = {}
    for name, (severity, patterns) in compiled.items():
        found = sorted({m.group(0) for p in patterns for m in p.finditer(text)})
        if found:
            hits[name] = (severity, found)
    return hits


def prompts_in_markdown(text: str) -> list[str]:
    prompts = [block.strip() for block in FENCE.findall(text)]
    without_fences = FENCE.sub("", text)
    quote: list[str] = []
    for line in without_fences.splitlines():
        match = QUOTE.match(line)
        if match:
            quote.append(match.group(1))
        elif quote:
            prompts.append(" ".join(quote).strip())
            quote = []
    if quote:
        prompts.append(" ".join(quote).strip())
    return [p for p in prompts if p]


def prompts_in_json(text: str) -> list[str]:
    data = json.loads(text)
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "prompt" and isinstance(value, str):
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return found


def effective_severity(name: str, severity: str, hits: dict[str, tuple[str, list[str]]]) -> str:
    """A minor together with any other class, or three stacked medium classes, counts as high."""
    if severity == "high":
        return "high"
    if name == "minor" and len(hits) >= 2:
        return "high"
    medium = [n for n, (s, _) in hits.items() if s == "medium"]
    if len(medium) >= STACK_THRESHOLD:
        return "high"
    return severity


def findings_for(path: Path, compiled) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    prompts = prompts_in_json(text) if path.suffix == ".json" else prompts_in_markdown(text)
    rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
    findings: list[Finding] = []
    for index, prompt in enumerate(prompts, start=1):
        hits = scan_text(prompt, compiled)
        for name, (severity, matches) in hits.items():
            findings.append(Finding(rel, index, name, effective_severity(name, severity, hits), tuple(matches)))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="files to scan (default: the shipped prompt surfaces)")
    parser.add_argument("--fail-on-high", action="store_true", help="exit 1 on any high-severity finding (default: report only)")
    args = parser.parse_args(argv)
    compiled = compile_cues(load_cues())
    targets = [Path(p) if Path(p).is_absolute() else ROOT / p for p in args.paths] or [ROOT / t for t in DEFAULT_TARGETS]
    findings: list[Finding] = []
    for target in targets:
        if target.exists():
            findings.extend(findings_for(target, compiled))
    high = [f for f in findings if f.severity == "high"]
    for finding in findings:
        print(f"{finding.severity:6} {finding.source} prompt {finding.prompt_index}: {finding.cue_class} -> {', '.join(finding.matches)}")
    print(
        f"Moderation pre-screen: {len(findings)} finding(s), {len(high)} high. "
        "A finding is a review flag from field-observed cue lists, not a platform verdict."
    )
    return 1 if (args.fail_on_high and high) else 0


if __name__ == "__main__":
    sys.exit(main())
