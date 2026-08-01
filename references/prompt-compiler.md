# Prompt Compiler

The compiler turns internal project state into one natural-language Seedance prompt for the current clip only. JSON or YAML can organize planning, but the final prompt sent to Seedance stays readable prose unless the user explicitly asks for structured output.

Before compilation, load the [Director's Read](directors-read.md). Narrative, story, and performance clips require the completed ten-field internal read; non-narrative utility, product-only, abstract, VFX, or ambient clips require the two-line utility intent and refusal. This is a planning gate, not a new project-state field or schema.

## Inputs

- project state;
- current clip contract;
- surface prompt profile;
- reference transfer contract;
- observed source state for continuations;
- completed and reserved beats;
- continuity locks and allowed changes;
- completed Director's Read or non-narrative lane record;
- prompt budget.

## Compile Order

1. Lineage: name `project_id`, `clip_id`, and parent in the user-facing contract or capsule; omit them from the final prompt when they would waste prompt budget.
2. Source role: identify the active reference tags and what each controls.
3. Actual opening state: use observed footage for continuations and planned state only for first clips. When the source clip or final frame is attached as a reference, name it by tag and state only what the source cannot carry.
4. Current clip action: one narrative job with an endpoint.
5. Director's Read carriers: for narrative work, compile the turn, visible suppressed behavior, non-transferable detail, and chosen replacement for the refused stock solution into blocking, action, prop use, camera, light, dialogue contradiction, silence, or sound. For non-narrative work, serve the utility intent and do not fabricate psychology.
6. Felt intent: the clip's one-line `felt_intent` - what the viewer should feel or notice - is the directing engine's intention made persistent in state. It never ships to Seedance as an abstract emotion word; it compiles as the specific camera, light, performance, and sound choices that carry it.
7. Camera and motion phase: include inherited vectors when continuity matters.
8. Light, environment, style, and audio: include only state-critical or intent-critical clauses.
9. Exclusions: completed beats and reserved future beats.
10. Endpoint: the completed state this clip must reach.

## Source-Carries-State Rule

When an accepted source is attached as a reference, the source carries the state and the text carries the delta. Do not re-describe in prose what the attached source already shows: prose restatement spends budget on information the model already has, and where the words disagree with the pixels, the prose becomes a drift instruction.

- Accepted clip attached as a video reference: the clip carries static and dynamic state. Text carries the source role by exact tag, the current action and endpoint, exclusions, and only the continuity locks at known drift risk.
- Accepted final frame attached as an image reference: the frame carries static state only. Text must still carry what a still cannot show - open motion vectors, camera movement phase, and audio phase - then the current action, endpoint, and exclusions.
- No visual source attached: write the observed opening state in prose, as for a cross-session continuation where the footage is unavailable.

## Natural-Language Prompt Rules

Do not emit internal JSON to Seedance. Do not include all future clips. Do not describe a planned ending as if it happened. Do not replay completed actions. Do not perform reserved later actions. Do not invent deterministic guarantees. Do not re-describe content an attached source reference already shows.

Do not emit Director's Read labels or abstract internal states such as `power shift`, `hidden want`, or `subtext`. Emit only visible or audible carriers. A non-narrative prompt must not gain invented desire, rivalry, conflict, or character psychology during compilation.

Use clip-scope language:

- "Begin with..." for observed opening state.
- "Continue the same..." only when source footage exists.
- "This clip only..." for the current narrative job.
- "Stop when..." for endpoint control.
- "Do not yet..." for reserved future beats.

## Compression

When the prompt must shrink, preserve in this order:

1. Exact reference tags and role boundaries.
2. Actual opening state the attached source cannot carry.
3. Current action and endpoint.
4. Felt-intent carriers: the specific light, performance, and sound clauses that make the viewer feel what this clip exists to make them feel.
5. Continuity locks.
6. Completed beat exclusions.
7. Reserved beat exclusions.
8. Camera or open motion vector.
9. Audio phase.

Delete generic style boosters, duplicate adjectives, future story summary, background visible in references, secondary actions, and speculative internal notes first. When a visual source is attached, opening-state prose that repeats the source is deleted before anything else on this list. Felt-intent carriers are not "speculative emotional labels": the label never ships, but its carriers ship as concrete visible choices, and they outrank locks and exclusions because a continuity-correct, affect-flat clip is a failed clip that costs a retake anyway.
