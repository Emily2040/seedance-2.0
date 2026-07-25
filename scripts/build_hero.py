#!/usr/bin/env python3
"""Generate the theme-aware masthead pair from one geometry.

hero-dark.svg and hero-light.svg differ only by palette. Maintaining them as
two hand-edited files invites exactly one bug: a change landing in one theme
and not the other, which nobody notices because most readers only ever see one.

Emitting both from a single source makes that impossible, and ``--check``
proves the committed files still match the source so the SVGs cannot be edited
out from under this script.

Composition follows the Call Sheet philosophy in
references/frontend-design-system.md: one left spine, two hairlines, the
wordmark given the middle of the canvas, and a specification strip of
label-over-value fields. No viewfinder chrome, no gradients, no second hue.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SERIF = (
    "Didot, &apos;Bodoni MT&apos;, &apos;Hoefler Text&apos;, Baskerville, "
    "&apos;Palatino Linotype&apos;, Georgia, serif"
)
MONO = "ui-monospace, SFMono-Regular, &apos;SF Mono&apos;, Menlo, Consolas, monospace"

# Canvas: 1200x470. Margin 76 gives the wordmark room without the strip
# crowding the lower edge at GitHub's rendered width.
W, H = 1200, 470
M = 76
RIGHT = W - M

THEMES = {
    "dark": {
        "bg": "#100E0A",
        "fg": "#EDE6D6",
        "muted": "#9A917D",
        "hairline": "#2E2A22",
        "accent": "#E2A75E",
    },
    "light": {
        "bg": "#F7F3EA",
        "fg": "#1C1914",
        "muted": "#6F6757",
        "hairline": "#D8D0BE",
        "accent": "#A86F24",
    },
}

# Timeless only. The design system forbids baking counts or version numbers
# into vector assets because they go stale in place.
FIELDS = [
    ("MODES", "T2V · I2V · V2V · R2V · FLF2V"),
    ("PIPELINE", "Route · Verify · Direct · Deliver"),
    ("READS", "EN · 中文 · 日本語 · 한국어 · ES · RU"),
]


def build(theme: str) -> str:
    c = THEMES[theme]
    o: list[str] = []
    add = o.append

    # title and desc are the first children of a role="img" svg, which is what
    # assistive technology reads; no aria-labelledby indirection needed.
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">')
    add('<title>Seedance 2.0 Skill OS</title>')
    add('<desc>Editorial masthead: the wordmark Seedance 2.0 Skill OS above the line '
        '"Direct the model, don\'t micro-manage the frame", with a specification strip listing '
        'generation modes, the route-verify-direct-deliver pipeline, and supported reading languages.</desc>')
    add(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')

    # Eyebrow, sitting on the spine.
    add(f'<text x="{M}" y="86" font-family="{MONO}" font-size="13" letter-spacing="6.5" '
        f'fill="{c["muted"]}">INTENT-FIRST AI FILMMAKING</text>')

    # First hairline. A single registration tick marks the spine.
    add(f'<line x1="{M}" y1="108" x2="{RIGHT}" y2="108" stroke="{c["hairline"]}" stroke-width="1"/>')
    add(f'<line x1="{M}" y1="103" x2="{M}" y2="113" stroke="{c["hairline"]}" stroke-width="1"/>')

    # Wordmark. One family, two sizes; the amber falls on the second line only.
    # A calligraphic face was tried here and dropped: no script font ships on
    # Linux or most Windows installs, so it silently degraded to plain serif and
    # the "single flourish" was invisible to most readers. A design that only
    # exists on the author's machine is not a design.
    add(f'<text x="{M}" y="243" font-family="{SERIF}" font-size="104" fill="{c["fg"]}">Seedance 2.0</text>')
    add(f'<text x="{M}" y="313" font-family="{SERIF}" font-size="62" fill="{c["accent"]}">Skill OS</text>')

    # Tagline, right-aligned against the opposite margin so the eye returns
    # across the wordmark rather than stacking beneath it. Two sentences,
    # matching the README verbatim; a trailing em dash broke badly here.
    add(f'<text x="{RIGHT}" y="240" text-anchor="end" font-family="{SERIF}" font-size="25" '
        f'font-style="italic" fill="{c["muted"]}">Direct the model.</text>')
    add(f'<text x="{RIGHT}" y="274" text-anchor="end" font-family="{SERIF}" font-size="25" '
        f'font-style="italic" fill="{c["muted"]}">Don&apos;t micro-manage the frame.</text>')

    # Second hairline, then the specification strip.
    add(f'<line x1="{M}" y1="358" x2="{RIGHT}" y2="358" stroke="{c["hairline"]}" stroke-width="1"/>')

    col = M
    step = (RIGHT - M) / len(FIELDS)
    for label, value in FIELDS:
        x = round(col)
        add(f'<text x="{x}" y="389" font-family="{MONO}" font-size="10.5" letter-spacing="3.4" '
            f'fill="{c["muted"]}">{label}</text>')
        add(f'<text x="{x}" y="414" font-family="{SERIF}" font-size="17" fill="{c["fg"]}">{value}</text>')
        col += step

    add("</svg>")
    return "\n".join(o) + "\n"


def targets() -> dict[Path, str]:
    return {ROOT / f"assets/hero-{theme}.svg": build(theme) for theme in THEMES}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed files match the source")
    args = parser.parse_args()

    drift: list[str] = []
    for path, content in targets().items():
        if args.check:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != content:
                drift.append(path.relative_to(ROOT).as_posix())
        else:
            path.write_text(content, encoding="utf-8")

    if args.check:
        if drift:
            print("Masthead is out of date; re-run scripts/build_hero.py:")
            for name in drift:
                print(f"- {name}")
            return 1
        print("Masthead check passed: committed SVGs match the generator.")
        return 0

    print("Wrote assets/hero-dark.svg and assets/hero-light.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
