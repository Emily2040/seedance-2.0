#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lineage_contract import (
    ACCEPTED_PARENT_STATUSES,
    classify_parent_id,
    has_usable_observed_end_state,
    parent_link_mode,
)


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
    "clip_id", "parent_clip_id", "scene_id", "sequence_index", "prompt_version", "generation_mode",
    "status", "narrative_job", "felt_intent", "already_happened", "this_clip_only", "reserved_for_later",
    "planned_start_state", "planned_end_state", "observed_start_state", "observed_end_state",
    "continuity_locks", "allowed_changes", "continuity_breaks", "accepted_deviations",
    "transition_in", "transition_out", "open_motion_vectors", "handoff_requirements",
    "extension_depth",
}
REQUIRED_CLIP_CONTRACT_FIELDS = {
    "project_id", "clip_id", "parent_clip_id", "scene_id", "sequence_index", "narrative_job", "felt_intent",
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
ACCEPTED = ACCEPTED_PARENT_STATUSES


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
    clips_by_id = {}
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
    for clip in data["clips"]:
        check_required(clip, REQUIRED_CLIP_FIELDS, f"{rel}: clip", errors)
        cid = clip.get("clip_id")
        if cid in clip_ids:
            errors.append(f"{rel}: duplicate clip_id {cid}")
        clip_ids.add(cid)
        clips_by_id.setdefault(cid, clip)
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
        if clip.get("status") in ACCEPTED:
            if not has_usable_observed_end_state(clip):
                errors.append(
                    f"{rel}: accepted clip {cid} observed_end_state must be a non-empty object"
                )
        if clip.get("status") == "rejected" and clip.get("observed_end_state"):
            errors.append(f"{rel}: rejected clip {cid} must not publish observed_end_state as canon")

    for clip in data["clips"]:
        cid = clip.get("clip_id")
        parent_kind, parent = classify_parent_id(clip)
        sequence_index = clip.get("sequence_index", 1)
        if parent_kind == "root":
            if isinstance(sequence_index, int) and not isinstance(sequence_index, bool) and sequence_index > 1:
                errors.append(f"{rel}: later clip {cid} missing parent_clip_id")
        elif parent_kind == "invalid":
            errors.append(
                f"{rel}: clip {cid} parent_clip_id must be null or a non-empty string"
            )
        elif parent == cid:
            errors.append(f"{rel}: clip {cid} cannot parent itself")
        elif parent not in clip_ids:
            errors.append(f"{rel}: clip {cid} parent {parent} is missing")
        else:
            parent_index = clips_by_id[parent].get("sequence_index")
            if (
                isinstance(sequence_index, int)
                and not isinstance(sequence_index, bool)
                and isinstance(parent_index, int)
                and not isinstance(parent_index, bool)
                and parent_index >= sequence_index
            ):
                errors.append(
                    f"{rel}: clip {cid} sequence_index {sequence_index} must be greater than "
                    f"parent {parent} sequence_index {parent_index}"
                )
            link_mode = parent_link_mode(clip, clips_by_id[parent])
            if link_mode == "missing_observed_end_state":
                errors.append(
                    f"{rel}: clip {cid} parent {parent} is accepted but missing observed_end_state"
                )
            elif link_mode == "unusable_status":
                errors.append(
                    f"{rel}: clip {cid} parent {parent} status "
                    f"{clips_by_id[parent].get('status')!r} is not usable"
                )
        overlap_current_future = set(clip.get("this_clip_only", [])) & set(clip.get("reserved_for_later", []))
        if overlap_current_future:
            errors.append(f"{rel}: clip {cid} overlaps current and reserved beats: {sorted(overlap_current_future)}")
        overlap_done_current = set(clip.get("already_happened", [])) & set(clip.get("this_clip_only", []))
        if overlap_done_current:
            errors.append(f"{rel}: clip {cid} replays completed beats: {sorted(overlap_done_current)}")

    visited_lineage = set()
    active_lineage = []
    active_positions = {}

    def visit_lineage(cid) -> None:
        if cid in visited_lineage:
            return
        if cid in active_positions:
            cycle = active_lineage[active_positions[cid]:] + [cid]
            errors.append(f"{rel}: clip lineage cycle: {' -> '.join(str(item) for item in cycle)}")
            return
        active_positions[cid] = len(active_lineage)
        active_lineage.append(cid)
        parent_kind, parent = classify_parent_id(clips_by_id[cid])
        if parent_kind == "parent" and parent in clips_by_id and parent != cid:
            visit_lineage(parent)
        active_lineage.pop()
        active_positions.pop(cid)
        visited_lineage.add(cid)

    for cid in clips_by_id:
        visit_lineage(cid)

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
            parent_kind, _ = classify_parent_id(obj)
            if parent_kind == "invalid":
                errors.append(f"{rel}: parent_clip_id must be null or a non-empty string")
            felt = obj.get("felt_intent")
            if "felt_intent" in obj and (not isinstance(felt, str) or not felt.strip()):
                errors.append(f"{rel}: felt_intent must be a non-empty one-line string")
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
