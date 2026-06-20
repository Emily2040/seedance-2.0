#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_SEQUENCE_IDS = {
    "sequence_long_idea_routes_to_plan",
    "standalone_clip_does_not_overplan",
    "sequence_defines_final_outcome",
    "sequence_outputs_only_first_final_prompt",
    "continuation_requires_source_clip",
    "continuation_requires_observed_end_state",
    "continuation_uses_observed_not_planned_state",
    "continuation_does_not_replay_previous_action",
    "continuation_respects_reserved_future_beats",
    "continuation_preserves_open_motion_vector",
    "native_extend_vs_next_shot",
    "accepted_take_updates_canon",
    "rejected_take_does_not_update_canon",
    "accepted_deviation_replans_downstream",
    "unexpected_completed_beat_removed_from_future",
    "unfinished_beat_carried_or_repaired",
    "clip_lineage_parent_id",
    "reference_tags_survive_clip_chain",
    "exact_reference_tag_preserved",
    "reference_transfer_and_ignore_present",
    "multi_subject_reference_selector",
    "local_reference_reanchor",
    "continuity_source_vs_motion_reference",
    "multi_character_screen_direction_handoff",
    "prop_state_handoff",
    "audio_state_handoff",
    "camera_phase_handoff",
    "extension_drift_triggers_reanchor",
    "cross_session_project_capsule",
    "compact_prompt_does_not_become_dense",
    "dense_storyboard_has_completed_shot_endpoints",
    "continuous_take_uses_phases_not_shot_labels",
    "multishot_uses_shot_labels_not_continuous_take",
    "screen_direction_preserved",
    "physical_contact_has_consequence_chain",
    "abstract_mood_has_visible_evidence",
    "camera_has_start_path_and_endpoint",
    "2d_prompt_rejects_live_action_lens_language",
    "continuation_excludes_completed_action",
    "continuation_excludes_reserved_future_action",
    "prompt_budget_is_surface_specific",
    "internal_json_not_emitted_to_seedance",
    "compression_preserves_reference_contracts",
    "four_shot_mode_requires_verified_profile",
    "i2v_does_not_redundantly_redescribe_image",
    "r2v_reference_roles_do_not_bleed",
    "sequence_prompt_contains_only_current_clip",
}


REQUIRED_OPTIONAL_FIELDS = {
    "critical",
    "expected_state_delta",
    "forbidden_behaviors",
    "required_output_sections",
    "expected_prompt_architecture",
    "expected_sequence_relation",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    path = root / "evals" / "evals.json"
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Invalid eval JSON: {exc}")
        return 1
    cases = data.get("cases", [])
    by_id = {case.get("id"): case for case in cases if isinstance(case, dict)}
    missing = sorted(REQUIRED_SEQUENCE_IDS - set(by_id))
    if missing:
        errors.append("missing sequence eval ids: " + ", ".join(missing))
    critical = [case for cid, case in by_id.items() if cid in REQUIRED_SEQUENCE_IDS and case.get("critical") is True]
    if len(critical) < 12:
        errors.append("at least 12 sequence evals must be marked critical")
    for cid in REQUIRED_SEQUENCE_IDS:
        case = by_id.get(cid)
        if not case:
            continue
        for field in REQUIRED_OPTIONAL_FIELDS:
            if field not in case:
                errors.append(f"{cid}: missing {field}")
        if "seedance-sequence" not in case.get("skills_expected_to_activate", []) and "seedance-continuation" not in case.get("skills_expected_to_activate", []) and "seedance-prompt" not in case.get("skills_expected_to_activate", []):
            errors.append(f"{cid}: missing expected sequence/continuation/prompt skill activation")
    if errors:
        print("Sequence eval errors:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Sequence eval check passed: {len(REQUIRED_SEQUENCE_IDS)} sequence cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
