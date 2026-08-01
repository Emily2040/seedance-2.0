#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from lineage_contract import analyze_lineage, load_project_document


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


def has_allowance(clip: dict, key: str) -> bool:
    blob = " ".join(str(item).lower() for item in (
        clip.get("transition_in", ""),
        clip.get("allowed_changes", []),
        clip.get("accepted_deviations", []),
        clip.get("continuity_breaks", []),
    ))
    return key.lower() in blob or "intentional" in blob or "axis reset" in blob


def state_value(state: dict | None, key: str):
    if not isinstance(state, dict):
        return None
    if key in state:
        return state.get(key)
    for value in state.values():
        if isinstance(value, dict) and key in value:
            return value.get(key)
    return None


def validate(path: Path, root: Path) -> tuple[list[str], list[str]]:
    data, rel, errors = load_project_document(path, root)
    warnings: list[str] = []
    if data is None:
        return errors, warnings
    lineage = analyze_lineage(data.get("clips"), rel)
    errors.extend(lineage.errors)
    for clip, parent in lineage.accepted_links:
        parent_id = parent.get("clip_id")
        end_state = parent.get("observed_end_state")
        start_state = clip.get("planned_start_state")
        if not start_state:
            errors.append(f"{rel}: clip {clip['clip_id']} missing planned_start_state")
            continue
        for key in IMMUTABLE_KEYS:
            a = state_value(end_state, key)
            b = state_value(start_state, key)
            if a is not None and b is not None and a != b and not has_allowance(clip, key):
                errors.append(f"{rel}: immutable {key} changes from {a!r} to {b!r} without allowance")
        for key in TRANSIENT_KEYS:
            a = state_value(end_state, key)
            b = state_value(start_state, key)
            if a is not None and b is not None and a != b and not has_allowance(clip, key):
                warnings.append(f"{rel}: transient {key} changes from {a!r} to {b!r} without allowance")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    for path in sorted((root / "examples").rglob("*project-state*.json")) if (root / "examples").exists() else []:
        e, w = validate(path, root)
        errors.extend(e)
        warnings.extend(w)
    if warnings:
        print("Continuity warnings:")
        for warning in warnings:
            print(f"- {warning}")
        print()
    if errors or (args.strict and warnings):
        print("Continuity errors:")
        for error in errors:
            print(f"- {error}")
        if args.strict:
            for warning in warnings:
                print(f"- {warning}")
        return 1
    print("Continuity chain check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
