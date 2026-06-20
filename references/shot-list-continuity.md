# Shot List And Continuity

Use this reference when a user asks for a film scene, ad sequence, multi-shot plan, storyboard, treatment-to-shot-list conversion, or continuity repair.

## Pre-Production Brief

Collect only what changes production decisions:

- objective: film scene, product ad, music video, trailer, social cutdown, internal pitch, test render;
- audience and territory;
- duration and target platforms;
- hero subject, product, character, or brand;
- references and what each one controls;
- rights/authorization status;
- dialogue/audio needs;
- aspect ratios and delivery surfaces;
- deadline, approval owner, and risk constraints.

## Shot List Fields

| Field | Example |
|---|---|
| Shot ID | `S01_SH03` |
| Duration | `5s` |
| Mode | T2V, I2V, R2V, FLF2V, edit, extend |
| Purpose | establish, reveal, demonstrate, emotional turn, end card |
| Subject/action | product rotates once; character lowers letter |
| Shot contract | medium close-up, locked-off, 50mm portrait compression |
| References | `[Image1] product identity`, `[Video1] camera rhythm`, `[Audio1] beat` |
| Continuity anchors | wardrobe, prop, screen direction, light state, background layout |
| Start frame | where the shot begins |
| End frame | next-shot handoff or final target |
| Audio | dialogue, ambience, SFX, music cue, silence |
| Risks | face drift, logo text, hand complexity, unsafe likeness, prompt block |
| Review notes | accept, retry, edit, extend, replace |

## Continuity Ledger

Track these anchors across shots:

| Anchor | What to record |
|---|---|
| Character | tag, wardrobe, hair, silhouette, prop, emotional state |
| Product | label, logo, geometry, material, color, packshot angle |
| Location | layout, left/right geography, doorway/window positions |
| Screen direction | subject moves left-to-right or right-to-left |
| Eyeline | where each character looks and whether it matches reverse shots |
| Lighting | key direction, practical sources, time of day, atmosphere |
| Camera | lens feel, height, stability, movement family |
| Action state | what happened at previous endpoint |
| Sound state | music, ambience, dialogue, sync cue |

## Treatment To Shot List

1. Extract the dramatic or commercial beats.
2. Assign one Seedance clip per beat unless the beat is tiny and stable.
3. Choose the fragile anchor for each clip: face, product, text, choreography, or endpoint.
4. Select the safest mode: I2V for identity/product preservation, FLF2V for exact endpoints, R2V for role-bound motion or camera, edit for one-layer changes, extend for continuation.
5. Create a shot contract and continuity anchors for every shot.
6. Write prompts only after the shot list is stable.

## Three-Shot Commercial Pattern

| Shot | Purpose | Prompt spine |
|---|---|---|
| 1 | Problem or world | wide or medium environment, simple action, establish product context |
| 2 | Product/material proof | close or macro, locked or slow push, material detail and one SFX |
| 3 | Hero packshot/end state | product three-quarter, clean light, logo preserved, tagline handled in post |

## Handoff Rules

- Use the accepted last frame as the next first-frame reference when continuity matters.
- Keep wardrobe, product orientation, screen direction, and light direction stable unless the story explicitly changes them.
- If a prompt creates a good performance but bad product/logo, edit or composite the product layer rather than regenerating the whole shot.
- If a shot fails three times, simplify the shot contract or split the action into two clips.

## Sequence-State Handoff

For stateful sequences, replace a loose continuity ledger with clip lineage:

- `project_id`, `clip_id`, and `parent_clip_id`;
- planned start and planned end state;
- observed start and observed end state after review;
- completed beats, current clip beats, and reserved future beats;
- continuity locks and allowed changes;
- transition in, transition out, open motion vectors, and handoff requirements.

Finalize only the current unresolved clip prompt. Later shot cards stay provisional until the preceding accepted take is reviewed.
