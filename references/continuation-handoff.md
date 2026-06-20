# Continuation Handoff

Use this reference for every continue, extend, next-shot, bridge, repair-tail, or re-anchor request. A successor prompt must be based on accepted source footage or an accepted final frame.

## Source Gate

Do not write a continuation prompt until these are known:

- project ID and current clip ID;
- parent clip ID;
- accepted source clip or accepted final frame;
- observed end state;
- completed beats;
- reserved future beats;
- continuity locks;
- exact reference registry;
- active surface or conservative surface profile.

If the source is missing, ask for the clip, final frame, or an exact visible-end description. Do not invent it.

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

## Seamless Versus Next Shot

Use `seamless_continuation` only when the next generation continues the same shot, geography, and open motion from accepted footage.

Use `intentional_next_shot` when an editorial cut is appropriate. It may preserve story continuity, but it does not promise exact frame continuity.

Use `bridge_between_known_states` when a known start state must reach a known final state.

Use `repair_tail` when the final seconds of the parent clip failed.

Use `reanchor_after_drift` when extension depth or visible drift makes the chain unstable.

## Completed And Reserved Beats

Every continuation prompt must exclude completed beats and reserved future beats. If Clip 01 already exited the terminal, Clip 02 must not show the terminal exit again. If vehicle departure is reserved for Clip 03, Clip 02 must stop before departure.

## Exact Reference Tags

Preserve tags byte-for-byte: `@Image1`, `@Image 1`, `[Image1]`, `[Video 1]`, and interface equivalents must not be normalized, translated, renumbered, re-cased, or reformatted.

## Acceptance Rule

Accepted observed state overrides planned state. Rejected footage never becomes canon. Future prompts stay provisional until the previous accepted take is reviewed.
