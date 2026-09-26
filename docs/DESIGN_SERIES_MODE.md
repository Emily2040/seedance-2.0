# Design: series mode for micro-drama and short stories

Status: design, 2026-09-26. Answers the report that users bring a one-to-three
minute story or a multi-episode series, expect the whole thing drafted as
linked director-grade prompts, and instead get one prompt and a continuation
that falls apart. Evidence tiers are stated throughout; sources are in
`docs/EVIDENCE_NOTES_2026-09-26.md`. The specimen episode at the end is
authored and unrendered.

## Why it falls apart today

Four repository readers mapped the current behaviour. It is principled and
incomplete.

- The sequence skill plans the whole story and compiles only the next
  unresolved clip; later clips are stored as "provisional intent cards"
  (`skills/seedance-sequence/SKILL.md:26, 68-69`). The intent card has no
  defined shape, so the "whole story" a user sees is one sentence per clip
  (`examples/sequence-airport-arrival/sequence-plan.md`).
- The state model has story, scenes, beats and clips, but no episode or
  series layer: no cold open, hook, cliffhanger, recap, or recurring-cast
  record (`references/sequence-project-state.md:47-55`).
- Dialogue is untimed and unformatted inside clip prompts; two-speaker scenes
  are steered out of a single generation; eyelines and screen direction are
  ledger rows nobody writes into a prompt; example clips are planned at 5–8
  seconds, not 15.
- The README promises a "prompt batch" for professional roles while the eval
  suite forbids more than one finished prompt (`evals/evals.json:1124`).

The gate itself is right. Seedance 2.0 may not end where the plan expected,
extension is not available on every surface, and the provider's own model
card lists continuation defects (color consistency, multi-subject omission,
subject duplication). What is missing is everything between "plan" and "one
prompt".

## What the official and field evidence allows

- One generation is 4–15 seconds. A two-minute episode is at least eight
  generations; a one-call episode is a 2.5 leak or fiction. (Official.)
- Structured, shot-level prompting outperforms one global prompt for Seedance
  in the one benchmark that measured it, and the same benchmark rates Seedance
  weak on film-grammar continuity: transitions, rhythm, the 180-degree rule,
  eyelines. (Research tier.) Dense cutting inside dialogue is therefore the
  wrong bet; one setup per clip is the right one.
- Continuity techniques, by tier: identity images every clip (official
  framing, necessary not sufficient); the accepted final frame as the next
  first frame (field, most common, no guarantee); the previous clip as a video
  reference for camera and motion (official framing for video references,
  unproven for identity); short filtered locks placed consistently (field plus
  the research finding that filtered prior context beats a whole bible);
  native extend where the surface has it, capped at two or three steps
  (official feature, degradation reported). Seeds do nothing across clips.
- Vertical short-drama craft as reported by press and production tools: 9:16,
  a hook in the first 3 seconds, a turn about every 15 seconds, episodes of
  40–70 seconds for the feed and up to 2 minutes for story series; segments
  sized by function, transitions 8–10 s, narrative beats 10–15 s, peaks
  12–15 s. (Field and press tiers.)
- Every production tool that drafts a whole episode up front still gates
  generation stage by stage, and the ones closest to this repository forbid
  compiling a continuation before the real previous video exists. (Field.)

## Series mode: the shape

Series mode adds two artifacts above the clip and one between the plan and the
prompt. It keeps the accepted-footage gate; it changes what the user can see
before footage exists.

### 1. Series bible (once per series)

Short, filtered, written for re-use in prompts, not as literature.

| Field | Content | Example from the specimen |
|---|---|---|
| Premise in one sentence | What the series is about and where it ends | A night nurse finds a stranger's ring in a laundromat dryer engraved with her own name. |
| Cast, two to four | Name; age; three stable visible features; one playable trait (a behaviour, not an adjective); voice in one line; reference tag | Teo, 60s, reading glasses on a cord, grey cardigan, keeps his left hand in his pocket; speaks slowly, finishes sentences late; `@Image2` |
| Locations, one to three | Name; fixed geography (what is left, right, behind); light source by time of day; reference tag | 24-hour laundromat: dryers along the left wall, attendant booth right, folding table centre; ceiling fluorescents, one warm lamp in the booth; `@Image3` |
| Visual rules | Aspect ratio; palette; camera family; what never appears | 9:16; cold fluorescents against one warm practical; locked or slow push only; no handheld; no on-screen text |
| Audio rules | Music policy; ambience bed; dialogue language and register | No music inside clips; dryer drone and rain as bed; English, quiet, short lines |
| Continuity locks | The five things that must never drift | Teo's glasses cord, Mara's missing left earring, the ring's engraving, dryer 7's position, the booth lamp |

### 2. Episode beat sheet (once per episode)

An episode is a list of clips with a job each. The sheet places the hook, the
turns and the cliffhanger by clip number, so the pacing convention is a
structure the user can see, not a lecture.

| Clip | Seconds | Function | Beat (one line) | Turn or hook |
|---|---|---|---|---|
| 01 | 15 | Hook | Mara pulls a ring from the lint trap; it is engraved with her name | Hook by 0:03 |
| … | … | … | … | Turn at 04 and 07; cliffhanger at 08 |

Sizing rule for the sheet (field tier, labelled): transitions 8–10 s,
narrative beats 10–15 s, peaks 12–15 s; a two-minute episode is eight clips;
a 60-second feed episode is four or five.

### 3. Provisional shooting script (the missing artifact)

Every clip in the episode is drafted in full, as a shooting script, and
marked provisional. This is what the user asked for and can read end to end.
The gate moves from "later clips do not exist" to "later clips exist and say
what will change when footage arrives".

Each clip card carries:

1. **Job and turn**: the beat and what changes.
2. **Direction**: one playable action per performer (a verb and a piece of
   business, never an emotion word), the suppressed behaviour if the clip has
   one, blocking with left and right named, and eyelines.
3. **Camera**: one setup, one move or a lock, start and end composition.
4. **Light**: the motivated source, in one line.
5. **Dialogue**: the exact lines, speaker named, and the spoken-seconds
   estimate at 2.3 to 2.8 English words per second, which is a working
   assumption and not a measurement of the model.
6. **Sound**: ambience, one cue, and the music policy.
7. **Continuity locks**: only the two or three at risk in this clip, from the
   bible.
8. **References**: each tag with its role and what it must not transfer.
9. **Endpoint**: the completed visible state the next clip inherits.
10. **The compiled prompt**, in the official order, within the surface budget.
11. **Re-anchor line**: which clauses will be rewritten from footage.

Clip 01 is final. Clips 02 onward are provisional. When a take is accepted,
the skill records the observed end state, re-compiles only the clips whose
inherited state changed, and marks them final one at a time. The user sees
the whole episode from the start and the gate still holds.

### 4. Per-clip prompt schema

For a continuous clip (most drama beats): one paragraph in the official order.
For a clip that needs a cut: numbered shot blocks in event order, camera move
or cut type first inside each block, no absolute seconds. Both forms:

```text
[Who, with @tag] does [playable action] at [where in frame, facing which
way]; [second performer] [action]. [Camera: one setup, one move or locked,
endpoint]. [Light: source]. Dialogue: NAME says "exact line." [Sound:
ambience; one cue]. [Constraints: no subtitles, no music; keep @tag's
features; the two locks at risk]. End on [visible state].
```

Budget: about 90–120 English words per clip prompt; the official ceiling is
1,000 English words or 500 Chinese characters, and the reason to stay far
under it is legibility of the one beat, not a model limit.

### 5. Dialogue per language

Estimate spoken seconds per line before writing it into a clip and leave the
line room to land: English about 2.3 to 2.8 words per second; Chinese about
3.5 to 4.5 characters per second; Japanese by morae, Korean by syllables using
the repository's existing sync-budget protocol. None of these rates is a
Seedance measurement; the model card lists multi-speaker lip-sync errors.
Rules that follow: one speaker per clip by default; a two-person exchange is
two clips or one clip with one line each and a reaction; lines under eight
words; a reaction beat after every line; the language of dialogue uniform in a
clip.

### 6. Continuity, in order of trust

1. Identity images for every recurring performer in every clip, one clean
   frontal reference each; a plain-background half-body is the field
   consensus.
2. The accepted final frame of the previous clip as the first frame when the
   surface supports it, plus the observed end state written in prose when it
   does not.
3. The previous clip as a video reference only when the next clip must
   inherit camera or motion.
4. Short locks at the end of the prompt, filtered to what this clip puts at
   risk.
5. Native extend only on a verified surface, at most two steps before
   re-anchoring from canonical references.

Drift is expected. The beat sheet reserves a re-anchor clip after every scene
boundary, and the retake protocol's one-variable rule applies per clip.

### 7. What the non-technical user sees

At door 3 of the first-run screen ("I have a story"), the agent asks one
question, "how does it end?", then returns: the bible in a table, the beat
sheet in a table, and the eight clip cards with clip 01 marked ready and the
rest marked "will adjust after clip 01". It never says "provisional intent
card". It says: "Clips 2 to 8 are written. I'll touch only the lines that
depend on how clip 1 actually ends."

## Repository changes

| File | Change |
|---|---|
| `skills/seedance-sequence/SKILL.md` | Replace "intent cards" with the provisional shooting script; define the clip card fields; keep clip 01 final and later clips provisional; add the episode beat sheet and the series bible to the output contract. |
| `references/sequence-project-state.md`, `schemas/project-state.schema.json` | Add `series`, `episode`, `hook_clip`, `turn_clips`, `cliffhanger_clip`, `recurring_cast`, `reanchor_after_scene`; add `provisional: true/false` and `inherits_from_observed_state` on clip records. |
| `references/prompt-compiler.md` | Compile all clips as provisional; re-compile only clips whose inherited state changed; emit the per-clip schema above. |
| `references/directing-engine.md`, `references/cinematography-shot-language.md` | Require blocking with named sides and eyelines in every drama clip; one setup per clip; add the two-person coverage rule across clips. |
| `references/audio-guide.md`, `references/sync-budget-protocol.md` | Add the per-language spoken-seconds estimate with its unverified label; one speaker per clip default. |
| `references/continuation-handoff.md` | Order the continuity techniques by trust as above; document the re-anchor clip. |
| `references/multishot-grammar.md` | The dialogue-clip rule: one setup, no dense cutting, cite the film-grammar weakness finding. |
| `README.md` | Reconcile "prompt batch" with the eval rule: a batch is provisional clips plus one final. |
| `evals/evals.json` | New cases: a story request returns bible, beat sheet and eight clip cards with exactly one final prompt; a clip card without a playable action or endpoint fails; a two-speaker beat is split or reduced to one line each; a clip prompt with absolute seconds fails on 2.0. |
| `examples/series-laundromat/` | The specimen below as a worked example with its project state. |

## Specimen episode: "Dryer Seven" (authored, unrendered)

Two minutes, 9:16, eight clips of about 15 seconds, English, one location.
Original characters. Written to the bar above; every prompt is for Seedance
2.0 on a 15-second surface with duration set in the tool's panel.

### Director's read (internal, never sent)

- Turn: Mara arrives as someone returning lost property and leaves as someone
  who stays; the value that changes is from "not my business" to "tell me".
- Suppressed behaviour: Teo keeps his left hand in his pocket to hide a
  tremor; he takes it out exactly twice.
- Non-transferable detail: rings engraved MARA in a drawer, and Mara's missing
  left earring.
- Stock solution refused: no flashback, no tears, no music swell. Grief is a
  drawer of rings and a dryer ritual.

### Series bible excerpt

- **Mara**, late 20s, night nurse; navy scrubs under an open grey coat, hair
  tied back, left earring missing. Playable trait: checks a pager that never
  buzzes. Voice: flat, tired, dry. `@Image1`.
- **Teo**, 60s, laundromat attendant; reading glasses on a cord, grey
  cardigan, left hand in pocket. Playable trait: steadies objects against an
  edge before lifting them. Voice: slow, finishes sentences late. `@Image2`.
- **Laundromat, 2 a.m.**: dryers along the left wall, dryer 7 nearest the
  camera; attendant booth right with a warm desk lamp; folding table centre;
  rain on the front window behind. `@Image3`.
- Visual rules: 9:16; cold ceiling fluorescents against the one warm lamp;
  locked frames or a slow push only; no on-screen text.
- Audio rules: no music; dryer drone, rain; short English lines.
- Locks: glasses cord; missing left earring; engraving "MARA"; dryer 7 on the
  left; booth lamp on the right.

### Beat sheet

| Clip | s | Function | Beat | Marker |
|---|---|---|---|---|
| 01 | 15 | Hook | Ring from the lint trap, engraved MARA | Hook |
| 02 | 15 | Setup | She brings it to the booth; he reads her badge, not the ring | |
| 03 | 15 | Complication | The tremor shows as he lifts the ring | |
| 04 | 15 | Turn 1 | A drawer of identical rings | Turn |
| 05 | 15 | Reveal | "Every year on the fourteenth"; her pager finally buzzes | |
| 06 | 15 | Decision | She sits down; pager face down; he takes his glasses off | |
| 07 | 15 | Ritual | He puts a ring in dryer 7 and starts it | Turn |
| 08 | 15 | Cliffhanger | The ring fits her; he notices the earring | Cliffhanger |

### Clip 01 (final)

Direction: Mara kneels at dryer 7, pulls the lint trap, digs with two fingers,
finds the ring, turns it to the ceiling light, reads it, looks up right
toward the booth. Camera: locked medium on the dryer at her eye level when
kneeling, no move. Light: cold fluorescents; the booth lamp is a warm point
top right. Dialogue: none. Sound: dryer drone, rain, the scrape of the lint
trap, a small metal tick when the ring meets the trap edge. Spoken seconds: 0.
Endpoint: ring held between thumb and finger at eye height, her face turned
up right.

```text
Mara @Image1, navy scrubs under an open grey coat, kneels at the nearest
dryer on the left wall of the laundromat @Image3 at 2 a.m. and pulls out the
lint trap. She digs with two fingers, stops, and lifts a plain gold ring out
of the lint. She turns it to the ceiling light, reads the inside, and looks
up to the right toward the warm lamp of the attendant booth. Locked medium
shot at her kneeling eye level, no camera movement. Cold fluorescent light
with one warm lamp far right. Sound: dryer drone, rain on the window, the
lint trap scraping, one small metal tick. No music, no subtitles. Keep her
left ear bare. End with the ring held up at eye height and her face turned
up right.
```

Re-anchor: none; this is the first clip.

### Clip 02 (provisional)

Direction: Mara stands at the booth counter and sets the ring down; Teo, left
hand in his cardigan pocket, does not look at the ring; he reads the name
badge on her scrubs, then lays his right hand flat on the counter beside the
ring without touching it. Blocking: Mara frame left facing right; Teo frame
right facing left; eyelines meet across the counter. Camera: locked two-shot
over the counter, slightly favouring Teo; no move. Light: the warm desk lamp
keys Teo; the fluorescents fill Mara. Dialogue: MARA, "Found this in seven."
(4 words, about 1.7 s). Sound: drone, rain, ring set on laminate. Endpoint:
Teo's right hand flat beside the ring, his eyes on her badge.

```text
Mara @Image1 stands at the left side of the attendant booth counter, facing
right, and sets the gold ring down on the laminate. Teo @Image2, reading
glasses on a cord, grey cardigan, left hand kept in his pocket, stands
inside the booth facing her. He does not look at the ring; he reads the name
badge on her scrubs. Mara says "Found this in seven." Teo lays his right hand
flat on the counter beside the ring without touching it. Locked two-shot
across the counter, no camera movement. Warm desk lamp on Teo, cold
fluorescent fill on Mara. Sound: dryer drone, rain, the ring tapping the
counter. No music, no subtitles. Keep his left hand in the pocket. End with
his hand flat beside the ring and his eyes on her badge.
```

Re-anchor: her hand position and the ring's exact spot on the counter come
from clip 01's accepted final frame.

### Clip 03 (provisional)

Direction: Teo takes his left hand out of his pocket to pick up the ring;
the hand trembles; he braces the heel of it against the counter edge before
lifting the ring. Mara sees the hand, says nothing, glances down at the pager
clipped to her waistband. Camera: locked medium close on Teo's hands and the
ring, Mara's torso soft in the left of frame; no move. Light: lamp on the
hands. Dialogue: TEO, "Seven jams every winter." (4 words, about 1.8 s, spoken
slowly). Sound: drone, rain, the ring sliding on laminate. Endpoint: ring in
Teo's closed left palm on the counter.

```text
Close on the booth counter. Teo @Image2 takes his left hand out of his
cardigan pocket; the hand trembles. He braces the heel of the hand against
the counter edge, then picks up the gold ring. Mara @Image1 stands soft at
the left edge of frame; her eyes drop to the pager on her waistband and she
says nothing. Teo says, slowly, "Seven jams every winter." His left hand
closes around the ring and rests on the counter. Locked medium close-up on
the hands and the ring, no camera movement. Warm lamp light on the hands.
Sound: dryer drone, rain, the ring sliding on the counter. No music, no
subtitles. Keep the glasses cord visible. End with the closed left hand
resting on the counter.
```

Re-anchor: whether the ring lay left or right of his hand in clip 02's
accepted frame decides which hand crosses which.

### Clip 04 (provisional)

Direction: Teo opens the counter drawer, takes out a small tin, and tips it;
three more rings roll onto the counter in a line. Mara leans in and reads
them one by one, turning each with a fingertip. Blocking as clip 02. Camera:
locked high angle on the counter from Mara's side; no move. Light: lamp.
Dialogue: MARA, "How many Maras do your dryers eat?" (7 words, about 2.8 s).
Sound: drawer slide, tin lid, three rings rolling and settling. Endpoint: four
rings in a row under Teo's glasses, which he has lowered to look.

```text
High angle over the booth counter. Teo @Image2 opens the drawer, takes out a
small dented tin, and tips it; three gold rings roll out and settle in a line
beside the first. Mara @Image1 leans in from the left and turns each ring
with one fingertip, reading the inside of each. She says "How many Maras do
your dryers eat?" Teo lowers his reading glasses onto his nose and looks at
the four rings, not at her. Locked high-angle shot from Mara's side of the
counter, no camera movement. Warm lamp light on the rings. Sound: drawer
slide, tin lid, rings rolling and settling. No music, no subtitles. Keep her
left ear bare and the glasses cord visible. End with four rings in a row
under his lowered glasses.
```

Re-anchor: number and spacing of rings, and which hand holds the tin, from
clip 03's accepted frame.

### Clip 05 (provisional)

Direction: Teo, glasses down, speaks to the rings, not to her; halfway
through he puts his left hand back into the pocket. Mara's pager buzzes for
the first time; she silences it with her thumb without reading it and keeps
her eyes on him. Camera: locked medium on Teo across the counter, Mara's
shoulder in frame left; no move. Light: lamp. Dialogue: TEO, "One. Every year
on the fourteenth I put one in seven." (11 words, about 4.5 s, slow); no line
for Mara. Sound: drone, rain, a short pager buzz, the click of it silenced.
Endpoint: her thumb on the pager, her eyes on him, his left hand back in the
pocket.

```text
Medium shot of Teo @Image2 behind the booth counter, reading glasses down,
four gold rings in front of him. He speaks to the rings, not to Mara: "One.
Every year on the fourteenth I put one in seven." Halfway through the line
his left hand slides back into his cardigan pocket. Mara @Image1, shoulder in
the left edge of frame, feels her pager buzz once at her waistband; she
silences it with her thumb without looking at it and keeps her eyes on him.
Locked medium shot across the counter, no camera movement. Warm lamp on Teo,
cold fill from the room. Sound: dryer drone, rain, one short pager buzz, a
click. No music, no subtitles. Keep the glasses cord visible. End with her
thumb on the pager and her eyes on him.
```

Re-anchor: the rings' layout and his glasses position from clip 04's
accepted frame.

### Clip 06 (provisional)

Direction: Mara takes off her coat, drops it over the folding table, sits on
the table's edge facing the booth, and sets the pager face down beside her.
Teo takes his glasses off for the first time and looks straight at her.
Blocking: Mara now centre-left, Teo right; eyelines meet across the room.
Camera: one slow push from wide to medium on Mara, ending when she is seated;
Teo stays soft at frame right. Light: fluorescents on her, lamp behind him.
Dialogue: MARA, "Tell me the fourteenth." (4 words, about 1.7 s). Sound: coat
on laminate, the pager set down, drone, rain. Endpoint: glasses folded on the
counter, Teo bare-eyed, Mara seated facing him.

```text
Mara @Image1 takes off her grey coat, drops it over the folding table in the
centre of the laundromat @Image3, and sits on the table's edge facing the
booth on the right. She places her pager face down beside her. She says
"Tell me the fourteenth." Teo @Image2, soft at the right edge of frame,
takes his reading glasses off, folds them onto the counter, and looks
straight at her for the first time. Camera starts wide and pushes in slowly
to a medium shot on Mara, settling as she sits. Cold fluorescent light on
her, the warm lamp behind him. Sound: the coat landing, the pager set down,
dryer drone, rain. No music, no subtitles. Keep her left ear bare. End with
his folded glasses on the counter and the two of them facing each other.
```

Re-anchor: where the coat and pager land, and whether she sits or leans,
from clip 05's accepted frame; the push length adjusts to her position.

### Clip 07 (provisional)

Direction: Teo comes out of the booth with the tin, crosses left to dryer 7,
opens the door, places one ring in the drum with his right hand, closes the
door, feeds a coin, presses start. The drum turns; the ring ticks inside.
Mara watches from the table. Camera: locked wide from behind Mara's shoulder,
dryer 7 left, booth right; no move. Light: fluorescents; the dryer's small
interior lamp comes on. Dialogue: TEO, "It's the fourteenth." (3 words, about
1.3 s). Sound: his steps, the dryer door, a coin, the drum starting, the ring
ticking on metal. Endpoint: the drum turning with the ring ticking; Teo's
hand still on the dryer door.

```text
Wide shot from behind Mara @Image1's shoulder as she sits on the folding
table. Teo @Image2 comes out of the booth on the right carrying the small
tin, crosses left to the nearest dryer, opens its round door, places one gold
ring inside with his right hand, closes the door, drops in a coin and presses
start. The drum begins to turn and the ring ticks against the metal. He says
"It's the fourteenth." Locked wide shot, no camera movement, dryer 7 on the
left and the booth lamp on the right. Cold fluorescent light; the dryer's
small interior light comes on. Sound: his steps, the dryer door, one coin,
the drum starting, the ring ticking. No music, no subtitles. Keep his left
hand in the pocket. End with the drum turning and his right hand still on
the door.
```

Re-anchor: the tin's location and Mara's seated position from clip 06's
accepted frame.

### Clip 08 (provisional, cliffhanger)

Direction: Mara picks up the first ring from the counter, slides it onto her
own ring finger; it fits. She holds the hand up. Teo, turning back from the
dryer, looks not at the ring but at her bare left ear, and stops walking.
Blocking: Mara at the counter left, Teo mid-room right. Camera: locked medium
on Mara's hand and face, Teo entering soft behind; no move. Light: lamp on her
hand. Dialogue: TEO, "Her left one. She lost it here too." (8 words, about
3.2 s). Sound: drone, drum, ring on skin. Endpoint: hold on both, her hand
raised, his step stopped.

```text
Mara @Image1 stands at the booth counter, picks up the first gold ring, and
slides it onto the ring finger of her right hand; it fits. She raises the hand
into the lamp light and looks at it. Behind her, soft, Teo @Image2 turns back
from the dryer, sees her bare left ear, and stops mid-step. He says "Her left
one. She lost it here too." Locked medium shot on Mara's raised hand and face,
Teo soft in the background right, no camera movement. Warm lamp on her hand,
cold room behind. Sound: dryer drone, the drum turning, the faint ring tick.
No music, no subtitles. Keep her left ear bare and his glasses cord visible.
End holding on her raised hand and his stopped step.
```

Re-anchor: whether the first ring stayed on the counter through clips 04 to
07 in the accepted footage; if it moved, clip 08 opens with her taking it
from wherever it was last seen.

### What the critic should attack

The specimen was written against the repository's anti-slop lexicon and the
Director's Read. The checks a reviewer should run before this becomes an
example: every line under eight words except one that is deliberately long
and slow; every clip one setup; every endpoint a visible state; no emotion
adjectives; locks limited to what each clip risks; total dialogue under 20
spoken seconds across two minutes, which is deliberate for a first series
episode on a model with documented multi-speaker lip-sync limits.
