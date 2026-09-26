#!/usr/bin/env python3
"""Check storyboard prompts block by block for the cells a shot table must fill.

Every shot block must state which side the camera is on and the light, and must
carry none of the trap phrases in data/direction-traps.json. The check is a
presence lint: a passing prompt can still be wrong, and the paper render in
references/shot-table.md is still owed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAPS_PATH = ROOT / "data/direction-traps.json"
DEFAULT_TARGETS = ("data/front-page-clips.json",)

SHOT_MARKER = re.compile(
    r"(?:^|(?<=[\s。！？；」』）)]))(?:Shot\s*\d+[.:]|镜头\s*\d+[：:]|ショット\s*\d+[：:]|샷\s*\d+[:：]|Кадр\s*\d+[.:])"
)
CAMERA = re.compile(r"\bcamera\b|机位|カメラ|카메라|камер", re.IGNORECASE)
LIGHT = re.compile(r"\blight\b|灯光|光：|光は|조명|свет", re.IGNORECASE)


def load_traps(path: Path = TRAPS_PATH) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [phrase for phrases in data["traps"].values() for phrase in phrases]


def split_blocks(prompt: str) -> list[str]:
    """Return the shot blocks of a storyboard prompt; text before the first marker is dropped."""
    starts = [m.start() for m in SHOT_MARKER.finditer(prompt)]
    if not starts:
        return []
    starts.append(len(prompt))
    return [prompt[a:b].strip() for a, b in zip(starts, starts[1:])]


def check_prompt(prompt: str, traps: list[str]) -> list[str]:
    """Return one finding per missing cell or trap, empty when the prompt passes."""
    findings: list[str] = []
    blocks = split_blocks(prompt)
    if not blocks:
        return findings
    for index, block in enumerate(blocks, start=1):
        if not CAMERA.search(block):
            findings.append(f"block {index}: no camera side stated")
        if not LIGHT.search(block):
            findings.append(f"block {index}: no light stated")
        for phrase in traps:
            if phrase in block:
                findings.append(f"block {index}: trap phrase {phrase!r}")
    return findings


def prompts_in_json(path: Path) -> list[tuple[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    found: list[tuple[str, str]] = []

    def walk(node, label):
        if isinstance(node, dict):
            name = node.get("id", label)
            for key, value in node.items():
                if key == "prompt" and isinstance(value, str):
                    found.append((str(name), value))
                else:
                    walk(value, name)
        elif isinstance(node, list):
            for item in node:
                walk(item, label)

    walk(data, path.name)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--text", type=Path, help="lint one prompt read from this file instead of the shipped surfaces")
    args = parser.parse_args(argv)
    traps = load_traps()
    total_blocks = 0
    total_findings = 0
    prompts: list[tuple[str, str]] = []
    if args.text:
        prompts.append((str(args.text), args.text.read_text(encoding="utf-8")))
    else:
        for target in DEFAULT_TARGETS:
            prompts.extend(prompts_in_json(ROOT / target))
    for label, prompt in prompts:
        blocks = split_blocks(prompt)
        total_blocks += len(blocks)
        for finding in check_prompt(prompt, traps):
            total_findings += 1
            print(f"{label}: {finding}")
    print(
        f"Shot-table check: {len(prompts)} prompt(s), {total_blocks} shot block(s), {total_findings} finding(s). "
        "Presence only: a camera side and a light per block, no trap phrases; the paper render is still owed."
    )
    return 1 if total_findings else 0


if __name__ == "__main__":
    sys.exit(main())
