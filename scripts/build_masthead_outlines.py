#!/usr/bin/env python3
"""Generate assets/masthead-outlines.json: display type as vector outlines.

The masthead's display type is glyph geometry, not live text. A font stack
resolves to a different face on every platform - the retired stack gave Didot
only on macOS and a default system serif on Linux - so the editorial serif the
design system specifies was what a minority of readers actually saw. Outlines
depend on no installed font and render identically for everyone.

This is a maintainer tool, not part of the installed skill runtime. Its two
third-party packages are isolated in a hash-pinned build lock. The installer
always force-reinstalls them, so a same-version package already present in the
environment cannot bypass wheel-hash verification.

    python scripts/build_masthead_outlines.py             # verified install + rewrite
    python scripts/build_masthead_outlines.py --install-build-deps  # prepare an offline check
    python scripts/build_masthead_outlines.py --check     # verify it is current

Run it only when the wordmark or tagline copy changes, then re-run
scripts/build_hero.py so the SVGs pick up the new geometry.

The fonts are vendored under assets/fonts/ with their OFL text, so a clean
checkout reproduces the committed geometry offline. Outlines are glyph
geometry rather than font software; the OFL permits both these outlines and
the bundled originals, and attribution travels in the generated file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements-masthead.lock"
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

PINNED_BUILDER_VERSIONS = {
    "fonttools": "4.63.0",
    "uharfbuzz": "0.55.0",
    "harfbuzz": "14.2.1",
}

BUILD_LOCK_PROVENANCE_PATH = "requirements-masthead.lock"
BUILD_INSTALL_POLICY = (
    "generator writes only after pip --force-reinstall --require-hashes; "
    "preinstalled distributions are not reused"
)
LOCKED_PYTHON_BUILDERS = ("fonttools", "uharfbuzz")


def pinned_install_argv(python: str | Path | None = None) -> list[str]:
    """Return the forced, hash-verified install command with an absolute lock path."""
    return [
        str(python or sys.executable),
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        "--require-hashes",
        "--requirement",
        str(LOCK),
    ]


def shell_command(argv: list[str]) -> str:
    """Render an argv for the host shell without losing paths that contain spaces."""
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def recovery_command() -> str:
    """Return a cwd-independent command that installs the pinned build toolchain."""
    return shell_command([sys.executable, str(Path(__file__).resolve()), "--install-build-deps"])


def install_pinned_builder_dependencies() -> None:
    """Force-install locked wheels; never accept an already-satisfied distribution."""
    require_lock_matches_pinned_versions()
    subprocess.run(pinned_install_argv(), check=True, cwd=ROOT)


def build_lock_sha256() -> str:
    """Bind generated provenance to the exact requirements lock bytes."""
    return hashlib.sha256(LOCK.read_bytes()).hexdigest()


def repo_relative_posix(path: Path) -> str:
    """Return a repository-relative path with stable JSON/documentation separators."""
    return path.relative_to(ROOT).as_posix()


def pinned_builder_versions() -> dict[str, str]:
    """Return the toolchain versions committed in requirements-masthead.lock."""
    return dict(PINNED_BUILDER_VERSIONS)


def locked_python_builder_versions(lock_bytes: bytes | None = None) -> dict[str, str]:
    """Extract the two top-level Python pins from the exact lock bytes."""
    try:
        text = (LOCK.read_bytes() if lock_bytes is None else lock_bytes).decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise SystemExit(f"cannot read masthead build lock {LOCK}: {exc}") from exc

    versions: dict[str, str] = {}
    for package in LOCKED_PYTHON_BUILDERS:
        prefix = f"{package}=="
        matches = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line.startswith(prefix):
                value = line[len(prefix):].split(maxsplit=1)[0].rstrip("\\")
                if value:
                    matches.append(value)
        if len(matches) != 1:
            raise SystemExit(
                f"masthead build lock must declare {package} exactly once; found {len(matches)}"
            )
        versions[package] = matches[0]
    return versions


def require_lock_matches_pinned_versions(lock_bytes: bytes | None = None) -> dict[str, str]:
    """Refuse a lock whose package pins disagree with the shaper contract."""
    locked = locked_python_builder_versions(lock_bytes)
    expected = {name: PINNED_BUILDER_VERSIONS[name] for name in LOCKED_PYTHON_BUILDERS}
    if locked != expected:
        raise SystemExit(
            f"masthead build lock version mismatch (expected {expected!r}; found {locked!r})"
        )
    return locked


def installed_builder_versions() -> dict[str, str]:
    """Read versions from the libraries that actually shape the outlines."""
    try:
        import fontTools
        import uharfbuzz as hb
    except ImportError as exc:
        raise SystemExit(
            "masthead builder dependencies are missing; run:\n"
            f"  {recovery_command()}\n"
            f"Resolved build lock: {LOCK}"
        ) from exc
    return {
        "fonttools": fontTools.__version__,
        "uharfbuzz": hb.__version__,
        "harfbuzz": hb.version_string(),
    }


def require_pinned_builder_versions() -> dict[str, str]:
    """Refuse to emit geometry from an unrecorded shaping toolchain."""
    actual = installed_builder_versions()
    if actual != PINNED_BUILDER_VERSIONS:
        expected = ", ".join(
            f"{name}={version}" for name, version in PINNED_BUILDER_VERSIONS.items()
        )
        observed = ", ".join(f"{name}={version}" for name, version in actual.items())
        raise SystemExit(
            f"masthead builder version mismatch; run `{recovery_command()}` "
            f"(expected {expected}; found {observed})"
        )
    return actual


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
    require_lock_matches_pinned_versions()
    builder_versions = require_pinned_builder_versions()
    sources = {"roman": ROMAN, "italic": ITALIC}
    missing = [repo_relative_posix(p) for p in sources.values() if not p.exists()]
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
            "vendored": [repo_relative_posix(p) for p in sources.values()],
            "instances": f"opsz tracks rendered size clamped to {OPSZ_MIN}-{OPSZ_MAX}; wght=400 throughout",
            "shaping": "HarfBuzz with kern and liga features enabled",
            "builder_versions": builder_versions,
            "build_lock": {
                "path": BUILD_LOCK_PROVENANCE_PATH,
                "sha256": build_lock_sha256(),
                "install_policy": BUILD_INSTALL_POLICY,
            },
            "note": (
                "Outlines are glyph geometry, not font software. The OFL permits both these "
                "outlines and the bundled originals in assets/fonts/; attribution is retained here."
            ),
        },
        "glyphs": glyphs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify the committed asset is current")
    parser.add_argument(
        "--install-build-deps",
        action="store_true",
        help="force-install the hash-locked build toolchain and exit",
    )
    args = parser.parse_args(argv)

    if args.install_build_deps:
        if args.check:
            parser.error("--install-build-deps and --check are separate steps")
        install_pinned_builder_dependencies()
        print(f"Installed masthead builder from {repo_relative_posix(LOCK)} with wheel hashes enforced.")
        return 0

    # Writing provenance is a release operation: always replace even an
    # apparently matching installation from the locked wheel set first.
    # Read-only --check remains offline after the explicit preparation step.
    if not args.check:
        install_pinned_builder_dependencies()

    rendered = json.dumps(document(), indent=2, ensure_ascii=False) + "\n"

    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != rendered:
            print(f"{repo_relative_posix(TARGET)} is out of date; re-run scripts/build_masthead_outlines.py")
            return 1
        print("Masthead outlines check passed.")
        return 0

    TARGET.write_text(rendered, encoding="utf-8")
    print(f"Wrote {repo_relative_posix(TARGET)} ({len(rendered)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
