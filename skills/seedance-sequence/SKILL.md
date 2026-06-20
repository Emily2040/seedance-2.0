---
name: seedance-sequence
description: "This skill should be used when a Seedance 2.0 request is a long story, connected set of clips, multi-generation scene, campaign sequence, dense storyboard, continuation-ready plan, or any idea that must be divided into stateful clips."
license: MIT
user-invocable: true
tags:
  - sequence
  - continuity
  - prompt-compiler
  - seedance-20
metadata:
  version: "6.0.0"
  updated: "2026-06-20"
  parent: "seedance-20"
  author: "Iamemily2050 (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: "🎬"
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-sequence

Use this when the user's idea is larger than one reliable generation, when connected clips are requested, or when the user says continue, extend, next part, part two, next scene, or make it longer. Plan globally, generate locally: the skill plans the whole story, but compiles only the next unresolved clip.

Load `[ref:sequence-project-state]`, `[ref:continuation-handoff]`, `[ref:prompt-compiler]`, `[ref:surface-prompt-profiles]`, `[ref:event-density]`, and `[ref:continuity-qc]`. Load `[ref:reference-transfer-contract]` when references are present and `[ref:dense-storyboard-mode]` when the request contains many shots or animation panels.

## Intent

The user is trying to make a film, not a pile of prompts. This skill protects the thread of action across generations: what already happened, what is happening now, what must not happen yet, and what the accepted footage actually shows. The plan is global; the prompt is local.

## Sequence Classifier

Classify as `sequence_project` when the story exceeds the verified active-surface duration, asks for multiple connected clips, contains several narrative beats, is a film scene, ad, campaign, music sequence, action scene, dialogue scene, or uses continue/extend/next-part language. Otherwise classify as `standalone_clip` and return to the concise prompt path.

For every request also classify:

- generation input mode: T2V, I2V, V2V, R2V, FLF2V, edit, native extend when verified for the active surface, or troubleshoot;
- sequence relation: standalone, sequence_first_clip, seamless_continuation, intentional_next_shot, bridge_between_known_states, repair_tail, or reanchor_after_drift;
- shot structure: compact_single_take, phased_single_take, dense_multishot, first_last_frame_transition, or video_edit_contract;
- medium grammar: live_action, 3d_animation, 2d_animation, product_or_object, or another supported medium;
- surface profile: exact reference-tag convention, verified duration range, prompt budget, supported reference roles, timeline syntax, edit/extension availability, audio behavior, and constraints.

If the surface is unknown, use a conservative generic profile. Do not invent a duration, prompt limit, reference count, or tag syntax.

## Build Process

1. Establish the story promise and final outcome before Clip 01.
2. Identify the character, product, or narrative objective.
3. Extract ordered beats and assign each beat a status: planned, current, completed, omitted, or replaced.
4. Divide beats into generation-sized clips using the active surface budget or conservative assumption.
5. Give every clip one narrative job and one completed endpoint.
6. Define planned opening state, planned ending state, continuity locks, allowed changes, and extension-friendly handoff requirements.
7. Store later clips as provisional intent cards, not final prompts.
8. Compile only the first unresolved clip prompt from the current clip contract.
9. After generation, require the clip or final frame, record observed start/end state, reconcile canon, and only then compile the next prompt.

Use beginner-friendly language. It is valid to say: "This idea needs three connected generations. I will plan the complete story now, but finalize one prompt at a time so each new prompt matches what Seedance actually produced."

## Sequence Map Fields

Each clip card must include `clip_id`, `sequence_index`, `parent_clip_id`, `narrative_job`, `target_duration_sec`, `generation_mode`, `shot_structure`, `already_happened`, `this_clip_only`, `reserved_for_later`, `planned_start_state`, `planned_end_state`, `transition_in`, `transition_out`, `continuity_locks`, `allowed_changes`, and `status`.

Clip 01 can plan "exit terminal and reach open car door" with the endpoint "subject beside the open rear door" while reserving "entering the car" and "vehicle departure" for later clips. Do not paste all planned clips into one generation prompt.

## Output Contract

For a new sequence, return:

1. Project summary.
2. Story spine.
3. Final outcome.
4. World and continuity bible.
5. Sequence map.
6. Clip 01 contract.
7. Clip 01 final Seedance prompt in natural language.
8. Provisional intent cards for future clips.
9. Instruction to return the generated clip or final frame before Clip 02 is finalized.
10. Project State Capsule.

Do not output internal JSON unless the user asks for it. The readable capsule is the cross-session handoff.
