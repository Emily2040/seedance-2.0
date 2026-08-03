# Sequence Worked Trace

One project, walked end to end through the full loop - plan, compile, generate, observe, deviate, reconcile, hit the chain cap, re-anchor, break for the night, and resume. The machine half of this trace already lives in `examples/`; this is the prose half that shows how the pieces are actually used. Field schemas without a trace get re-interpreted on every run; this file is the interpretation.

The project: **seq_airport_arrival** (`examples/sequence-airport-arrival/`) - a traveler exits the terminal, enters a waiting car, and the car departs. Deviation-handling details borrow the second fixture, **sequence-observed-deviation** (`examples/sequence-observed-deviation/`), which records a real unexpected-completed-beat event.

## 0 - Plan globally

The idea ("my character lands and is driven away") is bigger than one generation, so the Sequence Gate classifies it `sequence_project`. Before Clip 01 exists, the plan fixes: the story promise and final outcome, beats grouped into **scenes**, and per clip a `narrative_job`, a `felt_intent`, and a completed endpoint.

Here everything happens at one location in one time envelope, so the scene map is a single scene: `scene_01`, arc position `release`, canonical anchor `@Image 1` (the traveler's identity - note the internal space in the tag; it is preserved byte-for-byte forever), `max_chain_depth: 2`, and an audio plan of curb ambience and sync SFX per clip with score unified in post. Three clips are assigned: exit terminal and approach the car (Clip 01), enter and close the door (Clip 02), the car departs (Clip 03). See `project-state.json` - `scenes`, `beats`, `clips`.

Only Clip 01 is compiled. Clips 02-03 stay provisional intent cards, because their opening states do not exist yet.

## 1 - Compile Clip 01

The contract (`clip-01-contract.json`) carries the job ("Exit terminal and approach the open rear car door"), the felt intent ("the quiet relief of arrival"), the reserved beats (entering the car, departure), and the locks. The compiler (see [prompt-compiler](prompt-compiler.md)) emits one natural-language prompt (`clip-01-prompt.md`) - T2V, since nothing exists yet - and before generation the intent echo is stated in one line: *this clip exists so the viewer feels the relief of arrival.* No internal JSON ships to Seedance.

## 2 - Observe, and accept a deviation

The take comes back. The user attaches the clip or its final frame (locally: `python scripts/extract_last_frame.py take.mp4`), and the **agent** fills the observation record from the pixels - the Observation Fast Path in [continuation-handoff](continuation-handoff.md) - asking only what a still cannot show. The review (`clip-01-take-review.json`) records the honest result: the traveler is **two steps short of the open door**, still walking, left-to-right. The plan said "reaches the door"; the pixels disagree.

Verdict: `accept_with_deviation`. Reconciliation (see [sequence-project-state](sequence-project-state.md)) updates canon: the deviation is recorded, the observed end state overrides the planned one, and Clip 02's contract is recompiled to open **two steps out, mid-stride** - it does not replay the terminal exit, and it does not pretend she reached the door. Rejected takes, by contrast, would change nothing: rejected footage never becomes canon or a parent source.

## 3 - Continue from what actually happened

Clip 02 (`clip-02-continuation-contract.json`) is a `seamless_continuation` inside `scene_01`: parent `clip_01`, `extension_depth: 1`, sourced from the accepted take attached as `[Video 1]`. The **source-carries-state rule** applies: the video reference carries the opening state, so the prompt text carries only the delta - finish the approach, enter, close the door, plus the felt intent's carriers (the door shutting as an exhale) and the reserved-beat exclusion (no departure yet). Prose that re-describes what `[Video 1]` already shows would be budget spent turning disagreement into drift.

## 4 - The other way plans break: a beat completes early

The second fixture shows the mirror-image deviation. A rooftop courier take planned only "unlock the case" - but the accepted footage shows the case unlocked **and opened** (`take-review.json`: "case opened one clip earlier than planned"). Reconciliation removes the now-completed `beat_open_case` from the future (compare `project-state-before.json` with `project-state-after.json`: three planned clips become two, and the next clip's job becomes "Light the already visible signal device"). The rule in both directions is the same: **accepted observed state overrides planned state** - whether the take fell short or ran ahead.

## 5 - The chain cap and the scene boundary

Clip 03 chains from Clip 02's accepted footage: `extension_depth: 2` - exactly at `scene_01`'s `max_chain_depth`. That is legal, and it is also the end of the chain: a third output-sourced generation would exceed the cap, and the validator (`scripts/project_state_check.py`) fails it with instructions to open from canonical references instead. This is scheduled re-anchoring: identity decays along output-sourced chains, so the reset is routine, planned at the scene boundary - an intentional cut, opened from `@Image 1`, depth back to 0 - not an emergency repair after drift is visible. If drift appears **before** the cap, that is an immediate `reanchor_after_drift` instead.

## 6 - Break for the night, resume tomorrow

Sessions end; canon must not. The Project State Capsule (template in [sequence-project-state](sequence-project-state.md)) carries the whole project in under ~40 lines: scene map (completed scenes compressed to one line each), current scene, current actual state, open motion, completed beats, next clip job **and intent**, locks, reserved beats, extension depth, uncertainties. A new session pastes the capsule and continues from the recorded actual state - no hidden memory is assumed, and the machine truth (`project-state.json`, per the State Lifecycle) regenerates the capsule whenever `state_revision` bumps.

## 7 - Close out

Clip 03 ends the scene and the story: the car departs, the final outcome is met, the scene closes (its line in the capsule compresses to its outcome), and the take log archives. Total user effort per cycle after the plan: attach the take, confirm the agent's observation record, approve the intent echo, generate. The loop's guarantees did the rest: nothing replayed, nothing leaked early, nothing invented, and the story the user accepted is the story the state remembers.
