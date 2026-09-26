---
name: seedance-prompt
description: "This skill should be used when the user asks to write, improve, translate, compress, or debug a Seedance 2.0 video prompt; mentions T2V, I2V, V2V, R2V, camera direction, prompt quality, or provides reference assets for a production-ready prompt."
license: MIT
user-invocable: true
tags:
  - prompt-engineering
  - video-generation
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

# seedance-prompt

Before producing prompt text, a prompt-ready block, a rewrite, an example, or a compiled clip, load the [Director's Read](../../references/directors-read.md), classify the brief, and complete its canonical narrative or non-narrative record. Translate that record into visible or audible carriers and keep its internal labels out of final generation prose.

Build production-ready Seedance prompts from clear concepts or supplied reference assets. Treat the prompt as a short shooting brief: it must say what changes on screen, what the camera does, what the light and sound contribute, and what must stay stable. Keep final prompts under the platform prompt budget and remove filler before delivery.

Load the [Director's Read](../../references/directors-read.md) before any drafting or compression, [quick-ref](../../references/quick-ref.md) for the checklist, [reference-workflow](../../references/reference-workflow.md) for multimodal references, [i2v-guide](../../references/i2v-guide.md) for image-to-video, [first-last-frame-guide](../../references/first-last-frame-guide.md) for first/last-frame work, [examples-by-mode](../../references/examples-by-mode.md) when examples are useful, [shot-list-continuity](../../references/shot-list-continuity.md) for multi-shot professional plans, [multishot-grammar](../../references/multishot-grammar.md) for shot order, the continuous-versus-storyboard shape rule, the load-per-beat ladder, and cut placement inside one generation, and [multilingual-community-examples](../../references/multilingual-community-examples.md) for Chinese/Russian/Japanese/Korean/Spanish or mixed-language prompts. When sequence state is present, load [prompt-compiler](../../references/prompt-compiler.md) and compile only the current clip contract.

## Intent

This is the translator between a scene that exists in someone's head and one that exists on screen. The user has already imagined it; the job is to lose as little as possible in transit. Success is a first generation close enough that they can react instead of explain. Each revision inherits everything the story has already decided and changes only what the reaction asked for - a draft is a conversation, not a restart.

## Director Formula

Before filling slots, run the [Director's Read](../../references/directors-read.md) gate. A brief with a dramatic story turn must have all ten canonical narrative fields completed. Observation/performance without that turn and utility briefs use the two-line non-narrative intent and refusal, with no fabricated psychology. Preserve expressive movement, rhythm, or delight when requested. For narrative work, name a single intention from the read and let it choose camera, lighting, blocking, performance, and sound together. Load [directing-engine](../../references/directing-engine.md) when the setup needs its deeper instrument and voice logic. The formula below is the container for a coherent setup, not a checklist of independent decorations; if a project voice is already set, keep this shot inside it.

The Director's Read is internal planning, not prompt copy. For narrative work, compile its turn, visible suppressed behavior, and non-transferable detail into visible or audible carriers. For observation/performance or utility in the non-narrative lane, carry the requested action, rhythm, information, or sensory change without inventing those dramatic fields. Do not paste labels such as `POV`, `power shift`, `hidden want`, or `subtext` into the generation prompt, and do not ship an abstract feeling where blocking, gesture, prop use, camera endpoint, motivated light, dialogue contradiction, silence, or a sound cue can carry it.

Use `Subject + Action + Scene + Camera + Lighting/Style + Audio + Constraints`. Put the subject and primary action first because early clauses set the shot hierarchy. Do not force every slot if a reference asset already shows the information; for I2V, describe only the motion, camera, timing, transformation, audio, and preservation constraints that the still image cannot show.

| Slot | Use for | Prompt-ready pattern |
|---|---|---|
| Subject | The anchor the model must track. | `Original ceramic perfume bottle on black acrylic, label preserved exactly` |
| Action | The visible change. | `condensation beads form and slide down the glass over five seconds` |
| Scene | Only what is not already in references. | `quiet rain-lit kitchen counter, shallow depth of field` |
| Camera | One primary move with endpoint. | `slow dolly-in from medium product shot to macro label detail` |
| Light and style | Physical light plus safe visual language. | `warm practical key from frame left, cool blue rim, clean commercial realism` |
| Audio | Ambient bed, SFX, dialogue, or silence. | `Sound: low room tone, soft glass chime on final frame` |
| Constraints | Preservation and exclusions. | `do not alter logo, shape, label, or cap geometry` |

## Mode Gate

Choose the mode before drafting. **T2V** needs subject, action, scene, camera, light, style, and constraints because nothing is visible yet. **I2V** starts from `@Image1` and adds only motion, time, camera, lighting transition, audio, and preservation. **V2V** should map `@Video1` to source clip, camera move, action rhythm, blocking, edit target, or extension anchor rather than accidentally transferring identity. **R2V** must list every reference role and state what must not transfer. **FLF2V** uses `@Image1` as first frame and `@Image2` as last frame, then describes only the continuous transition.

| Mode | Drafting priority | Common mistake | Repair |
|---|---|---|---|
| T2V | Build the whole shot in compact layers. | Too many events in one clip. | Keep one visible beat and one endpoint. |
| I2V | Preserve visible identity; add motion. | Re-describing the image until the product or face drifts. | Say `preserve @Image1 exactly`; add only dynamic changes. |
| V2V | Transfer motion, camera, or timing. | Copying unauthorized likeness or scene details. | Use owned/licensed/authorized references and restrict transfer role. |
| R2V | Assign separate roles to each asset. | One reference asked to control identity, pose, scene, and style. | Split roles or prioritize the most important role. |
| FLF2V | Move from first frame to last frame. | Treating the last frame as vague mood instead of endpoint. | State `@Image2` is the final visual target. |
| Edit | Preserve the source clip while changing one layer. | Rewriting the whole scene and losing continuity. | Say `@Video1 is the source clip; change only...` |
| Extend | Continue from accepted source footage only. | Starting from a planned ending or inventing the clip state. | Route to [seedance-continuation](../seedance-continuation/SKILL.md) and use the observed end state. |

## Time Structure

Seedance 2.0 keys on shot order, not seconds (official guidance recorded 2026-09-26; sources and the full rule in [multishot-grammar](../../references/multishot-grammar.md)). Classify the shape first. One scene with one continuous action or state change is **continuous** and compiles as one paragraph with no shot labels, whatever its duration. Several events, a location change, a reveal that needs a cut, or a comparison is a **storyboard** and compiles as numbered shots in event order, each block ordered camera move or cut, action and expression, space change, audio, with the cut written in words. Never write absolute seconds such as 0–3 s inside a shot block on 2.0; duration is the surface parameter, and a felt length is written as behaviour.

For a storyboard clip, score the load (a camera move, each spoken line, extra people, contact that must land, a location change) and place the requested shot count on the ladder: **Safe**, **Stretch**, or **Ambitious**. When the shot count is open, present up to three rungs with the trade-off in one line each, recommend one (Safe on a first attempt or a last credit, Stretch when the user has room to iterate), say once that the thresholds are this skill's heuristics and that no official shot ceiling exists, and write one finished prompt at the recommended or chosen rung; other rungs are written on request, and "choose for me" means draft the recommendation. When the user has fixed the count, write it and state its rung in one line. Ambitious is never called broken; two shorter generations are offered as the better spend. A request for timestamps on the newer model line stays inside the boundary in [api-status](../../references/api-status.md): keep the craft, withhold the numbers.

## Sequence Boundary

The generic prompt skill must not independently invent continuation state. If the user asks to continue, extend, make part two, or use a previous clip, route to [seedance-continuation](../seedance-continuation/SKILL.md) unless the accepted clip/final frame and observed end state are already present in the sequence state.

For sequence prompts, preserve `project_id`, `clip_id`, `parent_clip_id`, continuity locks, exact reference tags, the actual opening state, completed beat exclusions, and reserved future beats. The final prompt remains natural language and covers only the current clip.

## Prompt Build Process

First, load the [Director's Read](../../references/directors-read.md), classify the brief, and complete the correct lane record before prompt compilation. For a narrative lane, identify the single visible beat and the intention it serves, then map the read to carriers; for a non-narrative lane, keep the concrete utility intent and refuse invented drama. Next, assign reference roles before adding adjectives. For a storyboard, or any clip with more than one person, build the [shot table](../../references/shot-table.md) before any prose: the floor plan in words, then one row per shot with the camera's side, who is in frame and where and facing, the eye-line, the one action, everyone else's idle business, the light and the last frame; run the paper render on it, and only then write the draft, rendering each row into one block in the director formula order. A table with a blank or default cell is not ready to become prose. For a continuous single-subject clip, write a compact first draft in the director formula order. Finally, run a self-check and, when loaded, the directing coherence test from [directing-engine](../../references/directing-engine.md): one main subject, one main action, one motivated main camera move, physically motivated lighting, performance written as a visible gesture rather than an emotion word, assigned character tags, sound intent, and no hollow boosters.

## Compression Rules

When the prompt is too long, cut in this order: duplicate style adjectives, generic quality words, background details visible in references, secondary camera moves, secondary actions, and speculative emotional labels. Keep preservation constraints, action timing, and role maps. If a user requests a bilingual or mixed-language prompt, use language mixing only for clarity: reference roles, dialogue language, technical camera terms, and safe production constraints. Do not use another language to hide unsafe intent.

## Pre-Delivery Screen

Before the prompt is handed over, run the [moderation pre-screen](../../references/moderation-prescreen.md). List every noun and verb that names a weapon, an injury, a crime, a minor together with danger, a legal, police or medical setting or document, a substance, a horror figure, or a real identity; remove it, move it off frame, or replace it with its consequence; re-read for stacking; keep the exact dialogue; state the change in one line. The turn, the suppressed behaviour and the non-transferable detail never depend on the cue word, so the drama survives the rewrite. Prohibited content is refused through [seedance-filter](../seedance-filter/SKILL.md), never reworded.

Before the screen, run the eight-point check in [direct-for-the-model](../../references/direct-for-the-model.md): every reaction a plain feeling plus one physical anchor, never an idiom and never a bare list of muscles; one action per shot with everyone else kept alive in their idle business, never frozen; a lock line at the end of every shot repeating the light, each principal, where they stand, which way they face and which side the camera is on, with reactions written as reverses and every crossing of the room given its own shot; prop actions written as a hand, not a verb; an ending the frame can contain or a move or cut to reach it; every line given a voice and eyes rather than "flat". Two physical rules belong to the same pass. Never write an involuntary outcome as the endpoint (a coat caught in a door, a slip, a spill): the model stages it as a deliberate act by the character, so write the deliberate action or leave the consequence off screen. Keep spectacle in what the model renders well, weather, light, cloth, dust, water, crowds and fire at a distance, drawn effects in 2D, with any contact simple and singular. For a short-drama hook, an action beat or a showcase clip, apply the Stakes and Peak section of [directing-engine](../../references/directing-engine.md): stakes in frame, a force against the character, escalation inside the clip, one visual peak, the premise spoken or shown by shot two, and coverage of four or five shots with a reaction shot counted at half a beat.

## Output Contract

Return:

1. Mode: T2V, I2V, V2V, R2V, FLF2V, edit, or extend.
2. Reference role map, if any.
3. Final prompt under the verified active-surface prompt budget.
4. For a storyboard clip with an open shot count: the ladder (up to three rungs, one trade-off line each), the recommendation, and the evidence-tier sentence; the final prompt is the recommended or chosen rung.
5. For a storyboard or multi-person clip: the shot table the prompt was rendered from (floor plan, then one row per shot: camera side, in frame and facing, eye-line, action, others, light, last frame), delivered beneath the prompt, collapsed where the surface allows, so the geometry can be checked on paper before a take is paid for.
6. Optional Chinese compressed version when useful.
7. Shot-list or delivery note when the prompt belongs to a professional sequence.
8. Safety or copyright note when relevant.
9. Screen note: one line naming any wording the pre-screen changed, or that it changed nothing.

Before finalizing, run an anti-slop pass and remove vague quality boosters.
