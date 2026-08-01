#!/usr/bin/env python3
"""Generate assets/masthead-outlines.json: display type as vector outlines.

The masthead's display type is glyph geometry, not live text. A font stack
resolves to a different face on every platform - the retired stack gave Didot
only on macOS and a default system serif on Linux - so the editorial serif the
design system specifies was what a minority of readers actually saw. Outlines
depend on no installed font and render identically for everyone.

This is a maintainer tool, not part of the validation suite: it needs two
third-party packages that the offline CI gate deliberately does not carry.

    python -m pip install fonttools uharfbuzz
    python scripts/build_masthead_outlines.py            # rewrite the asset
    python scripts/build_masthead_outlines.py --check    # verify it is current

Run it only when the wordmark or tagline copy changes, then re-run
scripts/build_hero.py so the SVGs pick up the new geometry.

The fonts are vendored under assets/fonts/ with their OFL text, so a clean
checkout reproduces the committed geometry offline. Outlines are glyph
geometry rather than font software; the OFL permits both these outlines and
the bundled originals, and attribution travels in the generated file.
"""
from __future__ import annotations

import argparse
import json
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts"
ROMAN = FONT_DIR / "BodoniModa[opsz,wght].ttf"
ITALIC = FONT_DIR / "BodoniModa-Italic[opsz,wght].ttf"
TARGET = ROOT / "assets" / "masthead-outlines.json"

# Optical size tracks the rendered size, clamped to the axis range. That is
# what the axis is for: a didone drawn for 96px has hairlines that vanish at
# 26px, and one drawn for 26px looks clumsy blown up to 128px.
OPSZ_MIN, OPSZ_MAX = 6, 96

SPECS = {
    "wordmark":  {"font": "roman",  "text": "Seedance 2.0",                  "size": 128},
    "skill_os":  {"font": "roman",  "text": "Skill OS",                      "size": 66},
    "tagline_1": {"font": "italic", "text": "Direct the model.",             "size": 26},
    "tagline_2": {"font": "italic", "text": "Don’t micro-manage the frame.", "size": 26},
}


def outline(src: Path, text: str, size: float) -> tuple[str, float]:
    """Shape `text` with HarfBuzz and return one SVG path plus its advance."""
    import uharfbuzz as hb
    from fontTools.misc.transform import Transform
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    opsz = max(OPSZ_MIN, min(OPSZ_MAX, size))
    font = instantiateVariableFont(TTFont(src), {"opsz": opsz, "wght": 400}, inplace=False)

    # HarfBuzz shapes the instantiated instance, not the variable original.
    blob = BytesIO()
    font.save(blob)
    face = hb.Face(blob.getvalue())
    hbfont = hb.Font(face)
    upem = face.upem
    hbfont.scale = (upem, upem)

    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"kern": True, "liga": True})

    glyph_set, order = font.getGlyphSet(), font.getGlyphOrder()
    scale = size / upem
    x = 0.0
    parts: list[str] = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = SVGPathPen(glyph_set, ntos=lambda v: f"{v:.1f}")
        # Font space is y-up, SVG is y-down.
        transform = Transform(scale, 0, 0, -scale, x + pos.x_offset * scale, -pos.y_offset * scale)
        glyph_set[order[info.codepoint]].draw(TransformPen(pen, transform))
        commands = pen.getCommands()
        if commands:
            parts.append(commands)
        x += pos.x_advance * scale
    return " ".join(parts), round(x, 2)


def document() -> dict:
    sources = {"roman": ROMAN, "italic": ITALIC}
    missing = [str(p.relative_to(ROOT)) for p in sources.values() if not p.exists()]
    if missing:
        raise SystemExit(f"missing vendored font(s): {', '.join(missing)}")

    from fontTools.ttLib import TTFont

    names = TTFont(ROMAN)["name"]
    glyphs = {}
    for key, spec in SPECS.items():
        path_d, advance = outline(sources[spec["font"]], spec["text"], spec["size"])
        glyphs[key] = {"text": spec["text"], "size": spec["size"], "advance": advance, "d": path_d}

    return {
        "_comment": (
            "Display type for the masthead, stored as vector outlines rather than live text. "
            "Regenerate with scripts/build_masthead_outlines.py only when the wordmark or "
            "tagline copy changes, then re-run scripts/build_hero.py."
        ),
        "provenance": {
            "font_family": names.getDebugName(1),
            "font_version": names.getDebugName(5),
            "designer": names.getDebugName(9),
            "license": "SIL Open Font License 1.1",
            "license_url": names.getDebugName(14) or "https://scripts.sil.org/OFL",
            "license_text": "assets/fonts/OFL.txt",
            "source": "https://github.com/google/fonts/tree/main/ofl/bodonimoda",
            "vendored": [str(p.relative_to(ROOT)) for p in sources.values()],
            "instances": f"opsz tracks rendered size clamped to {OPSZ_MIN}-{OPSZ_MAX}; wght=400 throughout",
            "shaping": "HarfBuzz with kern and liga features enabled",
            "note": (
                "Outlines are glyph geometry, not font software. The OFL permits both these "
                "outlines and the bundled originals in assets/fonts/; attribution is retained here."
            ),
        },
        "glyphs": glyphs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify the committed asset is current")
    args = parser.parse_args()

    rendered = json.dumps(document(), indent=2, ensure_ascii=False) + "\n"

    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != rendered:
            print(f"{TARGET.relative_to(ROOT)} is out of date; re-run scripts/build_masthead_outlines.py")
            return 1
        print("Masthead outlines check passed.")
        return 0

    TARGET.write_text(rendered, encoding="utf-8")
    print(f"Wrote {TARGET.relative_to(ROOT)} ({len(rendered)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
