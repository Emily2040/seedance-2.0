#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from lineage_contract import (
    analyze_lineage,
    build_take_review_indexes,
    bound_validation_diagnostics,
    classify_parent_id,
    json_integer,
    is_take_review_path,
    load_bounded_take_review,
    load_project_document,
    TakeReviewIndex,
    validate_take_review_record,
    validate_take_reconciliation,
)
from strict_json import bound_diagnostics
from strict_json import load as load_strict_json


REQUIRED_PROJECT_FIELDS = {
    "schema_version", "state_revision", "project_id", "project_mode", "surface",
    "clip_budget_sec", "prompt_budget", "story", "world_bible", "reference_registry",
    "scenes", "beats", "clips", "take_history", "current_clip_id", "canon_revision", "updated_at",
}
REQUIRED_SCENE_FIELDS = {
    "scene_id", "scene_index", "narrative_function", "arc_position", "location",
    "time_of_day", "anchor_source", "max_chain_depth", "audio_plan",
    "assigned_clip_ids", "transition_out", "status",
}
ARC_POSITIONS = {"open", "rising", "turn", "climax", "release"}
SCENE_STATUSES = {"planned", "current", "completed", "omitted", "replaced"}
MAX_CHAIN_DEPTH_CEILING = 3
REQUIRED_STORY_FIELDS = {
    "logline", "story_promise", "objective", "initial_condition", "final_outcome",
    "target_duration_sec", "tone", "medium",
}
REQUIRED_BEAT_FIELDS = {
    "beat_id", "description", "narrative_function", "status", "assigned_clip_id", "dependencies",
}
REQUIRED_CLIP_FIELDS = {
    "clip_id", "scene_id", "sequence_index", "prompt_version", "generation_mode",
    "status", "narrative_job", "felt_intent", "already_happened", "this_clip_only", "reserved_for_later",
    "planned_start_state", "planned_end_state", "observed_start_state", "observed_end_state",
    "continuity_locks", "allowed_changes", "continuity_breaks", "accepted_deviations",
    "transition_in", "transition_out", "open_motion_vectors", "handoff_requirements",
    "extension_depth",
}
REQUIRED_CLIP_CONTRACT_FIELDS = {
    "project_id", "clip_id", "scene_id", "sequence_index", "narrative_job", "felt_intent",
    "target_duration_sec", "generation_mode", "shot_structure", "already_happened",
    "this_clip_only", "reserved_for_later", "planned_start_state", "planned_end_state",
    "continuity_locks", "allowed_changes", "status",
}


def load_json(path: Path) -> object:
    return load_strict_json(path)


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


def validate_project(
    path: Path,
    root: Path,
    review_index: TakeReviewIndex | None = None,
) -> list[str]:
    data, rel, errors = load_project_document(path, root)
    if data is None:
        return bound_validation_diagnostics(errors, rel)

    lineage = analyze_lineage(data.get("clips"), rel)
    errors.extend(lineage.errors)
    check_required(data, REQUIRED_PROJECT_FIELDS, rel, errors)
    missing_project_fields = REQUIRED_PROJECT_FIELDS - set(data)
    if missing_project_fields:
        return bound_validation_diagnostics(errors, rel)

    clips = lineage.clips
    clips_by_id = lineage.clips_by_id
    clip_ids = set(clips_by_id)
    if review_index is None:
        review_index = build_take_review_indexes([path])[path.resolve().parent]
    errors.extend(validate_take_reconciliation(data, clips_by_id, rel, review_index))

    if data["project_mode"] not in {"standalone_clip", "sequence_project"}:
        errors.append(f"{rel}: invalid project_mode {data['project_mode']}")
    if data["project_mode"] == "sequence_project" and not data["story"].get("final_outcome"):
        errors.append(f"{rel}: sequence project missing final_outcome")
    check_required(data["story"], REQUIRED_STORY_FIELDS, f"{rel}: story", errors)

    scene_ids = set()
    scene_depth_caps = {}
    scene_indexes = set()
    scene_assigned = {}
    clip_scene = {}
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list):
        errors.append(f"{rel}: scenes must be an array of scene objects")
        scenes = []
    for scene in scenes:
        if not isinstance(scene, dict):
            errors.append(f"{rel}: scenes entries must be objects")
            continue
        check_required(scene, REQUIRED_SCENE_FIELDS, f"{rel}: scene", errors)
        sid = scene.get("scene_id")
        if sid in scene_ids:
            errors.append(f"{rel}: duplicate scene_id {sid}")
        scene_ids.add(sid)
        idx = scene.get("scene_index")
        if not isinstance(idx, int) or isinstance(idx, bool) or idx < 1:
            errors.append(f"{rel}: scene {sid} scene_index must be an integer >= 1")
        elif idx in scene_indexes:
            errors.append(f"{rel}: duplicate scene_index {idx}")
        else:
            scene_indexes.add(idx)
        if scene.get("status") not in SCENE_STATUSES:
            errors.append(f"{rel}: scene {sid} invalid status {scene.get('status')}")
        if scene.get("arc_position") not in ARC_POSITIONS:
            errors.append(f"{rel}: scene {sid} invalid arc_position {scene.get('arc_position')}")
        depth_cap = scene.get("max_chain_depth")
        if not isinstance(depth_cap, int) or isinstance(depth_cap, bool) or depth_cap < 0 or depth_cap > MAX_CHAIN_DEPTH_CEILING:
            errors.append(f"{rel}: scene {sid} max_chain_depth must be an integer between 0 and {MAX_CHAIN_DEPTH_CEILING}")
        else:
            scene_depth_caps[sid] = depth_cap
        assigned_list = scene.get("assigned_clip_ids", [])
        seen_assigned = set()
        for assigned in assigned_list if isinstance(assigned_list, list) else []:
            if assigned in seen_assigned:
                errors.append(f"{rel}: scene {sid} lists clip {assigned} more than once")
            seen_assigned.add(assigned)
        scene_assigned[sid] = seen_assigned
    for clip in clips:
        check_required(clip, REQUIRED_CLIP_FIELDS, f"{rel}: clip", errors)
        cid = clip.get("clip_id")
        if (
            not isinstance(cid, str)
            or not cid.strip()
            or clips_by_id.get(cid) is not clip
        ):
            continue
        sid = clip.get("scene_id")
        clip_scene[cid] = sid
        depth = clip.get("extension_depth")
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
            errors.append(f"{rel}: clip {cid} extension_depth must be a non-negative integer")
            depth = None
        felt = clip.get("felt_intent")
        if "felt_intent" in clip and (not isinstance(felt, str) or not felt.strip()):
            errors.append(f"{rel}: clip {cid} felt_intent must be a non-empty one-line string")
        if sid not in scene_ids:
            errors.append(f"{rel}: clip {cid} scene {sid} is missing")
        elif sid in scene_depth_caps and depth is not None and depth > scene_depth_caps[sid]:
            errors.append(
                f"{rel}: clip {cid} extension_depth {depth} exceeds "
                f"scene {sid} max_chain_depth {scene_depth_caps[sid]}; open from canonical references instead"
            )
    for clip in clips:
        cid = clip.get("clip_id")
        if (
            not isinstance(cid, str)
            or not cid.strip()
            or clips_by_id.get(cid) is not clip
        ):
            continue
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

    assignment_owners = {}
    for sid, assigned_set in scene_assigned.items():
        for assigned in assigned_set:
            if assigned not in clip_ids:
                errors.append(f"{rel}: scene {sid} assigned to missing clip {assigned}")
            assignment_owners.setdefault(assigned, []).append(sid)
    for cid, owners in assignment_owners.items():
        if len(owners) > 1:
            errors.append(f"{rel}: clip {cid} is assigned to multiple scenes: {sorted(owners)}")
    for cid, sid in clip_scene.items():
        if sid in scene_assigned and cid not in scene_assigned[sid]:
            errors.append(f"{rel}: clip {cid} carries scene_id {sid} but scene {sid} does not list it in assigned_clip_ids")
        owners = assignment_owners.get(cid, [])
        if owners and sid not in owners:
            errors.append(f"{rel}: clip {cid} carries scene_id {sid} but is listed under scene {owners[0]}")

    for ref in data.get("reference_registry", []):
        if not ref.get("preserve_exact_tag"):
            errors.append(f"{rel}: reference {ref.get('tag')} must set preserve_exact_tag true")

    if data["current_clip_id"] not in clip_ids:
        errors.append(f"{rel}: current_clip_id missing from clips")
    return bound_validation_diagnostics(errors, rel)


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
    review_indexes = build_take_review_indexes(paths)
    for path in paths:
        errors.extend(
            validate_project(path, root, review_indexes[path.resolve().parent])
        )

    for path in sorted((root / "examples").rglob("*.json")) if (root / "examples").exists() else []:
        rel = path.relative_to(root).as_posix()
        is_take_review = is_take_review_path(path)
        if is_take_review and path.parent.resolve() in review_indexes:
            # The directory index already loaded and validated this candidate
            # through the stable, bounded authority reader. Invalid, excluded,
            # oversized, and over-budget candidates are represented by its
            # diagnostics and must never be re-read by the generic JSON path.
            continue
        try:
            obj = load_bounded_take_review(path) if is_take_review else load_json(path)
        except Exception as exc:
            errors.append(f"{rel}: invalid JSON: {exc}")
            continue
        if not isinstance(obj, dict):
            errors.append(f"{rel}: JSON example must be an object")
            continue
        if "contract" in path.name:
            check_required(obj, REQUIRED_CLIP_CONTRACT_FIELDS, rel, errors)
            parent_kind, _ = classify_parent_id(obj)
            if parent_kind == "invalid":
                errors.append(f"{rel}: parent_clip_id must be null or a non-empty string")
            sequence_index = json_integer(obj.get("sequence_index"))
            if parent_kind == "root" and sequence_index is not None and sequence_index > 1:
                errors.append(
                    f"{rel}: later clip sequence_index {obj.get('sequence_index')} "
                    "must declare a non-empty parent_clip_id"
                )
            felt = obj.get("felt_intent")
            if "felt_intent" in obj and (not isinstance(felt, str) or not felt.strip()):
                errors.append(f"{rel}: felt_intent must be a non-empty one-line string")
            if set(obj.get("this_clip_only", [])) & set(obj.get("reserved_for_later", [])):
                errors.append(f"{rel}: current and reserved beats overlap")
        if is_take_review:
            errors.extend(validate_take_review_record(obj, rel))

    for schema in (root / "schemas").glob("*.schema.json") if (root / "schemas").exists() else []:
        try:
            load_json(schema)
        except Exception as exc:
            errors.append(f"{schema.relative_to(root).as_posix()}: invalid JSON: {exc}")

    errors = bound_diagnostics(errors, "additional project-state diagnostics omitted")
    if errors:
        print("Project state errors:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Project state check passed: {len(paths)} project states.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
