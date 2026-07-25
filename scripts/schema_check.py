#!/usr/bin/env python3
"""Execute the shipped JSON Schemas against the instances they must accept.

The repository ships schemas under ``schemas/`` and example records under
``examples/``. Nothing previously validated one against the other: the other
checkers re-declare required fields in Python, so a schema and its examples
could drift apart silently and both would still pass.

This runs the schemas as schemas. Every file in ``schemas/`` must be declared
in ``validation/schema-instances.json`` with at least one instance, so a new
schema cannot be added without an example that proves what it accepts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:  # pragma: no cover - covered by test_dependency_is_required
    Draft202012Validator = None  # type: ignore[assignment]
    FormatChecker = None  # type: ignore[assignment]

MANIFEST = Path("validation/schema-instances.json")
SCHEMA_DIR = Path("schemas")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """json.loads keeps the last duplicate key; a silent overwrite in a schema
    or fixture would hide the very drift this check exists to catch."""
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate object key: {key!r}")
        seen[key] = value
    return seen


def load_json(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if text.startswith("﻿"):
        raise ValueError("UTF-8 BOM is not permitted")
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def pointer(error: Any) -> str:
    return "/" + "/".join(str(part) for part in error.absolute_path)


def check(root: Path) -> list[str]:
    errors: list[str] = []

    manifest_path = root / MANIFEST
    if not manifest_path.exists():
        return [f"missing {MANIFEST.as_posix()}"]
    try:
        manifest = load_json(manifest_path)
    except ValueError as exc:
        return [f"{MANIFEST.as_posix()}: {exc}"]

    declared = manifest.get("instances")
    if not isinstance(declared, dict):
        return [f"{MANIFEST.as_posix()}: 'instances' must be an object"]

    schema_dir = root / SCHEMA_DIR
    on_disk = {path.name for path in sorted(schema_dir.glob("*.schema.json"))}

    for name in sorted(on_disk - declared.keys()):
        errors.append(
            f"schemas/{name} has no entry in {MANIFEST.as_posix()}; "
            "declare at least one instance it must accept"
        )
    for name in sorted(declared.keys() - on_disk):
        errors.append(f"{MANIFEST.as_posix()} declares schemas/{name}, which does not exist")

    for name in sorted(on_disk & declared.keys()):
        schema_path = schema_dir / name
        try:
            schema = load_json(schema_path)
        except ValueError as exc:
            errors.append(f"schemas/{name}: {exc}")
            continue

        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # jsonschema raises SchemaError
            errors.append(f"schemas/{name}: not a valid Draft 2020-12 schema: {exc}")
            continue

        instances = declared[name]
        if not isinstance(instances, list) or not instances:
            errors.append(f"{MANIFEST.as_posix()}: schemas/{name} must declare a non-empty list")
            continue

        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for relative in instances:
            instance_path = root / relative
            if not instance_path.exists():
                errors.append(f"schemas/{name}: declared instance {relative} does not exist")
                continue
            try:
                instance = load_json(instance_path)
            except ValueError as exc:
                errors.append(f"{relative}: {exc}")
                continue
            for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path)):
                errors.append(f"{relative} against schemas/{name}: {pointer(error)}: {error.message}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if Draft202012Validator is None:
        print(
            "schema check requires jsonschema.\n"
            "  python -m pip install --require-hashes --requirement requirements-validation.lock\n"
            "The lock covers CPython 3.11-3.13 on Linux, macOS, and Windows. On a platform\n"
            "it does not cover, install jsonschema>=4.26 by any means you trust and re-run;\n"
            "this checker needs the library, not that particular lock file.",
            file=sys.stderr,
        )
        return 2

    errors = check(Path(args.repo).resolve())
    if errors:
        print("Schema execution errors:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Schema check passed: every schema executed against its declared instances.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
