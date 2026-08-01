# Sequence Project State

Use this reference when a Seedance request becomes a multi-clip project. The project state is the source of truth; prompts are temporary compiled instructions for one generation.

## Operating Model

User idea -> story spine -> world and continuity bible -> scene plan -> sequence plan -> current clip contract -> current clip prompt -> generated take -> observed take review -> canon reconciliation -> next clip contract -> next prompt.

Plan globally. Generate locally. Observe the real result. Update canon. Continue from actual accepted footage.

## Canonical State

Keep canonical and transient state separate.

Canonical references control identity and immutable design: character identity, product identity, wardrobe, product geometry, persistent props, location, and approved reference tags.

Accepted previous footage controls transient opening state: pose, action phase, screen position, camera phase, environment arrangement, audio phase, open motion, and incomplete gestures.

## Scene Layer

A scene is the re-anchor unit: one location and time envelope whose clips may chain from each other's accepted footage. Scenes group beats and own clips; every clip carries exactly one `scene_id`.

Seamless continuation is legal only inside a scene. A scene boundary is an intentional cut: the next clip opens from canonical references, not from prior output, and `extension_depth` resets to 0.

`extension_depth` counts consecutive output-sourced generations since the last canonical re-anchor. It resets to 0 whenever a clip opens from canonical references. It may not exceed the scene's `max_chain_depth` (default 2, hard ceiling 3): a clip that would exceed it must open from canonical references instead. Schedule these re-anchors in the plan; do not wait for visible drift.

Map the arc to scenes, not clips: each scene carries one `arc_position` (open, rising, turn, climax, or release) and its clips inherit it.

Audio plan: clips carry ambience, sync SFX, and on-camera dialogue only. Unify music and score in post, because audio is not continuous across separate generations. Do not ask each clip for score.

## Required Project Fields

At minimum, a project state contains `schema_version`, `state_revision`, `project_id`, `project_mode`, `surface`, `clip_budget_sec`, `prompt_budget`, `story`, `world_bible`, `reference_registry`, `scenes`, `beats`, `clips`, `take_history`, `current_clip_id`, `canon_revision`, and `updated_at`.

Story fields: `logline`, `story_promise`, `objective`, `initial_condition`, `final_outcome`, `target_duration_sec`, `tone`, and `medium`.

Scene fields: `scene_id`, `scene_index`, `narrative_function`, `arc_position`, `location`, `time_of_day`, `anchor_source`, `max_chain_depth`, `audio_plan`, `assigned_clip_ids`, `transition_out`, and `status`.

Beat fields: `beat_id`, `description`, `narrative_function`, `status`, `assigned_clip_id`, and `dependencies`.

Clip lineage fields: `clip_id`, `parent_clip_id`, `scene_id`, `sequence_index`, `prompt_version`, `generation_mode`, `source_clip_tag`, `status`, `narrative_job`, `felt_intent`, `already_happened`, `this_clip_only`, `reserved_for_later`, `planned_start_state`, `planned_end_state`, `observed_start_state`, `observed_end_state`, `continuity_locks`, `allowed_changes`, `continuity_breaks`, `accepted_deviations`, `transition_in`, `transition_out`, `open_motion_vectors`, `handoff_requirements`, and `extension_depth`.

`parent_clip_id` may be absent or `null` only for a topological root/re-anchor whose `sequence_index` is 1. Every later clip must carry an exact, non-empty parent ID; an empty or whitespace-only string is never a root. A `planned` child may retain a provisional graph edge only to a `planned`, `ready`, `accepted`, or `accepted_with_deviation` predecessor. That provisional edge is planning data, not permission to generate from unaccepted output. Before the child advances beyond `planned`, its parent must be `accepted` or `accepted_with_deviation` and must carry a non-empty `observed_end_state`. `generated`, `reviewed`, `repair`, and `rejected` parents are unusable; wait for acceptance, repair/re-anchor, or remove the edge. Rejected footage is never a parent in either the provisional or executable graph.

Every `accepted` or `accepted_with_deviation` clip, including a terminal clip with no children, must carry a non-empty object in `observed_end_state`. A rejected clip must set that field to `null`. Clip and parent IDs are limited to 256 characters so malformed records cannot turn a validation message into an unbounded output channel.

### Validation boundary

The JSON Schemas validate document structure and invariants that belong to one record. They cannot prove graph-wide facts: unique `clip_id` values, parent existence, self-parent rejection, parent-before-child ordering, cycle freedom, scene/beat references, or whether a referenced parent has an executable status and observed endpoint. Schema success is therefore not graph validation. Before a project state is accepted, handed off, installed as an example, or released, run all three checks: `schema_check.py`, `project_state_check.py`, and `continuity_chain_check.py`. The latter two are mandatory semantic validators, not optional lint.

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
SCENE MAP:
CURRENT SCENE:
CURRENT ACTUAL STATE:
OPEN MOTION:
COMPLETED BEATS:
NEXT CLIP JOB:
NEXT CLIP INTENT:
CONTINUITY LOCKS:
ALLOWED CHANGES:
RESERVED FUTURE BEATS:
EXTENSION DEPTH:
UNRESOLVED UNCERTAINTIES:

## State Lifecycle

The state is append-heavy by nature - every take review adds detail - so a thirty-clip project needs compaction rules, or by clip 25 every session begins by re-pasting a monster.

File convention (for agents with a persistent workspace such as Claude Code or Codex): keep `project-state.json` as the machine truth and regenerate the readable capsule from it; never hand-maintain the same fact in two places. Archive the take log to a separate `take-log.md` (or `take-history.jsonl`) instead of letting `take_history` grow inside the working state.

Compaction rules:

- A **completed scene compresses to one line** in the scene map and the capsule: scene id, one-line outcome, and the accepted final frame it handed off. Its clip-level detail stays in the JSON and the archived take log, not in the capsule.
- **Full detail is kept only for the current scene** plus the immediately previous accepted clip - everything a continuation prompt can actually use.
- **Superseded takes** (rejected, or accepted-then-replaced) move to the archive on scene close; canon keeps only each clip's accepted review.
- The **capsule stays under roughly 40 lines**. If it is longer, something that should have been compacted was not.

`state_revision` bumps on every canon change - an accepted take, an accepted deviation, a re-anchor, a scene close, or a lock change - and the capsule is regenerated at the same moment. A capsule whose revision does not match the JSON is stale; trust the JSON.
