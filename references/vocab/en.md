# English Vocabulary

Use this reference when the user chooses English Seedance prompt wording. The examples support editorial clarity; they do not establish a language-wide moderation ranking or guarantee that a revised prompt will be accepted. Keep reference tags unchanged when translating surrounding prose. The tokens in these tables and templates are examples, not attached assets or universal syntax. Before adapting them, follow [Using Reference Examples](../surface-prompt-profiles.md#using-reference-examples) and preserve the actual binding token, whatever its script or format.

| Function | English wording | What it decides |
|---|---|---|
| Role | `@Image1 is the first frame` | locks the opening composition |
| Role | `@Image2 is the last frame` | sets the final visual target |
| Role | `@Image1 locks character identity` | face, hair, and wardrobe stay stable |
| Role | `@Video1 controls camera movement only` | motion donor, no appearance transfer |
| Role | `@Video1 controls action rhythm only` | pacing donor, nothing else transfers |
| Role | `@Audio1 controls tempo and mood only` | the clock of the edit, not its content |
| FirstLastFrame | `keep the first frame unchanged` | anchors the opening state |
| FirstLastFrame | `treat the last frame as the final visual target` | endpoint, not mood reference |
| FirstLastFrame | `one continuous motion, no jump cut` | forces a single transition path |
| FirstLastFrame | `preserve the same character, wardrobe, and layout` | continuity lock across frames |
| Camera | `slow push-in` | replaces "cinematic zoom" |
| Camera | `pull back to reveal the space` | motivated reveal, not "epic wide" |
| Camera | `stable lateral tracking` | clean sideways travel |
| Camera | `locked medium shot` | stability for faces and dialogue |
| Camera | `macro close-up` | material and product detail |
| Camera | `low-angle shot` | stature without the word "epic" |
| Camera | `over-the-shoulder shot` | conversation geometry |
| Camera | `handheld with slight breathing sway` | documentary energy, controlled |
| Shot | `medium close-up` | emotion with context |
| Shot | `wide establishing shot` | place before people |
| Shot | `three-quarter profile` | dimensional face angle |
| Lens | `24mm wide spatial feel` | space and context |
| Lens | `50mm natural portrait perspective` | honest faces |
| Lens | `macro lens on material detail` | texture as the subject |
| Lighting | `soft backlight` | separation without glow words |
| Lighting | `warm practical light from the left` | sourced, directional warmth |
| Lighting | `cool moonlight rim` | night shape without "moody" |
| Lighting | `volumetric light through thin mist` | visible beams, physical cause |
| Lighting | `wet asphalt reflecting neon` | the reflection is the light |
| Motion | `fog parts around the footsteps` | environment reacts to subject |
| Motion | `droplets merge and slide down the label` | product motion, physical |
| Motion | `a slow head turn that stops` | acting beat with an endpoint |
| Motion | `fabric settles after the gesture` | follow-through proves the move |
| VFX | `gold particles rise, catch the backlight, and dissipate` | source, path, endpoint |
| VFX | `thin electrical arcs crawl along the cable` | effect anchored to an object |
| VFX | `cold vapor rolls over the rim and sinks` | density and direction |
| Audio | `quiet room tone` | silence with presence |
| Audio | `one clear spoken line in quotes` | dialogue the lip-sync can hold |
| Audio | `a single soft metallic tick` | one sound, one event |
| Audio | `no music until after the line` | mix priority stated plainly |
| Audio | `distant traffic bed under rain` | layered ambience, no slop |
| Text | `no on-screen text, no watermark` | text belongs in post |
| Editing | `match cut on the circular shape` | named transition, not "cool" |
| Editing | `hard cut on the downbeat` | edit tied to the sound |
| Constraint | `keep the logo, label, and shape unchanged` | product identity lock |
| Constraint | `no identity change, no object redesign` | drift guard |
| Constraint | `one action, one camera move` | the budget rule in six words |
| Constraint | `nothing else moves` | isolates the hero motion |
| Safety | `staged confrontation, no graphic injury` | requests non-graphic staging; context still needs assessment |
| Safety | `original character with broad archetype traits` | requests an original character; a label does not establish permission |
| Safety | `prop object handled safely` | requests safe handling of a confirmed prop; not an approval guarantee |

## Dialogue Notes

No validated English word ceiling or universal second-place language ranking is established here. Preserve quoted dialogue and time the actual delivery with pauses. A short speaker turn and stable framing are starting heuristics, not limits. Evaluate words, performance, and sync separately using [audio-guide](../audio-guide.md); a written pause is direction, not a guaranteed re-sync mechanism.

## Slop Traps

Review these phrases in context. They can communicate useful style or mood; this repository has no measured basis for calling them universally zero-signal. Keep the intended energy and clarify only a material ambiguity. These are possible decisions, not required replacements. Follow [anti-slop-lexicon](../anti-slop-lexicon.md) for shared preservation and delivery rules.

| Phrase to review | Preserve or clarify |
|---|---|
| cinematic | Keep the intended film language; clarify framing, pacing or light where needed, without imposing a stock look |
| epic | Preserve the ambition; clarify whether scale, emotional stakes or another intensity matters |
| stunning / breathtaking | Clarify the intended impact or reveal without inventing a new event |
| beautiful | Keep the aesthetic preference; clarify relevant color, texture, material or performance |
| masterpiece / award-winning | Remove unsupported praise when redundant; retain any actual reference role or concrete requirement |
| 8K / ultra-HD | Retain the delivery target in supported settings; state unknown support or a mismatch instead of silently deleting or lowering it |
| hyper-detailed / insanely detailed | Name the important details if needed; do not invent an output resolution or an arbitrary two-detail limit |
| dynamic | Clarify what moves, its speed and endpoint; an energetic scene can keep a locked camera |
| dramatic | Preserve the intended tension or acting; shadows, silence and camera pressure are choices |
| atmosphere of mystery | Preserve the intended uncertainty; use the existing scene before adding fog, darkness or concealment |
| ultra-realistic | Keep the realism direction; add relevant material or motion detail without promising a rendered result |
| trending / viral style | Clarify the intended format or reference; do not assume vertical framing, a fast hook or engagement results |

## Wording in Context

A blocked result alone does not establish a false positive or reveal a trigger word. These are conditional editorial examples for known benign meanings, not measured filter behavior. Keep exact quoted dialogue unchanged unless the user asks to edit it.

| Known intended meaning | Faithful clarification |
|---|---|
| `shoot the scene` means recording a take | `film the scene` |
| `kill the lights` means switching the room lights off | `switch off the room lights` |
| `gun it` means increasing a vehicle's speed | `accelerate the vehicle` |
| `execution of the move` refers to performance | `performance of the move` |
| `blow up the image` means increasing its display size | `enlarge the image`; do not invent a new framing or output resolution |
| `dead silence` refers to sound | Preserve the requested sound state. Ask only if it matters whether the user means a muted track or quiet ambience; do not automatically add room tone |

Assess identity, consent, age, harm and other relevant context through [seedance-filter](../../skills/seedance-filter/SKILL.md) or the applicable rights route. A topic label is a reason to assess context, not proof that the request is prohibited or that a synonym will make it permissible. If the underlying request is prohibited, refuse it and offer a legitimate alternative only where appropriate.

Load [filter-vocab](../filter-vocab.md) to distinguish clarification from content changes, and [anti-slop-lexicon](../anti-slop-lexicon.md) for editorial vocabulary guidance. No rewrite promises acceptance or authorizes another generation attempt.
