# Sequence Project State

Use this reference when a Seedance request becomes a multi-clip project. The project state is the source of truth; prompts are temporary compiled instructions for one generation.

## Operating Model

User idea -> story spine -> world and continuity bible -> sequence plan -> current clip contract -> current clip prompt -> generated take -> observed take review -> canon reconciliation -> next clip contract -> next prompt.

Plan globally. Generate locally. Observe the real result. Update canon. Continue from actual accepted footage.

## Canonical State

Keep canonical and transient state separate.

Canonical references control identity and immutable design: character identity, product identity, wardrobe, product geometry, persistent props, location, and approved reference tags.

Accepted previous footage controls transient opening state: pose, action phase, screen position, camera phase, environment arrangement, audio phase, open motion, and incomplete gestures.

## Required Project Fields

At minimum, a project state contains `schema_version`, `state_revision`, `project_id`, `project_mode`, `surface`, `clip_budget_sec`, `prompt_budget`, `story`, `world_bible`, `reference_registry`, `beats`, `clips`, `take_history`, `current_clip_id`, `canon_revision`, and `updated_at`.

Story fields: `logline`, `story_promise`, `objective`, `initial_condition`, `final_outcome`, `target_duration_sec`, `tone`, and `medium`.

Beat fields: `beat_id`, `description`, `narrative_function`, `status`, `assigned_clip_id`, and `dependencies`.

Clip lineage fields: `clip_id`, `parent_clip_id`, `sequence_index`, `prompt_version`, `generation_mode`, `source_clip_tag`, `status`, `narrative_job`, `already_happened`, `this_clip_only`, `reserved_for_later`, `planned_start_state`, `planned_end_state`, `observed_start_state`, `observed_end_state`, `continuity_locks`, `allowed_changes`, `continuity_breaks`, `accepted_deviations`, `transition_in`, `transition_out`, `open_motion_vectors`, `handoff_requirements`, and `extension_depth`.

## Visual State

Track only what matters and do not invent unclear details.

Characters: canonical identity ID, wardrobe, hair, position in world, position in frame, pose, action phase, emotional state, gaze, eyeline, travel direction, speed, and body orientation.

Props: identity, owner, position, condition, motion, and interaction state.

Environment: location, geography, background arrangement, time of day, weather, atmosphere, and persistent practical elements.

Camera: shot size, height, angle, support, path, direction, speed, movement phase, subject relationship, focus state, exposure state, and endpoint.

Lighting: key direction, intensity, color relationship, practical sources, and transition state.

Audio: ambience, completed dialogue, active dialogue, music phase, SFX phase, active engine or environmental sounds, and audio reference ownership.

Open motion: subject direction and speed, camera direction and speed, moving props, incomplete gestures, cloth or hair follow-through, vehicle movement, and pending impact recovery.

Observation quality: `observation_confidence`, `uncertainties`, and `requires_user_confirmation`.

## Reconciliation

When an accepted clip differs from plan:

1. Record the deviation.
2. Decide whether to accept as canon, repair, reject/regenerate, or re-anchor the next shot.
3. If accepted, update downstream planning.
4. Remove any beat unexpectedly completed.
5. Carry any incomplete planned beat into the next appropriate clip.
6. Never pretend the planned ending happened when it did not.

Rejected footage does not alter canon and cannot become a continuation parent.

## Project State Capsule

Use a readable capsule for cross-session continuation. A new conversation cannot be assumed to possess hidden prior memory.

Required fields:

PROJECT ID:
STORY GOAL:
FINAL OUTCOME:
SURFACE:
REFERENCE TAGS:
CANONICAL REFERENCES:
ACCEPTED CLIPS:
CURRENT ACTUAL STATE:
OPEN MOTION:
COMPLETED BEATS:
NEXT CLIP JOB:
CONTINUITY LOCKS:
ALLOWED CHANGES:
RESERVED FUTURE BEATS:
EXTENSION DEPTH:
UNRESOLVED UNCERTAINTIES:
