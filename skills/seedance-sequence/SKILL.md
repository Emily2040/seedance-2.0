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
  version: "6.7.0"
  updated: "2026-08-01"
  parent: "seedance-20"
  author: "Iamemily2050 (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: "🎬"
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-sequence

Use this when the user's idea is larger than one reliable generation, when connected clips are requested, or when the user says continue, extend, next part, part two, next scene, or make it longer. Plan globally, generate locally: the skill plans the whole story, but compiles only the next unresolved clip.

Load `[ref:sequence-project-state]`, `[ref:continuation-handoff]`, `[ref:prompt-compiler]`, `[ref:surface-prompt-profiles]`, `[ref:event-density]`, and `[ref:continuity-qc]`. Load `[ref:reference-transfer-contract]` when references are present and `[ref:dense-storyboard-mode]` when the request contains many shots or animation panels. Load `[ref:directing-engine]` to set one directorial voice for the whole story and plan the long-form spine so the look is authored by one hand across every clip. For a user's first multi-clip project, `[ref:sequence-worked-trace]` walks the whole loop once - plan, deviation, reconciliation, chain cap, re-anchor, resume.

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

## Scene Architecture

Plan scenes before clips. A scene is the re-anchor unit: one location and time envelope whose clips may chain from each other's accepted footage.

- Seamless continuation is legal only inside a scene. A scene boundary is an intentional cut that opens from canonical references and resets `extension_depth` to 0.
- Cap consecutive output-sourced generations at the scene's `max_chain_depth` (default 2, hard ceiling 3). Schedule re-anchors in the plan; identity decays with chained generations, so a scheduled reset is routine and a drift repair is expensive.
- Map the arc to scenes: each scene carries one `arc_position` and its clips inherit it.
- Cuts are the cheapest continuity tool. The audience expects frame continuity only inside a chained shot, not across an editorial cut. A five-minute story usually resolves to several scenes of two to five clips, not one long extension chain.
- Audio: clips carry ambience, sync SFX, and on-camera dialogue; unify music and score in post because audio is not continuous across separate generations.

## Build Process

1. Establish the story promise and final outcome before Clip 01.
2. Identify the character, product, or narrative objective, and with `[ref:directing-engine]` set one directorial voice for the whole project and plan the long-form spine - how shot scale, camera movement, light contrast, and sound should progress from open to climax to release, and which single clip breaks the pattern to mark the turn.
3. Extract ordered beats and assign each beat a status: planned, current, completed, omitted, or replaced.
4. Group beats into scenes: assign each scene one location and time envelope, one `arc_position`, canonical `anchor_source` references, `max_chain_depth` (default 2), and an audio plan.
5. Divide each scene into generation-sized clips using the active surface budget or conservative assumption; chain clips from accepted footage only inside a scene, and open every scene from canonical references.
6. Give every clip one narrative job, one `felt_intent` - a single line naming what the viewer should feel or notice, the directing engine's intention made persistent in state - and one completed endpoint.
7. Define planned opening state, planned ending state, continuity locks, allowed changes, and extension-friendly handoff requirements.
8. Store later clips as provisional intent cards, not final prompts.
9. Compile only the first unresolved clip prompt from the current clip contract.
10. After generation, require the clip or final frame, record observed start/end state, reconcile canon, and only then compile the next prompt.

Use beginner-friendly language. It is valid to say: "This idea needs three connected generations. I will plan the complete story now, but finalize one prompt at a time so each new prompt matches what Seedance actually produced."

## Sequence Map Fields

Each clip card must include `clip_id`, `scene_id`, `sequence_index`, `parent_clip_id`, `narrative_job`, `felt_intent`, `target_duration_sec`, `generation_mode`, `shot_structure`, `already_happened`, `this_clip_only`, `reserved_for_later`, `planned_start_state`, `planned_end_state`, `transition_in`, `transition_out`, `continuity_locks`, `allowed_changes`, `arc_position`, and `status`. The `arc_position` (open, rising, turn, climax, or release) is inherited from the clip's scene and records where it sits on the directorial spine so its scale, movement, light, and sound trends inherit the project voice.

Each scene card must include `scene_id`, `scene_index`, `narrative_function`, `arc_position`, `location`, `time_of_day`, `anchor_source`, `max_chain_depth`, `audio_plan`, `assigned_clip_ids`, `transition_out`, and `status`.

Clip 01 can plan "exit terminal and reach open car door" with the endpoint "subject beside the open rear door" while reserving "entering the car" and "vehicle departure" for later clips. Do not paste all planned clips into one generation prompt.

## Output Contract

For a new sequence, return:

1. Project summary.
2. Story spine.
3. Final outcome.
4. World and continuity bible, including the chosen directorial voice and the long-form look spine (how scale, movement, light, and sound progress, and which clip breaks the pattern).
5. Scene map and sequence map.
6. Clip 01 contract.
7. Intent echo: one line - "this clip exists so the viewer feels X" - confirmed before generation spends money.
8. Clip 01 final Seedance prompt in natural language.
9. Provisional intent cards for future clips.
10. Instruction to return the generated clip or final frame before Clip 02 is finalized.
11. Project State Capsule.

Do not output internal JSON unless the user asks for it. The readable capsule is the cross-session handoff.
