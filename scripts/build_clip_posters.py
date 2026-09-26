#!/usr/bin/env python3
"""Generate the front-page clip slates from ``data/front-page-clips.json``.

Each slate stands in for one clip in the README gallery until the maintainer
renders that clip on Seedance 2.0. The slates follow the editorial design
system: warm ink background, hairline frame, live monospace text (the stack
``design_audit.py`` requires), one amber mark, no gradients, no external
resources. ``--check`` verifies that the committed SVGs match this generator so
the data file and the assets cannot drift apart.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "front-page-clips.json"
OUTPUT_DIR = ROOT / "assets" / "clips"

W, H = 1600, 900
INK, FG, MUTED, HAIRLINE, AMBER = "#100E0A", "#EDE6D6", "#9A917D", "#2E2A22", "#E2A75E"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
LANGUAGE_NAMES = {"en": "English", "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ru": "Russian", "es": "Spanish"}


def load_clips(path: Path = DATA_PATH) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    clips = data["clips"]
    if not isinstance(clips, list) or not clips:
        raise ValueError("front-page-clips.json must list at least one clip")
    return clips


def render(clip: dict, total: int) -> str:
    number = int(clip["number"])
    label = " · ".join([
        f"CLIP {number:02d}",
        LANGUAGE_NAMES.get(clip["language"], clip["language"]).upper(),
        f"{int(clip['duration_seconds'])} S",
        clip["aspect"],
        clip["shape"].upper(),
        "UNRENDERED SLATE" if clip.get("status") != "rendered" else "RENDERED",
    ])
    title = escape(clip["title"])
    lines = [escape(line) for line in clip.get("poster_lines", [])][:2]
    desc = escape(
        f"Slate for clip {number:02d} in {LANGUAGE_NAMES.get(clip['language'], clip['language'])}: "
        + " ".join(clip.get("poster_lines", []))
        + " The exact prompt is published beneath the slate; the clip is rendered by the maintainer on Seedance 2.0."
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">',
        f"<title id=\"t\">Clip {number:02d} slate: {title}</title>",
        f'<desc id="d">{desc}</desc>',
        f'<rect width="{W}" height="{H}" fill="{INK}"/>',
        f'<rect x="40.5" y="40.5" width="{W - 81}" height="{H - 81}" fill="none" stroke="{HAIRLINE}" stroke-width="1"/>',
        f'<text x="88" y="118" font-family="{MONO}" font-size="26" letter-spacing="2" fill="{MUTED}">{escape(label)}</text>',
        f'<rect x="88" y="140" width="72" height="3" fill="{AMBER}"/>',
        f'<text x="88" y="470" font-family="{MONO}" font-size="84" fill="{FG}">{title}</text>',
    ]
    y = 560
    for line in lines:
        parts.append(f'<text x="90" y="{y}" font-family="{MONO}" font-size="34" fill="{FG}">{line}</text>')
        y += 52
    parts.append(f'<line x1="88" y1="{H - 132}" x2="{W - 88}" y2="{H - 132}" stroke="{HAIRLINE}" stroke-width="1"/>')
    parts.append(
        f'<text x="88" y="{H - 84}" font-family="{MONO}" font-size="24" fill="{MUTED}">'
        "seedance-20 · prompt beneath this slate · not rendered yet</text>"
    )
    parts.append(
        f'<text x="{W - 88}" y="{H - 84}" text-anchor="end" font-family="{MONO}" font-size="24" fill="{MUTED}">'
        f"{number:02d} / {total:02d}</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def expected_files(clips: list[dict]) -> dict[Path, str]:
    total = len(clips)
    return {OUTPUT_DIR / f"{clip['id']}.svg": render(clip, total) for clip in clips}


def check(clips: list[dict]) -> list[str]:
    problems = []
    for path, content in expected_files(clips).items():
        rel = path.relative_to(ROOT).as_posix()
        if not path.exists():
            problems.append(f"missing {rel}")
        elif path.read_text(encoding="utf-8") != content:
            problems.append(f"{rel} does not match the generator")
    committed = {p for p in OUTPUT_DIR.glob("*.svg")} if OUTPUT_DIR.exists() else set()
    for stray in sorted(committed - set(expected_files(clips))):
        problems.append(f"{stray.relative_to(ROOT).as_posix()} has no clip in the data file")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed slates match the data file")
    args = parser.parse_args(argv)
    clips = load_clips()
    if args.check:
        problems = check(clips)
        if problems:
            print("Clip slate check failed:")
            for problem in problems:
                print(f"- {problem}")
            return 1
        print(f"Clip slate check passed: {len(clips)} slates match data/front-page-clips.json.")
        return 0
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, content in expected_files(clips).items():
        path.write_text(content, encoding="utf-8")
    print(f"Wrote {len(clips)} slates to {OUTPUT_DIR.relative_to(ROOT).as_posix()}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
