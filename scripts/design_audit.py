#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

if __package__:
    from .strict_json import diagnostic_text, read_repo_text, validate_repo_input_path
else:
    from strict_json import diagnostic_text, read_repo_text, validate_repo_input_path


# Live text in a shipped asset must use the monospace stack and nothing else.
# Two syntaxes carry a family: the SVG presentation attribute and the CSS
# `font:` shorthand used inside <style>. Both are collected, because checking
# only one leaves the other free to reintroduce a platform-dependent face.
FONT_FAMILY_ATTR = re.compile(r'font-family\s*=\s*"([^"]*)"')
FONT_SHORTHAND = re.compile(r"font\s*:\s*([^;{}]*)")
MONOSPACE_MARKER = "ui-monospace"


def font_family_findings(rel: str, svg: str) -> list[str]:
    """Every declared family must be the monospace stack.

    Stated as a requirement rather than a denylist: a list of banned serif
    names silently passes `font-family="Arial"` or a bare generic, which is
    exactly the platform-dependent rendering the outlines were adopted to end.
    """
    declarations = FONT_FAMILY_ATTR.findall(svg) + FONT_SHORTHAND.findall(svg)
    if not declarations:
        return []
    findings = []
    for declared in declarations:
        if MONOSPACE_MARKER not in declared:
            findings.append(
                f"{rel} declares a non-monospace font family ({declared.strip()[:60]!r}); "
                "live text must use the monospace stack and display type must be outlined"
            )
    return findings


def png_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


# Transitional ceiling for the existing gallery. Lower with the README refactor.
MAX_README_ASSET_BYTES = 24 * 1024 * 1024
MAX_ASSET_BYTES = 5 * 1024 * 1024
LANGUAGE_PATHS = ("docs/QUICKSTART.md", "docs/QUICKSTART.zh.md", "docs/QUICKSTART.ja.md",
                  "docs/QUICKSTART.ko.md", "docs/QUICKSTART.es.md", "docs/QUICKSTART.ru.md")


def prose_only(text: str) -> str:
    """Supported README subset: skip fenced code and HTML comments."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines, fence = [], None
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return "\n".join(lines)


def anchors(text: str) -> set[str]:
    found, counts = set(), {}
    for line in prose_only(text).splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            heading = re.sub(r"[`*_~]", "", match.group(1)).strip().lower()
            base = re.sub(r"[^\w\- ]", "", heading)
            base = re.sub(r"\s+", "-", base).strip("-")
            n = counts.get(base, 0)
            counts[base] = n + 1
            found.add(base if not n else f"{base}-{n}")
    found.update(re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)', text, re.I))
    return found


class MediaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images, self.links, self.errors = [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img":
            if not (attrs.get("alt") or "").strip():
                self.errors.append("README image needs nonempty alt text")
            if not attrs.get("src"):
                self.errors.append("README image needs a source")
            else:
                self.images.append(attrs["src"])
        if tag in {"source", "img"} and attrs.get("srcset"):
            self.images.extend(part.strip().split()[0] for part in attrs["srcset"].split(",") if part.strip())
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])


def readme_findings(root: Path, text: str, *, budget: int = MAX_README_ASSET_BYTES) -> list[str]:
    root = root.resolve()
    errors, images, links = [], [], []
    prose = prose_only(text)
    parser = MediaParser()
    parser.feed(prose)
    errors.extend(parser.errors)
    images.extend(parser.images)
    links.extend(parser.links)
    for match in re.finditer(r'(!?)\[([^\]\n]*)\]\(([^)\n]+)\)', prose):
        image, label, destination = match.groups()
        destination = destination.strip().strip("<>")
        if image:
            if not label.strip():
                errors.append("README image needs nonempty alt text")
            images.append(destination)
        else:
            links.append(destination)
    for required in LANGUAGE_PATHS:
        if required not in links:
            errors.append(f"README needs the {required} language entry link")
    for section in ("install", "start-here"):
        if section not in anchors(prose):
            errors.append(f"README needs a #{section} destination")
    local_images = set()
    for target in links + images:
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            if target in images:
                errors.append("README images must be repository-local so their size is bounded")
            elif parsed.scheme.lower() not in {"https", "http", "mailto"}:
                errors.append("README link uses an unsupported URL scheme")
            continue
        relative = unquote(parsed.path)
        path = root / (relative or "README.md")
        try:
            validate_repo_input_path(root, path)
            if not path.is_file():
                raise ValueError("not a file")
            parent = root
            for part in path.relative_to(root).parts:
                if part not in {entry.name for entry in parent.iterdir()}:
                    raise ValueError("path case does not match")
                parent /= part
        except (OSError, ValueError) as exc:
            errors.append(f"README target is missing or unsafe: {target}")
            continue
        if target in images:
            local_images.add(path)
            if path.stat().st_size > MAX_ASSET_BYTES:
                errors.append(f"README asset exceeds per-file budget: {relative}")
            if path.suffix.lower() == ".png":
                size = png_dimensions(path)
                if size is None or not all(0 < value <= 8192 for value in size):
                    errors.append(f"README PNG header/dimensions invalid: {relative}")
            elif path.suffix.lower() != ".svg":
                errors.append(f"README asset type is not supported: {relative}")
        if parsed.fragment and path.suffix.lower() == ".md":
            source = text if not relative or relative == "README.md" else read_repo_text(root, path)
            if unquote(parsed.fragment) not in anchors(source):
                errors.append(f"README fragment does not resolve: {target}")
    total = sum(p.stat().st_size for p in local_images)
    if total > budget:
        errors.append(f"README embedded assets exceed budget: {total} > {budget} bytes")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    errors = []
    try:
        text = read_repo_text(root, root / "README.md")
        errors.extend(readme_findings(root, text))
    except (OSError, ValueError):
        errors.append("README.md is missing or unreadable")

    for rel in ["assets/hero-dark.svg", "assets/hero-light.svg", "assets/skill-map.svg"]:
        path = root / rel
        if not path.exists():
            errors.append(f"missing asset: {rel}")
            continue
        svg = path.read_text(encoding="utf-8", errors="ignore")
        if "<svg" not in svg:
            errors.append(f"{rel} is not an SVG")
        if "<title>" not in svg or "<desc>" not in svg:
            errors.append(f"{rel} missing accessible title/desc")
        if re.search(r"<script|href=[\"\']https?://|xlink:href=[\"\']https?://", svg, re.I):
            errors.append(f"{rel} must not include scripts or external resources")
        if "linearGradient" in svg or "feGaussianBlur" in svg:
            errors.append(f"{rel} must follow the editorial standard: no gradients or blur filters")
        # Display type is outlined, so there is no serif stack left to look for
        # - that is the point. What must hold instead: every font family the
        # asset declares is the monospace stack. A denylist of serif names
        # cannot express that, because it passes anything not on the list
        # (font-family="Arial", or a bare generic). So resolve each declaration
        # and require it, rather than guessing at what is forbidden.
        errors.extend(font_family_findings(rel, svg))
        if "<path" not in svg:
            errors.append(f"{rel} has no outlined display type")

    if errors:
        print("Design audit errors:")
        for error in errors:
            print(f"- {diagnostic_text(error)}")
        return 1
    print("Design audit passed: supported README links, alt text, asset headers and budgets checked; visual review remains separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
