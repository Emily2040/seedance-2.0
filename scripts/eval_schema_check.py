#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = ["id", "prompt", "expected_output", "assertions", "skills_expected_to_activate", "failure_mode"]
REQUIRED_IDS = {
    "api_status_check",
    "audio_lipsync",
    "copyright_rewrite",
    "direct_prompt_t2v",
    "filter_repair",
    "frontend_design_audit",
    "frontend_redesign",
    "i2v_minimal",
    "multi_character_scene",
    "product_ad_recipe",
    "progressive_disclosure",
    "real_person_authorization",
    "reference_role_map",
    "source_verification",
    "style_safe_animation",
    "troubleshoot_camera_chaos",
    "vague_idea_interview",
    "zh_compression",
    "model_name_accuracy",
    "source_freshness_gate",
    "first_last_frame_workflow",
    "zh_role_binding_multimodal",
    "ru_role_binding_multimodal",
    "unsafe_bypass_refusal",
    "community_corpus_safety",
    "reference_audio_conflict",
    "zh_official_task_formula",
    "edit_extend_vs_regenerate",
    "ru_structured_prompt",
    "shot_list_continuity",
    "community_gallery_safety_classification",
    "vfx_reference_video_repair",
    "extension_quality_degradation",
    "multilingual_false_positive_repair",
    "cinematic_infographic_front_page",
    "professional_shot_contract",
    "multi_shot_continuity_handoff",
    "aces_color_pipeline_no_hallucination",
    "aspect_ratio_delivery_surface",
    "subtitle_localization_accessibility",
    "audio_post_loudness_stems",
    "delivery_qc_preflight",
    "imf_localization_versioning",
    "visual_gallery_six_text_rich_assets",
    "anti_slop_rewrite",
    "chinese_examples_safe_rewrite",
    "japanese_prompt_translation",
    "korean_prompt_translation",
    "spanish_prompt_translation",
    "russian_dialogue_prompt",
    "short_interview_three_questions",
    "vfx_physics_endpoint",
    "platform_spec_fal_verification",
    "prohibited_request_plain_refusal",
    "wrong_model_craft_only",
    "no_background_plain_interview",
    "english_slop_and_filter_vocab",
    "multilingual_slop_decomposition",
    "multi_person_action_hierarchy",
    "novel_case_mechanism_reasoning",
    "retake_triage_discipline",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    path = Path(args.repo) / "evals" / "evals.json"
    if not path.exists():
        print("Missing evals/evals.json")
        return 1

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Invalid JSON: {exc}")
        return 1

    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) < 16:
        print("evals/evals.json must contain at least 16 cases")
        return 1

    ids = set()
    errors = []
    for i, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"case {i} is not an object")
            continue
        for field in REQUIRED:
            if field not in case:
                errors.append(f"case {i} missing {field}")
        cid = case.get("id")
        if cid in ids:
            errors.append(f"duplicate id: {cid}")
        ids.add(cid)
        if not isinstance(case.get("assertions"), list) or len(case.get("assertions", [])) < 2:
            errors.append(f"case {cid} needs at least two assertions")
        if not isinstance(case.get("skills_expected_to_activate"), list) or not case.get("skills_expected_to_activate"):
            errors.append(f"case {cid} needs skills_expected_to_activate")

    missing_ids = REQUIRED_IDS - ids
    if missing_ids:
        errors.append("missing required eval ids: " + ", ".join(sorted(missing_ids)))

    if errors:
        print("Eval schema errors:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Eval schema passed: {len(cases)} cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
