# Prompt Compiler

The compiler turns internal project state into one natural-language Seedance prompt for the current clip only. JSON or YAML can organize planning, but the final prompt sent to Seedance stays readable prose unless the user explicitly asks for structured output.

Before compilation, load the [Director's Read](directors-read.md). Narrative, story, and performance clips persist the complete canonical internal read, evidence-bearing detail provenance, explicit value endpoints, and prompt carriers in `authoring_state`. `source_bound` requires a registered exact source locator; `authored_choice` requires a null source. Non-narrative utility, product-only, abstract, VFX, or ambient clips persist exactly the two-line utility intent and refusal. The handoff never substitutes a reduced taxonomy for the canonical record.

## Inputs

- project state;
- current clip contract;
- current clip lane-complete internal `authoring_state`;
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
5. Director's Read carriers: for narrative work, verify the full persisted record and compile the turn, visible suppressed behavior, non-transferable detail, and chosen replacement for the refused stock solution into blocking, action, prop use, camera, light, dialogue contradiction, silence, or sound. Emit exact `prompt_carriers`, never labels or explanations. For non-narrative work, serve the persisted utility intent while honoring its refusal; do not fabricate psychology.
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

Do not emit internal JSON or any canonical/internal label to Seedance: this includes dramatic function, turn, POV, power shift, hidden want/objective, obstacle/tactic, subtext/contradiction, visible suppressed behavior, non-transferable detail, provenance, or source, stock solution refused, value endpoints, prompt carriers, utility intent, and non-narrative refusal. Do not include all future clips. Do not describe a planned ending as if it happened. Do not replay completed actions. Do not perform reserved later actions. Do not invent deterministic guarantees. Do not re-describe content an attached source reference already shows.

Do not emit Director's Read labels or abstract internal states such as `power shift`, `hidden want`, or `subtext`. Punctuation, symbol, spacing, acronym, and heading variants remain labels: `POWER.SHIFT:`, `VALUE|BEFORE:`, `P.O.V.:`, and a bare `POWER SHIFT` heading are not escape hatches. Emit only visible or audible carriers. A non-narrative prompt must not gain invented desire, rivalry, conflict, or character psychology during compilation.

`prompt_carriers` are an audit boundary, not magic words. A deterministic check can prove only literal inclusion of the stored string in rendered generation prose and exclusion of recognized internal labels. It removes YAML front matter closed by either `---` or `...`; HTML comments, tags, non-rendered containers, image attributes, and bodies carrying any `style`, `hidden`, or `aria-hidden=true` attribute; fenced, indented, inline, and HTML code contexts; valid Markdown reference definitions and their continuation titles (including block/list containers), resolved reference-image alt metadata, and inline-link destinations or titles. Definitions inside fenced code or raw HTML blocks do not resolve an outside image. Because CSS cascade evaluation is out of scope, any raw `<style>` element or stylesheet link makes the whole prompt ineligible as carrier evidence. Metadata, code, hidden bodies, attributes, link titles, or non-prose Markdown therefore cannot counterfeit carrier inclusion. It recognizes assignment, explanation, heading, Unicode-arrow, Markdown-wrapper, HTML-entity, and any-table-cell forms of internal labels, including labels hidden in code. It cannot understand whether a carrier was negated or subordinated by nearby rendered instructions, and it cannot prove originality, dramatic truth, or faithful model execution. Review prompt polarity before generation; then review the generated take and reconcile the actual visible consequence.

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
4. Sequence `prompt_carriers`: the visible or audible behavior, object, and consequence that keep the Director's Read specific across handoffs.
5. Felt-intent carriers: the specific light, performance, and sound clauses that make the viewer feel what this clip exists to make them feel.
6. Continuity locks.
7. Completed beat exclusions.
8. Reserved beat exclusions.
9. Camera or open motion vector.
10. Audio phase.

Delete generic style boosters, duplicate adjectives, future story summary, background visible in references, secondary actions, and speculative internal notes first. When a visual source is attached, opening-state prose that repeats the source is deleted before anything else on this list. Felt-intent carriers are not "speculative emotional labels": the label never ships, but its carriers ship as concrete visible choices, and they outrank locks and exclusions because a continuity-correct, affect-flat clip is a failed clip that costs a retake anyway.
