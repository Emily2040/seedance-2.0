# Continuation Handoff

Use this reference for every continue, extend, next-shot, bridge, repair-tail, or re-anchor request. A successor prompt must be based on accepted source footage or an accepted final frame.

## Source Gate

Do not write a continuation prompt until these are known:

- project ID and current clip ID;
- parent clip ID;
- `scene_id`, and whether this continuation stays inside the scene or crosses a scene boundary;
- accepted source clip or accepted final frame;
- observed end state;
- next clip's `felt_intent` - what the viewer should feel or notice;
- next clip's explicit `directors_read_lane` and complete canonical `authoring_state`: the full narrative record with inherited `value_before` and exact `prompt_carriers`, or the two-line utility intent and refusal;
- completed beats;
- reserved future beats;
- continuity locks;
- exact reference registry;
- active surface or conservative surface profile.

If the source is missing, ask for the clip, final frame, or an exact visible-end description. Do not invent it.

## Observation Fast Path

The user should never be the state sensor **when the agent can actually see**. Attachment and inspection are different things: a host may accept a file and expose only its name. Before filling anything from "what is visible," confirm this client actually renders that media type — see Inspection Honesty in [agent-compatibility](agent-compatibility.md). If it does not, this fast path does not apply; take the **inspection unavailable** route below.

When the client does inspect the attachment, the AGENT fills the observation record from what is visible and asks only about what the attachment cannot show:

- **Final frame attached:** the agent reads pose, screen position, wardrobe and props, environment, lighting phase, and framing directly off the still, then asks at most three targeted questions - open motion at the cut, camera movement phase, and audio phase - because a still can never show them.
- **Full clip attached:** the agent reads everything including motion, camera phase, and (when audible) audio phase; usually nothing is left to ask.
- **Nothing attached:** only then fall back to asking the user to describe the visible end - and offer the extraction tool first.
- **Attached but not inspectable:** treat it as if nothing were attached. Say once that this client cannot open the file, ask the user to describe the visible end state, and record what they say as reported rather than seen — set `observation_confidence` to `low`, set `requires_user_confirmation` to `true`, and list the categories you could not verify in `uncertainties`. Never write a description you did not read off the pixels into `observed_end_state` at `medium` or `high` confidence; that is the one move that puts a fabricated state into canon.

For users working with this repository locally, `python scripts/extract_last_frame.py <take>` extracts the final frame of an accepted take (`--first-frame` for the opening; `--emit-record` prints this observation skeleton with the frame-readable and frame-blind categories marked). The helper refuses to replace an existing output image by default. Choose another `--output` path, or pass `--force` only for an intentional replacement whose metadata policy can be preserved. Windows retains the exact non-reparse output directory before decode and rejects parent recreation, junction redirection, normalization aliases, and all reserved device stems (including the superscript `COM¹`–`COM³` and `LPT¹`–`LPT³` forms). Force replacement initially requires the existing file to match the protected stage's owner, group, DACL, and mandatory label and to have no named streams or policy-bearing attributes. Its atomic commit backs up the actual boundary-time target, checks identity, bytes, security, streams, and attributes on both sides, and restores that exact backup if a late winner or metadata mutation appears. Linux requires effective `CAP_SYS_ADMIN`, an owner-controlled destination directory, successful privileged-namespace visibility and filesystem atomic-exchange probes, and refuses before decoding when those proofs fail; other POSIX runtimes refuse. A verified old-target descriptor stays open through decode, and the final transaction is checked on both sides and rolled back if the target changed after verification. Choosing a new output name is the portable, unprivileged path. In either publication mode FFmpeg streams decoded frames back to the helper rather than opening a mutable staging pathname; an independent bounded FFmpeg probe must decode the retained PNG before the helper writes it through an owned handle and atomically publishes the complete frame, so a failed run cannot expose a partial or undecodable final output. The extracted frame doubles as the continuation image reference, so one attachment pays for both the observation record and the next generation's anchor.

Do not interrogate the user across all record categories when an attachment is present: fill what is visible, state `observation_confidence`, and confirm rather than ask.

## Handoff Record

Record:

- observed start state;
- observed end state;
- open motion vector;
- camera phase;
- screen direction;
- character pose and gaze;
- prop ownership, position, and condition;
- location and persistent environment;
- lighting phase;
- ambience, completed dialogue, active dialogue, music phase, and SFX phase;
- observation confidence and uncertainties.
- the next clip's complete internal lane record: all canonical narrative fields, detail provenance, value before/after, and prompt carriers; or exactly utility intent and non-narrative refusal.

The authoring record and the observation record have different epistemic status. A take can show whether a carrier occurred and what visible consequence followed. It cannot reveal objective or contradiction as an observed fact. If accepted footage changes the dramatic turn, preserve the historical planned contract, make an explicit authorial decision in project state, reconcile the nearest narrative ancestor's `value_after` with the successor's `value_before` across any utility inserts, revise the next tactic and carriers, and only then compile the successor prompt.

## Seamless Versus Next Shot

Use `seamless_continuation` only when the next generation continues the same shot, geography, and open motion from accepted footage.

A scene boundary defaults to `intentional_next_shot`: open from canonical references and reset `extension_depth` to 0. Do not promise seamless continuation across a scene boundary.

Use `intentional_next_shot` when an editorial cut is appropriate. It may preserve story continuity, but it does not promise exact frame continuity.

Use `bridge_between_known_states` when a known start state must reach a known final state.

Use `repair_tail` when the final seconds of the parent clip failed.

Use `reanchor_after_drift` when extension depth or visible drift makes the chain unstable.

## Completed And Reserved Beats

Every continuation prompt must exclude completed beats and reserved future beats. If Clip 01 already exited the terminal, Clip 02 must not show the terminal exit again. If vehicle departure is reserved for Clip 03, Clip 02 must stop before departure. Carry the authoring state across the same handoff, but emit only its visible or audible `prompt_carriers`; internal labels and explanations never enter the generation prompt.

## Exact Reference Tags

Preserve tags byte-for-byte: `@Image1`, `@Image 1`, `@Image1`, `[Video 1]`, and interface equivalents must not be normalized, translated, renumbered, re-cased, or reformatted.

## Acceptance Rule

Accepted observed state overrides planned state. Rejected footage never becomes canon. Future prompts stay provisional until the previous accepted take is reviewed.
