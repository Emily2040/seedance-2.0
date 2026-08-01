# Director's Read Contract

This is the lightweight, canonical story-judgment contract. Load this Director's Read before prompt compilation on every route, including interview, fast, short, sequence, and continuation routes. Do not recreate it from memory. The larger [directing engine](directing-engine.md) may deepen the camera, light, voice, and staging choices afterward, but it never replaces this gate.

The read is internal planning only. It may appear in a production brief or agent handoff when useful, but its labels and abstractions do not belong in the final generation prompt. The final prompt receives only visible or audible carriers.

## Classify First

### Narrative lane

Use the narrative lane when the brief asks for any of these:

- a person, character, creature, or performer pursuing, resisting, choosing, concealing, reacting, relating, or changing;
- a story beat, dramatic turn, performance beat, dialogue, subtext, emotional shift, power shift, or deliberate audience alignment;
- a product, fashion, music, dance, action, or brand shot in which a performer has an objective, obstacle, choice, relationship, or change.

A silent scene can be narrative. A product shot can be narrative. The test is requested agency, performance, or dramatic change - not dialogue, genre, or whether a product is present.

### Non-narrative lane

Use the non-narrative lane for a packshot, material or light study, functional demonstration, camera or motion transfer, assembly instruction, abstract or VFX transformation, ambient environment, process visualization, or product shot with no requested agency, performance, relationship, or story turn.

A visible human or hand does not by itself create a narrative. If the person only demonstrates a function and the brief asks for no objective, resistance, choice, reaction, or expressive performance, keep the work in the non-narrative lane. Do not fabricate hidden wants, power struggles, subtext, character psychology, or conflict to make utility footage seem dramatic.

For the non-narrative lane, write only:

- `utility intent`: the concrete viewer-facing job of the shot;
- `non-narrative refusal`: the invented drama or anthropomorphism that must not be added.

Then proceed with the visible beat, camera, light, material behavior, sound, references, and constraints. Example: `utility intent: prove the engraved label stays legible as condensation forms; non-narrative refusal: no invented character, rivalry, seduction, or emotional reveal.`

If the lane is genuinely ambiguous and the answer would change the prompt, ask one plain question: `Is this only a clean demonstration, or should the person be playing a choice or feeling?` Otherwise use the evidence in the brief. Do not upgrade a utility shot into drama merely to fill fields.

## Mandatory Narrative Record

For every narrative, story, or performance brief, complete all ten fields before drafting or compressing the generation prompt. Do not leave blanks and do not substitute a generic mood word.

- `dramatic function`: what this beat earns - introduce, deepen, turn, test, reveal, decide, or pay off.
- `turn`: the single before-to-after value change visible in the beat.
- `POV`: whose experience organizes what the viewer sees, hears, and learns.
- `power shift`: who controls the beat at the start, who controls it at the end, and what changes that balance.
- `hidden want/objective`: what the focal subject is trying to get, protect, avoid, prove, or conceal. For a characterless story beat, use the scene's dramatic objective; do not invent psychology for an object or environment.
- `obstacle/tactic`: what blocks the objective, followed by the playable action used against it.
- `subtext/contradiction`: the gap between the stated surface and the underlying action or want.
- `visible suppressed behavior`: one small filmable action that shows an impulse being contained, redirected, or leaked.
- `non-transferable detail`: one brief- or reference-bound object, ritual, phrase, location fact, costume fact, sound, or behavior that another generic story could not inherit unchanged.
- `stock solution refused`: the genre's easiest default move that this beat explicitly will not use.

The non-transferable detail should come from supplied material when available. An authored fictional detail is allowed when the user invited invention, but label it as an authored choice in the internal read; never present it as observed reference evidence, local fact, or user-supplied canon. When the read is persisted as sequence state, use `non_transferable_detail_provenance: source_bound` only with a concrete `non_transferable_detail_source` locator registered in project state. Use `authored_choice` with a null source so later agents cannot lose or counterfeit the boundary during compression.

The stock refusal must name a real shortcut, not say only `avoid cliches`. Examples: no tearful close-up and score swell for grief; no speed ramp and impact montage for sport; no floating particles and lens flare for wonder; no orbiting camera and anonymous luxury surface for a product hero. Replace the refused move with a specific behavior, object, timing choice, or shot relationship.

## Compile to Carriers

Translate every useful abstraction into something the model can render or play:

| Internal read | Prompt carrier |
|---|---|
| POV | shot position, information withheld or revealed, eyeline, sound perspective |
| power shift | height, frame share, distance, who moves first, who yields space |
| hidden want/objective | a task, prop action, approach, retreat, delay, or repeated attempt |
| obstacle/tactic | visible interference followed by one playable response |
| subtext/contradiction | words against body, smile against grip, agreement against retreat, silence against urgent action |
| visible suppressed behavior | one timed gesture the camera can hold long enough to read |
| turn | a legible before/after state and camera endpoint |
| non-transferable detail | the exact object, ritual, sound, or environment fact preserved in the shot |
| stock solution refused | a physical exclusion only when needed, paired with the chosen replacement |

Do not paste `dramatic function`, `POV`, `power shift`, `hidden want`, `subtext`, or other read labels into the final generation prompt. Do not tell Seedance that a character `feels conflicted` when the conflict can be carried by behavior. At minimum, the final prompt must preserve the turn, the visible suppressed behavior, and the non-transferable detail as filmable or audible evidence. The deterministic compiler check proves literal carrier inclusion only; prompt-polarity review and take review decide whether that evidence is actually requested and enacted.

## Narrative Example: Internal Read to Prompt

Brief: `A hotel night clerk sees her missing brother on a security monitor but must keep serving the waiting guest.`

- `dramatic function`: turn routine service into a private recognition crisis.
- `turn`: professional control to nearly exposed urgency.
- `POV`: the clerk; the monitor matters only when she recognizes the face.
- `power shift`: the waiting guest controls her outward time, then the monitor controls her attention.
- `hidden want/objective`: replay the footage without revealing why it matters.
- `obstacle/tactic`: the guest is waiting; she keeps stamping the receipt while reaching toward replay.
- `subtext/contradiction`: her polite service voice says nothing is wrong while her body abandons the task.
- `visible suppressed behavior`: her finger hovers over replay, then she straightens a brass Room 214 key tag instead.
- `non-transferable detail`: authored choice - the worn brass Room 214 key tag catches against the receipt stamp.
- `stock solution refused`: no tearful close-up, flashback, or swelling grief score.

Compiled carrier example: `Stay at the night clerk's side of the counter as she stamps a receipt for the waiting guest. A familiar face crosses the small security monitor behind the register; her stamping stops mid-impact, one finger reaches toward replay, then she pulls it back and carefully straightens the worn brass Room 214 key tag. Hold the guest soft in the foreground, let the monitor hum and the stamp click carry the silence, and end on her hand still pinning the tag flat.`

The compiled prompt never names the hidden want, subtext, power shift, or emotion. The camera, interrupted task, withheld reach, exact prop, sound, and endpoint carry them.

## Non-Narrative Example

Brief: `Macro turntable shot of a perfume bottle while condensation forms; preserve the label.`

- `utility intent`: prove material texture and label legibility through the condensation change.
- `non-narrative refusal`: no invented character, desire, rivalry, seduction, or dramatic power shift; do not anthropomorphize the bottle.

Proceed directly to a controlled rotation, condensation timing, macro endpoint, motivated hero light, glass sound cue if useful, and exact label-preservation constraints. No Director's Read fields are manufactured for this lane.

## Handoff Rule

Every agent and every route uses this exact reference. A handoff may carry either the completed ten-field narrative record or the two-line non-narrative record. It may not say `handled from memory`, `use good judgment`, or `make it cinematic` in place of the record. Before another agent compiles or compresses a prompt, it verifies that the correct lane record is present and that the final prose contains carriers rather than internal labels.

This shared contract standardizes inputs and review criteria; it does not guarantee byte-identical classification or prose from separate language-model agents. Any claim about live cross-agent consistency requires a model-in-the-loop benchmark, not only these static routing checks.
