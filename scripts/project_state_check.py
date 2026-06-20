#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_PROJECT_FIELDS = {
    "schema_version", "state_revision", "project_id", "project_mode", "surface",
    "clip_budget_sec", "prompt_budget", "story", "world_bible", "reference_registry",
    "beats", "clips", "take_history", "current_clip_id", "canon_revision", "updated_at",
}
REQUIRED_STORY_FIELDS = {
    "logline", "story_promise", "objective", "initial_condition", "final_outcome",
    "target_duration_sec", "tone", "medium",
}
REQUIRED_BEAT_FIELDS = {
    "beat_id", "description", "narrative_function", "status", "assigned_clip_id", "dependencies",
}
REQUIRED_CLIP_FIELDS = {
    "clip_id", "parent_clip_id", "sequence_index", "prompt_version", "generation_mode",
    "status", "narrative_job", "already_happened", "this_clip_only", "reserved_for_later",
    "planned_start_state", "planned_end_state", "observed_start_state", "observed_end_state",
    "continuity_locks", "allowed_changes", "continuity_breaks", "accepted_deviations",
    "transition_in", "transition_out", "open_motion_vectors", "handoff_requirements",
    "extension_depth",
}
REQUIRED_CLIP_CONTRACT_FIELDS = {
    "project_id", "clip_id", "parent_clip_id", "sequence_index", "narrative_job",
    "target_duration_sec", "generation_mode", "shot_structure", "already_happened",
    "this_clip_only", "reserved_for_later", "planned_start_state", "planned_end_state",
    "continuity_locks", "allowed_changes", "status",
}
REQUIRED_TAKE_REVIEW_FIELDS = {
    "project_id", "clip_id", "take_id", "source_status", "verdict",
    "observed_start_state", "observed_end_state", "completed_beats", "incomplete_beats",
    "unexpected_completed_beats", "continuity_breaks", "accepted_deviations",
    "observation_confidence", "uncertainties", "requires_user_confirmation",
}
ACCEPTED = {"accepted", "accepted_with_deviation"}


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def check_required(obj: dict, required: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(required - set(obj))
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(missing)}")


def sequence_paths(root: Path) -> list[Path]:
    paths = []
    for path in (root / "examples").rglob("*.json") if (root / "examples").exists() else []:
        if "project-state" in path.name:
            paths.append(path)
    return sorted(paths)


def validate_project(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    errors: list[str] = []
    try:
        data = load_json(path)
    except Exception as exc:
        return [f"{rel}: invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return [f"{rel}: project state must be an object"]

    check_required(data, REQUIRED_PROJECT_FIELDS, rel, errors)
    if errors:
        return errors

    if data["project_mode"] not in {"standalone_clip", "sequence_project"}:
        errors.append(f"{rel}: invalid project_mode {data['project_mode']}")
    if data["project_mode"] == "sequence_project" and not data["story"].get("final_outcome"):
        errors.append(f"{rel}: sequence project missing final_outcome")
    check_required(data["story"], REQUIRED_STORY_FIELDS, f"{rel}: story", errors)

    clip_ids = set()
    accepted_ids = set()
    for clip in data["clips"]:
        check_required(clip, REQUIRED_CLIP_FIELDS, f"{rel}: clip", errors)
        cid = clip.get("clip_id")
        if cid in clip_ids:
            errors.append(f"{rel}: duplicate clip_id {cid}")
        clip_ids.add(cid)
        if clip.get("status") in ACCEPTED:
            accepted_ids.add(cid)
            if not clip.get("observed_end_state"):
                errors.append(f"{rel}: accepted clip {cid} missing observed_end_state")
        if clip.get("status") == "rejected" and clip.get("observed_end_state"):
            errors.append(f"{rel}: rejected clip {cid} must not publish observed_end_state as canon")

    for clip in data["clips"]:
        cid = clip.get("clip_id")
        parent = clip.get("parent_clip_id")
        if clip.get("sequence_index", 1) > 1:
            if not parent:
                errors.append(f"{rel}: later clip {cid} missing parent_clip_id")
            elif parent not in clip_ids:
                errors.append(f"{rel}: later clip {cid} parent {parent} is missing")
            elif clip.get("status") != "planned" and parent not in accepted_ids:
                errors.append(f"{rel}: later clip {cid} parent {parent} is not accepted")
        overlap_current_future = set(clip.get("this_clip_only", [])) & set(clip.get("reserved_for_later", []))
        if overlap_current_future:
            errors.append(f"{rel}: clip {cid} overlaps current and reserved beats: {sorted(overlap_current_future)}")
        overlap_done_current = set(clip.get("already_happened", [])) & set(clip.get("this_clip_only", []))
        if overlap_done_current:
            errors.append(f"{rel}: clip {cid} replays completed beats: {sorted(overlap_done_current)}")

    for beat in data["beats"]:
        check_required(beat, REQUIRED_BEAT_FIELDS, f"{rel}: beat", errors)
        assigned = beat.get("assigned_clip_id")
        if assigned is not None and assigned not in clip_ids:
            errors.append(f"{rel}: beat {beat.get('beat_id')} assigned to missing clip {assigned}")

    for ref in data.get("reference_registry", []):
        if not ref.get("preserve_exact_tag"):
            errors.append(f"{rel}: reference {ref.get('tag')} must set preserve_exact_tag true")

    if data["current_clip_id"] not in clip_ids:
        errors.append(f"{rel}: current_clip_id missing from clips")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    errors: list[str] = []
    paths = sequence_paths(root)
    if not paths:
        errors.append("missing project-state examples")
    for path in paths:
        errors.extend(validate_project(path, root))

    for path in sorted((root / "examples").rglob("*.json")) if (root / "examples").exists() else []:
        rel = path.relative_to(root).as_posix()
        try:
            obj = load_json(path)
        except Exception as exc:
            errors.append(f"{rel}: invalid JSON: {exc}")
            continue
        if not isinstance(obj, dict):
            errors.append(f"{rel}: JSON example must be an object")
            continue
        if "contract" in path.name:
            check_required(obj, REQUIRED_CLIP_CONTRACT_FIELDS, rel, errors)
            if set(obj.get("this_clip_only", [])) & set(obj.get("reserved_for_later", [])):
                errors.append(f"{rel}: current and reserved beats overlap")
        if "take-review" in path.name or path.name == "take-review.json":
            check_required(obj, REQUIRED_TAKE_REVIEW_FIELDS, rel, errors)
            if obj.get("verdict") == "reject" and obj.get("accepted_deviations"):
                errors.append(f"{rel}: rejected take must not accept deviations")

    for schema in (root / "schemas").glob("*.schema.json") if (root / "schemas").exists() else []:
        try:
            load_json(schema)
        except Exception as exc:
            errors.append(f"{schema.relative_to(root).as_posix()}: invalid JSON: {exc}")

    if errors:
        print("Project state errors:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Project state check passed: {len(paths)} project states.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
