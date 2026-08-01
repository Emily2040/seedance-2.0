#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

if __package__:
    from .lineage_contract import (
        analyze_lineage,
        build_take_review_indexes,
        bound_validation_diagnostics,
        load_project_document,
        TakeReviewIndex,
        validate_take_reconciliation,
    )
    from .strict_json import (
        bound_diagnostics,
        diagnostic_path,
        diagnostic_text,
        validate_repo_input_path,
    )
else:
    from lineage_contract import (
        analyze_lineage,
        build_take_review_indexes,
        bound_validation_diagnostics,
        load_project_document,
        TakeReviewIndex,
        validate_take_reconciliation,
    )
    from strict_json import (
        bound_diagnostics,
        diagnostic_path,
        diagnostic_text,
        validate_repo_input_path,
    )


IMMUTABLE_KEYS = [
    "canonical_identity_id",
    "wardrobe",
    "product_identity",
    "prop_owner",
    "location",
    "vehicle_identity",
    "persistent_environment",
    "reference_tags",
]
TRANSIENT_KEYS = [
    "pose",
    "position_in_frame",
    "travel_direction",
    "motion_vector",
    "camera_phase",
    "focus_state",
    "lighting_phase",
    "emotional_state",
    "audio_phase",
]

FIELD_ALIASES = {
    "canonical_identity_id": ("canonical identity", "character identity"),
    "product_identity": ("product identity",),
    "prop_owner": ("prop owner", "prop ownership"),
    "vehicle_identity": ("vehicle identity",),
    "persistent_environment": ("persistent environment",),
    "reference_tags": ("reference tag", "reference tags"),
    "position_in_frame": ("position in frame",),
    "travel_direction": ("travel direction", "screen direction"),
    "motion_vector": ("motion vector",),
    "camera_phase": ("camera phase",),
    "focus_state": ("focus state",),
    "lighting_phase": ("lighting phase",),
    "emotional_state": ("emotional state",),
    "audio_phase": ("audio phase",),
}

TRANSITION_CHANGE_WORDS = {
    "break",
    "change",
    "changed",
    "changes",
    "changing",
    "deviation",
    "different",
    "new",
    "replace",
    "replaced",
    "replacement",
    "reset",
    "shift",
    "swap",
    "swapped",
    "switch",
    "transition",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_phrase(value: object) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value).casefold()))


def text_items(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item_key, item_value in value.items():
            yield str(item_key)
            yield from text_items(item_value)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from text_items(item)
    elif value is not None:
        yield str(value)


def field_phrases(key: str) -> set[str]:
    phrases = {normalize_phrase(key)}
    phrases.update(normalize_phrase(alias) for alias in FIELD_ALIASES.get(key, ()))
    return phrases


def mentions_field(text: str, key: str) -> bool:
    padded = f" {normalize_phrase(text)} "
    return any(f" {phrase} " in padded for phrase in field_phrases(key))


def is_axis_reset(text: str) -> bool:
    return " axis reset " in f" {normalize_phrase(text)} "


def has_allowance(clip: dict, key: str) -> bool:
    for field in ("allowed_changes", "accepted_deviations", "continuity_breaks"):
        for text in text_items(clip.get(field, [])):
            if mentions_field(text, key) or (key == "travel_direction" and is_axis_reset(text)):
                return True

    transition = normalize_phrase(clip.get("transition_in", ""))
    if key == "travel_direction" and is_axis_reset(transition):
        return True
    return mentions_field(transition, key) and bool(
        set(transition.split()) & TRANSITION_CHANGE_WORDS
    )


def list_item_label(value: dict, index: int) -> str:
    for identity_key in ("character_id", "id", "name"):
        identity = value.get(identity_key)
        if isinstance(identity, (str, int)):
            return str(identity)
    return str(index)


def state_values(state: dict | None, key: str) -> list[tuple[str, object]]:
    if not isinstance(state, dict):
        return []

    matches: list[tuple[str, object]] = []

    def visit(value: object, path: tuple[str, ...]) -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                child_path = path + (str(child_key),)
                if child_key == key and child_value is not None:
                    matches.append((".".join(child_path), child_value))
                if isinstance(child_value, (dict, list)):
                    visit(child_value, child_path)
        elif isinstance(value, list):
            for index, child_value in enumerate(value):
                label = list_item_label(child_value, index) if isinstance(child_value, dict) else str(index)
                visit(child_value, path + (label,))

    visit(state, ())
    return matches


def comparable_values(
    end_state: dict,
    start_state: dict,
    key: str,
) -> list[tuple[str, object, object]]:
    end_values = state_values(end_state, key)
    start_values = state_values(start_state, key)
    if len(end_values) == 1 and len(start_values) == 1:
        return [(key, end_values[0][1], start_values[0][1])]

    end_by_path = dict(end_values)
    start_by_path = dict(start_values)
    return [
        (path, end_by_path[path], start_by_path[path])
        for path in sorted(end_by_path.keys() & start_by_path.keys())
    ]


def validate(
    path: Path,
    root: Path,
    review_index: TakeReviewIndex | None = None,
) -> tuple[list[str], list[str]]:
    data, rel, errors = load_project_document(path, root)
    warnings: list[str] = []
    if data is None:
        return bound_validation_diagnostics(errors, rel), warnings
    lineage = analyze_lineage(data.get("clips"), rel)
    errors.extend(lineage.errors)
    if review_index is None:
        review_index = build_take_review_indexes([path])[path.resolve().parent]
    errors.extend(
        validate_take_reconciliation(data, lineage.clips_by_id, rel, review_index)
    )
    for clip, parent in lineage.accepted_links:
        end_state = parent.get("observed_end_state")
        start_state = clip.get("planned_start_state")
        if not start_state:
            errors.append(f"{rel}: clip {clip['clip_id']} missing planned_start_state")
            continue
        for key in IMMUTABLE_KEYS:
            for field_path, a, b in comparable_values(end_state, start_state, key):
                if a != b and not has_allowance(clip, key):
                    errors.append(
                        f"{rel}: immutable {field_path} changes from {a!r} to {b!r} without allowance"
                    )
        for key in TRANSIENT_KEYS:
            for field_path, a, b in comparable_values(end_state, start_state, key):
                if a != b and not has_allowance(clip, key):
                    warnings.append(
                        f"{rel}: transient {field_path} changes from {a!r} to {b!r} without allowance"
                    )
    return (
        bound_validation_diagnostics(errors, rel),
        bound_validation_diagnostics(warnings, rel),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat transient continuity warnings as validation errors",
    )
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    examples = root / "examples"
    if os.path.lexists(examples):
        try:
            examples = validate_repo_input_path(root, examples)
        except ValueError as exc:
            errors.append(f"examples: {exc}")
            examples = None
    else:
        examples = None
    candidates = (
        sorted(examples.rglob("*project-state*.json"))
        if examples is not None
        else []
    )
    paths: list[Path] = []
    for path in candidates:
        try:
            paths.append(validate_repo_input_path(root, path))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(
                f"{diagnostic_path(path.relative_to(root))}: "
                f"invalid project state: {exc}"
            )
    review_indexes = build_take_review_indexes(paths)
    for path in paths:
        try:
            e, w = validate(path, root, review_indexes[path.resolve().parent])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(
                f"{diagnostic_path(path.relative_to(root))}: "
                f"invalid project state: {exc}"
            )
            continue
        errors.extend(e)
        warnings.extend(w)
    warnings = bound_diagnostics(warnings, "additional continuity warnings omitted")
    errors = bound_diagnostics(errors, "additional continuity errors omitted")
    if warnings:
        print("Continuity warnings:")
        for warning in warnings:
            print(diagnostic_text(f"- {warning}"))
        print()
    if errors or (args.strict and warnings):
        print("Continuity errors:")
        for error in errors:
            print(diagnostic_text(f"- {error}"))
        if args.strict:
            for warning in warnings:
                print(diagnostic_text(f"- {warning}"))
        return 1
    print("Continuity chain check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
