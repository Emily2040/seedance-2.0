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
from urllib.parse import unquote

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry
except ImportError:  # pragma: no cover - covered by test_dependency_is_required
    Draft202012Validator = None  # type: ignore[assignment]
    FormatChecker = None  # type: ignore[assignment]
    Registry = None  # type: ignore[assignment,misc]

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


SINGLE_SUBSCHEMA_KEYWORDS = (
    "additionalProperties",
    "contains",
    "contentSchema",
    "else",
    "if",
    "items",
    "not",
    "propertyNames",
    "then",
    "unevaluatedItems",
    "unevaluatedProperties",
)
ARRAY_SUBSCHEMA_KEYWORDS = ("allOf", "anyOf", "oneOf", "prefixItems")
MAP_SUBSCHEMA_KEYWORDS = (
    "$defs",
    "definitions",
    "dependentSchemas",
    "patternProperties",
    "properties",
)
REFERENCE_KEYWORDS = ("$ref", "$dynamicRef")


def _local_pointer_target(
    root: Any,
    reference: str,
    root_path: str = "$",
    resource_boundaries: dict[int, tuple[Any, str]] | None = None,
) -> tuple[Any, str, Any, str] | None:
    """Resolve a pointer and retain the nearest schema-resource boundary crossed."""
    if reference in {"", "#"}:
        return root, root_path, root, root_path
    if not reference.startswith("#"):
        return None
    fragment = unquote(reference[1:])
    if not fragment.startswith("/"):
        # Plain-name anchors are reached through normal schema-keyword traversal.
        return None

    current = root
    path = root_path
    resource_root = root
    resource_path = root_path
    for raw_token in fragment[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list):
            try:
                if not token.isdecimal():
                    return None
                current = current[int(token)]
            except IndexError:
                return None
        else:
            return None
        path += f"/{token}"
        if resource_boundaries is not None:
            boundary = resource_boundaries.get(id(current))
            if boundary is not None:
                resource_root, resource_path = boundary
    return current, path, resource_root, resource_path


def reference_audit(value: Any, path: str = "$") -> tuple[list[str], list[str]]:
    """Audit active references while ignoring unactivated literal data.

    JSON Schema keywords such as ``const``, ``enum``, ``default``, and
    ``examples`` contain JSON values, not subschemas. Walking every nested
    object therefore misclassifies a literal key named ``$ref``. This walker
    follows only Draft 2020-12 schema-valued keywords. A local JSON Pointer is
    resolved from its current schema-resource root (including nested ``$id``
    resources), so a subschema stored under an opaque container cannot hide an
    active external reference when explicitly used. Every resolved local target
    is also required to be an object or boolean that passes the Draft 2020-12
    metaschema; otherwise an omitted optional branch could hide an invalid
    runtime schema.
    """
    findings: list[str] = []
    invalid_targets: list[str] = []
    visited: set[tuple[int, int]] = set()
    indexed: set[int] = set()
    resource_boundaries: dict[int, tuple[Any, str]] = {}
    anchor_targets: dict[
        tuple[int, str],
        tuple[Any, str, Any, str] | None,
    ] = {}

    def index_schema_resources(
        schema: Any,
        schema_path: str,
        resource_root: Any,
        resource_path: str,
    ) -> None:
        """Index resource and anchor boundaries only in schema-valued positions."""
        if isinstance(schema, bool) or not isinstance(schema, dict):
            return
        identity = id(schema)
        if identity in indexed:
            return
        indexed.add(identity)
        if isinstance(schema.get("$id"), str):
            resource_boundaries[identity] = (schema, schema_path)
            resource_root = schema
            resource_path = schema_path
        for keyword in ("$anchor", "$dynamicAnchor"):
            anchor = schema.get(keyword)
            if not isinstance(anchor, str):
                continue
            key = (id(resource_root), anchor)
            target = (schema, schema_path, resource_root, resource_path)
            if key in anchor_targets and anchor_targets[key] != target:
                anchor_targets[key] = None
            else:
                anchor_targets[key] = target

        for keyword in SINGLE_SUBSCHEMA_KEYWORDS:
            if keyword in schema:
                index_schema_resources(
                    schema[keyword],
                    f"{schema_path}/{keyword}",
                    resource_root,
                    resource_path,
                )
        for keyword in ARRAY_SUBSCHEMA_KEYWORDS:
            children = schema.get(keyword)
            if isinstance(children, list):
                for index, child in enumerate(children):
                    index_schema_resources(
                        child,
                        f"{schema_path}/{keyword}/{index}",
                        resource_root,
                        resource_path,
                    )
        for keyword in MAP_SUBSCHEMA_KEYWORDS:
            children = schema.get(keyword)
            if isinstance(children, dict):
                for name, child in children.items():
                    index_schema_resources(
                        child,
                        f"{schema_path}/{keyword}/{name}",
                        resource_root,
                        resource_path,
                    )

    def activate_target(
        target: tuple[Any, str, Any, str],
        reference_path: str,
    ) -> None:
        """Validate one resolved local target before treating it as a schema."""
        target_schema, target_path, target_resource, target_resource_path = target
        if not isinstance(target_schema, (bool, dict)):
            invalid_targets.append(
                f"{reference_path} resolves to {target_path}, which is not an "
                "object or boolean schema"
            )
            return
        try:
            if Draft202012Validator is not None:
                Draft202012Validator.check_schema(target_schema)
        except Exception as exc:  # jsonschema raises SchemaError
            reason = getattr(exc, "message", str(exc).splitlines()[0])
            invalid_targets.append(
                f"{reference_path} resolves to invalid schema {target_path}: {reason}"
            )
            return
        walk(target_schema, target_path, target_resource, target_resource_path)

    def walk(
        schema: Any,
        schema_path: str,
        resource_root: Any,
        resource_path: str,
    ) -> None:
        if isinstance(schema, bool) or not isinstance(schema, dict):
            return
        # A pointer can activate a schema stored below an otherwise opaque
        # keyword. Index that newly active schema's ordinary descendants before
        # resolving its own references.
        index_schema_resources(schema, schema_path, resource_root, resource_path)
        # Draft 2020-12 `$id` establishes a new schema resource. Fragment-only
        # references below it resolve from that resource, not from the outer
        # JSON document. The URI text itself does not need to be resolved here;
        # check_schema validates its syntax after this network-safety pass.
        if isinstance(schema.get("$id"), str):
            resource_root = schema
            resource_path = schema_path

        identity = (id(schema), id(resource_root))
        if identity in visited:
            return
        visited.add(identity)

        for keyword in REFERENCE_KEYWORDS:
            reference = schema.get(keyword)
            reference_path = f"{schema_path}/{keyword}"
            if not isinstance(reference, str):
                continue
            if reference == "" or reference.startswith("#"):
                target = _local_pointer_target(
                    resource_root,
                    reference,
                    resource_path,
                    resource_boundaries,
                )
                if target is not None:
                    activate_target(target, reference_path)
                elif reference.startswith("#"):
                    anchor = unquote(reference[1:])
                    target = anchor_targets.get((id(resource_root), anchor))
                    if target is None:
                        findings.append(reference_path)
                    else:
                        activate_target(target, reference_path)
            else:
                findings.append(reference_path)

        for keyword in SINGLE_SUBSCHEMA_KEYWORDS:
            if keyword in schema:
                walk(
                    schema[keyword],
                    f"{schema_path}/{keyword}",
                    resource_root,
                    resource_path,
                )

        for keyword in ARRAY_SUBSCHEMA_KEYWORDS:
            children = schema.get(keyword)
            if isinstance(children, list):
                for index, child in enumerate(children):
                    walk(
                        child,
                        f"{schema_path}/{keyword}/{index}",
                        resource_root,
                        resource_path,
                    )

        for keyword in MAP_SUBSCHEMA_KEYWORDS:
            children = schema.get(keyword)
            if isinstance(children, dict):
                for name, child in children.items():
                    walk(
                        child,
                        f"{schema_path}/{keyword}/{name}",
                        resource_root,
                        resource_path,
                    )

    walk(value, path, value, path)
    return findings, invalid_targets


def external_reference_paths(value: Any, path: str = "$") -> list[str]:
    """Return active external or unresolved references."""
    return reference_audit(value, path)[0]


def invalid_local_reference_targets(value: Any, path: str = "$") -> list[str]:
    """Return local references whose activated targets are not valid schemas."""
    return reference_audit(value, path)[1]


def refuse_schema_retrieval(uri: str) -> Any:
    """Fail closed if validation ever tries to retrieve a non-bundled resource."""
    raise RuntimeError(f"external schema retrieval is disabled: {uri}")


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

        external_refs, invalid_local_targets = reference_audit(schema)
        if external_refs:
            errors.append(
                f"schemas/{name}: external or unresolved $ref/$dynamicRef is forbidden at "
                + ", ".join(external_refs)
            )
        if invalid_local_targets:
            errors.append(
                f"schemas/{name}: local $ref/$dynamicRef target is not a valid "
                "Draft 2020-12 schema: "
                + "; ".join(invalid_local_targets)
            )
        if external_refs or invalid_local_targets:
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

        validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
            registry=Registry(retrieve=refuse_schema_retrieval),
        )
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
