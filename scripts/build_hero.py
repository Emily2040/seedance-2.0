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
import hashlib
import os
import sys
from pathlib import Path

# Isolated mode intentionally omits the script directory from ``sys.path``.
# Add only this resolved sibling directory, never an inherited search path.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_masthead_outlines import (
    BUILD_INSTALL_POLICY,
    BUILD_LOCK_PROVENANCE_PATH,
    LOCKED_PYTHON_BUILDERS,
    PINNED_BUILDER_VERSIONS,
    locked_python_builder_versions,
)

if __package__:
    from .strict_json import diagnostic_path, diagnostic_text, load_json, read_repo_text
else:
    from strict_json import diagnostic_path, diagnostic_text, load_json, read_repo_text

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_COMMAND = "python -I -S -B scripts/build_hero.py"

# The display type is vector outlines, not live text. The previous stack
# (Didot, Bodoni MT, Hoefler Text, Baskerville, Palatino Linotype, Georgia)
# resolved to a different face on every platform - Didot only on macOS, a
# Times clone or DejaVu Serif on Linux, Palatino on most Windows installs -
# so the "high-contrast editorial serif" the design system specifies was
# what a minority of readers actually saw. That is the same failure the
# script wordmark was retired for; the stack had it too and outlasted it.
# Outlines render identically everywhere and depend on no installed font.
OUTLINES = ROOT / "assets/masthead-outlines.json"
LOCK = ROOT / BUILD_LOCK_PROVENANCE_PATH

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


def provenance_failure(detail: str) -> SystemExit:
    """Return one stable fail-closed error for all untrusted outline metadata."""
    return SystemExit(
        f"masthead outline provenance validation failed: {detail}; "
        "regenerate with python -I -S -B scripts/build_masthead_outlines.py"
    )


def validated_outline_document() -> dict:
    """Read the outline asset only after binding it to this checkout's build lock.

    The SVG generator is a release writer too: accepting path-shaped metadata,
    a merely plausible policy sentence, or versions that do not match the
    declared shaper would let tampered geometry be laundered into both themes.
    Every provenance field is therefore an exact value, and the digest is
    recomputed from the lock bytes in this checkout.
    """
    try:
        document = load_json(OUTLINES, expected_type=dict, root=ROOT)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise provenance_failure(f"cannot read {OUTLINES}: {exc}") from exc

    provenance = document.get("provenance")
    if not isinstance(provenance, dict):
        raise provenance_failure("provenance must be a JSON object")

    builder_versions = provenance.get("builder_versions")
    if builder_versions != PINNED_BUILDER_VERSIONS:
        raise provenance_failure(
            f"builder_versions must equal {PINNED_BUILDER_VERSIONS!r}"
        )

    build_lock = provenance.get("build_lock")
    if not isinstance(build_lock, dict):
        raise provenance_failure("build_lock must be a JSON object")
    if build_lock.get("path") != BUILD_LOCK_PROVENANCE_PATH:
        raise provenance_failure(
            f"build_lock.path must equal {BUILD_LOCK_PROVENANCE_PATH!r}"
        )
    if build_lock.get("install_policy") != BUILD_INSTALL_POLICY:
        raise provenance_failure("build_lock.install_policy does not match the required policy")

    try:
        lock_bytes = LOCK.read_bytes()
    except OSError as exc:
        raise provenance_failure(f"cannot read build lock {LOCK}: {exc}") from exc
    try:
        locked_versions = locked_python_builder_versions(lock_bytes)
    except SystemExit as exc:
        raise provenance_failure(f"invalid build-lock package pins: {exc}") from exc
    expected_locked_versions = {
        name: PINNED_BUILDER_VERSIONS[name] for name in LOCKED_PYTHON_BUILDERS
    }
    if locked_versions != expected_locked_versions:
        raise provenance_failure(
            "build-lock package pins do not match the required builder versions"
        )

    expected_digest = hashlib.sha256(lock_bytes).hexdigest()
    if build_lock.get("sha256") != expected_digest:
        raise provenance_failure("build_lock.sha256 does not match requirements-masthead.lock")

    glyph_runs = document.get("glyphs")
    if not isinstance(glyph_runs, dict):
        raise provenance_failure("glyphs must be a JSON object")
    return document


def glyphs() -> dict[str, dict]:
    return validated_outline_document()["glyphs"]


def render(theme: str, glyph_runs: dict[str, dict]) -> str:
    c = THEMES[theme]
    g = glyph_runs
    o: list[str] = []
    add = o.append

    def outline(key: str, x: float, y: float, fill: str, anchor: str = "start") -> None:
        """Place an outlined run. `anchor="end"` right-aligns on its advance."""
        run = g[key]
        left = x - run["advance"] if anchor == "end" else x
        add(f'<path transform="translate({left:.2f} {y})" fill="{fill}" d="{run["d"]}"/>')

    # title and desc are the first children of a role="img" svg, which is what
    # assistive technology reads; no aria-labelledby indirection needed.
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">')
    add('<title>Seedance 2.0 Skill OS</title>')
    add('<desc>Editorial masthead: the wordmark Seedance 2.0 Skill OS above the line '
        '"Direct the model, don\'t micro-manage the frame", with a specification strip listing '
        'generation modes, the route-verify-direct-deliver pipeline, and supported reading languages.</desc>')
    add(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')

    # Eyebrow, sitting on the spine. Three words of philosophy set as a field
    # label - not a market category. "AI FILMMAKING" said what every product in
    # the space says; an eyebrow that could open a competitor's page is not an
    # eyebrow, it is filler.
    add(f'<text x="{M}" y="84" font-family="{MONO}" font-size="13" letter-spacing="6.5" '
        f'fill="{c["muted"]}">INTENT BEFORE FRAMES</text>')

    # First hairline. A single registration tick marks the spine.
    add(f'<line x1="{M}" y1="106" x2="{RIGHT}" y2="106" stroke="{c["hairline"]}" stroke-width="1"/>')
    add(f'<line x1="{M}" y1="101" x2="{M}" y2="111" stroke="{c["hairline"]}" stroke-width="1"/>')

    # Wordmark, as outlines. One family at two sizes; the amber falls on the
    # second line only. Scale is the luxury: the first line owns its band of
    # the canvas alone, so nothing shares its vertical zone.
    outline("wordmark", M, 252, c["fg"])
    outline("skill_os", M, 332, c["accent"])

    # Tagline, right-aligned against the opposite margin, seated on the Skill OS
    # band so its second baseline registers with the amber baseline - one shared
    # datum across the width of the page instead of two texts floating apart.
    outline("tagline_1", RIGHT, 298, c["muted"], anchor="end")
    outline("tagline_2", RIGHT, 332, c["muted"], anchor="end")

    # Second hairline, then the specification strip.
    add(f'<line x1="{M}" y1="366" x2="{RIGHT}" y2="366" stroke="{c["hairline"]}" stroke-width="1"/>')

    # Specification fields stay live text: the values carry CJK, which no Latin
    # outline set can supply. They are set in the monospace stack so that every
    # remaining live glyph on the canvas belongs to one family - the only serif
    # here is outlined, so nothing can silently fall back to a system serif.
    col = M
    step = (RIGHT - M) / len(FIELDS)
    for label, value in FIELDS:
        x = round(col)
        add(f'<text x="{x}" y="396" font-family="{MONO}" font-size="10.5" letter-spacing="3.4" '
            f'fill="{c["muted"]}">{label}</text>')
        add(f'<text x="{x}" y="421" font-family="{MONO}" font-size="14" letter-spacing="0.4" '
            f'fill="{c["fg"]}">{value}</text>')
        col += step

    add("</svg>")
    return "\n".join(o) + "\n"


def build(theme: str) -> str:
    """Build one theme only after its outline provenance passes."""
    return render(theme, glyphs())


def targets() -> dict[Path, str]:
    # Validate once and render every target in memory before the first write.
    # This ordering is deliberate: invalid provenance may never partially
    # replace one theme before failing on the other.
    glyph_runs = glyphs()
    return {
        ROOT / f"assets/hero-{theme}.svg": render(theme, glyph_runs)
        for theme in THEMES
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed files match the source")
    args = parser.parse_args(argv)

    try:
        built_targets = targets()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(diagnostic_text(f"Cannot build masthead from repository inputs: {exc}"))
        return 1

    drift: list[str] = []
    for path, content in built_targets.items():
        if args.check:
            try:
                current = (
                    read_repo_text(root=ROOT, path=path)
                    if os.path.lexists(path)
                    else ""
                )
            except ValueError as exc:
                print(
                    diagnostic_text(
                        f"Cannot inspect {diagnostic_path(path.relative_to(ROOT))}: {exc}"
                    )
                )
                return 1
            if current != content:
                drift.append(diagnostic_path(path.relative_to(ROOT)))
        else:
            path.write_text(content, encoding="utf-8")

    if args.check:
        if drift:
            print(f"Masthead is out of date; re-run {PUBLIC_COMMAND}:")
            for name in drift:
                print(diagnostic_text(f"- {name}"))
            return 1
        print("Masthead check passed: committed SVGs match the generator.")
        return 0

    print("Wrote assets/hero-dark.svg and assets/hero-light.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
