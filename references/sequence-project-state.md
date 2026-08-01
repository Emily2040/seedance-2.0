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

## Dramatic Authoring State

Classify every clip with the canonical [Director's Read](directors-read.md) contract and record its `directors_read_lane` explicitly as `narrative` or `non_narrative`; never infer the lane from the free-form project `medium` label. Per-clip scope permits a utility insert and a character-led beat to coexist in one sequence without inventing psychology for the insert. Every explicit lane carries its complete canonical record in `authoring_state`; `felt_intent` alone is not enough.

A narrative record preserves `dramatic_function`, `turn`, `pov`, `power_shift`, `hidden_want_objective`, `obstacle_tactic`, `subtext_contradiction`, `visible_suppressed_behavior`, `non_transferable_detail`, `stock_solution_refused`, explicit `value_before` and `value_after`, and exact `prompt_carriers`. `non_transferable_detail_provenance` is `source_bound` only when `non_transferable_detail_source` names a concrete reference tag, URL, or `file:`, `ref:`, or `evidence:` locator that is registered in project state. When invention was invited, provenance is `authored_choice` and the source is `null`; an authored choice may never masquerade as observed or user-supplied fact.

A non-narrative record preserves exactly `utility_intent` and `non_narrative_refusal`. It does not carry narrative psychology, values, or prompt carriers. This is the canonical two-line utility handoff, not an empty lane marker.

This record is internal. Never paste field names, hidden psychology, or a prose explanation of subtext into Seedance. Compile only `prompt_carriers` plus the ordinary action, endpoint, camera, light, and sound instructions. A carrier must be filmable or audible: a hand stops under a lid, a paper tag is folded face-down, a reply comes after two unanswered rings. "She feels conflicted" is not a carrier. Carrier inclusion is checked only in rendered generation prose after YAML front matter, HTML comments and tags, recognized non-rendered or hidden HTML bodies, fenced/indented/inline/HTML code, valid reference definitions and continuation titles, inline-link destinations and titles, and alt text from image references that actually resolve are removed. Definitions inside code or raw HTML blocks do not resolve an outside reference. Undefined, escaped, or malformed Markdown remains rendered evidence. An element with inline `style` is ineligible evidence; because CSS cascade evaluation is out of scope, any raw `<style>` block or linked stylesheet makes the whole prompt untrusted. The checker proves literal carrier inclusion and recognized-label exclusion only; it does not understand negation, prove originality, or prove that a model enacted the carrier.

Within one lineage, a narrative clip's `value_before` must equal the `value_after` of its nearest narrative ancestor, walking across any non-narrative utility inserts. `value_before` and `value_after` must also differ after NFKC normalization, case folding, and removal of whitespace, punctuation, format controls, and Unicode default-ignorable code points; typography or an invisible character is not a dramatic turn. A utility insert may pause the dramatic thread but may not erase it. When accepted footage changes the turn, preserve the historical planned contract, update the accepted project clip's authored record, and reconcile the successor's value, tactic, and carriers before compiling again. Observed pixels can prove that a carrier occurred; they cannot prove an objective or contradiction. Those remain authored interpretations and require human or model-in-the-loop review.

Do not fabricate human psychology for a clip classified `non_narrative`, regardless of whether its medium is live action, animation, motion graphics, or something else. Preserve only its evidence-bearing utility intent and refusal. Conversely, a character-led motion-graphics or product film classified `narrative` still requires the full handoff.

## Required Project Fields

At minimum, a project state contains `schema_version`, `state_revision`, `project_id`, `project_mode`, `surface`, `clip_budget_sec`, `prompt_budget`, `story`, `world_bible`, `reference_registry`, `scenes`, `beats`, `clips`, `take_history`, `current_clip_id`, `canon_revision`, and `updated_at`. Every current strict sequence clip also declares `directors_read_lane`; the default/schema path remains additive for legacy files.

Story fields: `logline`, `story_promise`, `objective`, `initial_condition`, `final_outcome`, `target_duration_sec`, `tone`, and `medium`.

Scene fields: `scene_id`, `scene_index`, `narrative_function`, `arc_position`, `location`, `time_of_day`, `anchor_source`, `max_chain_depth`, `audio_plan`, `assigned_clip_ids`, `transition_out`, and `status`.

Beat fields: `beat_id`, `description`, `narrative_function`, `status`, `assigned_clip_id`, and `dependencies`.

Clip lineage fields: `clip_id`, `parent_clip_id`, `scene_id`, `sequence_index`, `prompt_version`, `generation_mode`, `source_clip_tag`, `status`, `narrative_job`, `felt_intent`, `directors_read_lane`, lane-complete `authoring_state`, any local `contract_authoring_state_snapshots`, `already_happened`, `this_clip_only`, `reserved_for_later`, `planned_start_state`, `planned_end_state`, `observed_start_state`, `observed_end_state`, `continuity_locks`, `allowed_changes`, `continuity_breaks`, `accepted_deviations`, `transition_in`, `transition_out`, `open_motion_vectors`, `handoff_requirements`, and `extension_depth`. Local snapshot membership is a consistency check, not an immutability proof; terminal contracts also require the protected provenance ledger below.

Within a scene, `sequence_index` is unique and every parent precedes its child. Parent chains may not self-parent or cycle. A root has `extension_depth: 0`; a same-scene child increments its parent's depth by exactly one, while a child that opens a later scene resets to 0. These are lineage invariants, not advisory metadata: an invalid chain must fail before physical or dramatic state is handed forward.

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

`take_history` is chronological per clip. Every clip in a post-review canonical
state (`accepted`, `accepted_with_deviation`, `repair`, or `rejected`) must have
a current history entry and exactly one sibling take-review record. The last
entry for that clip is authoritative: its `take_id` and verdict must match the
review, and the verdict must map to the clip's current status. A post-review
status without both records is invalid; an empty history is only valid while no
clip has reached one of those states. Earlier rejected attempts may remain as
history, but they do not override a later accepted take and do not need to stay
inline with their archived reviews.

Each inline history item is a closed object with `take_id`, `clip_id`, and
`verdict`, plus optional `evidence`. Project, clip, and take IDs in the state,
history, and sibling review are non-blank and at most 256 characters. Evidence
is at most 4096 characters, verdict is one of `accept`,
`accept_with_deviation`, `repair`, or `reject`, and the inline array is capped
at 4096 items. Archive older attempts before reaching that cap. Both semantic
validators use the same bounded reconciliation contract and index sibling
reviews once per directory. A review becomes authoritative only after its full
record-local schema contract passes. An authority candidate must be a regular,
non-link UTF-8 JSON file no larger than 1 MiB; symbolic links, Windows reparse
points, pipes, devices, sockets, and oversized files fail closed before parsing.
The captured review bytes for one directory are additionally capped at 16 MiB,
so the per-file and file-count limits cannot multiply into multi-gigabyte work.
Each review is opened once without following links where the platform supports
that flag. The exact handle is checked against every project-state file
identity, then read twice through the same bounded descriptor and accepted only
when identity, size, and bytes remain stable. A project state, symlink,
hardlink, or path-swap therefore cannot witness its own verdict, and divergent
captures fail closed instead of parsing a torn in-place rewrite.

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
NEXT CLIP DIRECTOR'S READ LANE:
NEXT CLIP AUTHORING STATE: INTERNAL - DO NOT COPY LABELS INTO THE GENERATION PROMPT
  DRAMATIC FUNCTION:
  TURN:
  POV:
  POWER SHIFT:
  HIDDEN WANT/OBJECTIVE:
  OBSTACLE/TACTIC:
  SUBTEXT/CONTRADICTION:
  VISIBLE SUPPRESSED BEHAVIOR:
  NON-TRANSFERABLE DETAIL:
  NON-TRANSFERABLE DETAIL PROVENANCE:
  NON-TRANSFERABLE DETAIL SOURCE:
  STOCK SOLUTION REFUSED:
  VALUE BEFORE:
  VALUE AFTER:
NEXT CLIP VISIBLE CARRIERS:
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
- The **capsule stays under roughly 50 lines** when the expanded authoring handoff is present. If it is longer, something that should have been compacted was not.

`directors_read_lane`, `authoring_state`, provenance, and contract snapshots remain absent-compatible only when the whole authoring layer is absent from a legacy file. Partial migration is invalid: presence of any one authoring key, even with a null, wrong-type, or invalid-lane value, triggers the lane-complete record and contract-provenance requirements. Strict sequence validation requires the lane even for a fully legacy record. Migrate a legacy narrative sequence by completing the canonical Director's Read and matching each narrative clip to its nearest narrative ancestor across utility inserts; do not invent the fields from old footage without an authorial review.

A `planned`, `ready`, `generated`, `reviewed`, or `repair` contract is current and its authoring state must exactly match the highest current project/canon revision. Only terminal `accepted`, `accepted_with_deviation`, or `rejected` contracts are historical plans: update status honestly, preserve the planned state and generation prompt, and keep observed reconciliation only in project state and take review. Every lane-bearing contract binds that state to `project_id`, `clip_id`, `canon_revision`, `state_revision`, and a canonical SHA-256 digest in `authoring_state_provenance`; the same record is registered under the project clip's `contract_authoring_state_snapshots`. The digest input is UTF-8 JSON for `authoring_state` with keys sorted, Unicode left literal, and compact `,`/`:` separators.

Local project and contract files can be rewritten together, so their mutual membership is not independent evidence. Every terminal lane-bearing **standalone contract artifact** must also match `validation/authoring-state-provenance-ledger.json`, an append-only ledger that binds status, authoring-state digest, canonical full-contract digest, and prompt digest to the exact project, clip, canon revision, and state revision. `entry_sequence` records append position; a later append is not required to sort by `project_id`. Every protected ledger entry must in turn be consumed by one and only one exact terminal contract-and-prompt pair; changing that pair back to a current status leaves an orphan and fails validation. The ledger revision and whole-ledger canonical digest are pinned in `scripts/project_state_check.py`; refreshing the ledger therefore requires an explicit reviewed pin change rather than a silent coordinated fixture rewrite. A historical contract keeps its planned revision and digest even when current project state has reconciled observed truth. Changing status, state, prompt, contract digest, and the local project snapshot together still fails the protected ledger. Never rewrite a historical contract to make a stale plan resemble observed canon.

That protection claim is deliberately artifact-scoped. A terminal clip record that exists only inside a project-state fixture is **not** independently protected by this contract ledger. To put such a record under the immutable-history claim, publish its complete standalone contract and generation prompt, then append their reviewed digests to the ledger and refresh the explicit pin. Project-only terminal examples remain useful lineage fixtures, but must not be described as ledger-protected contract history.

`state_revision` bumps on every canon change - an accepted take, an accepted deviation, a re-anchor, a scene close, or a lock change - and the capsule is regenerated at the same moment. A capsule whose revision does not match the JSON is stale; trust the JSON.

For one `project_id`, each `(canon_revision, state_revision)` pair identifies at most one snapshot. Two files with the same pair are ambiguous, and crossed pairs such as `(2, 1)` and `(1, 2)` are incomparable; validation fails instead of choosing whichever path sorts last. Project snapshots, standalone contracts, and take reviews are discovered by distinctive object shape as well as canonical filename, so renaming an exact duplicate does not evade revision or ledger checks.
