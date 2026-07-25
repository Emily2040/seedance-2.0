# Audio Guide

Use this reference for detailed audio, dialogue, beat-sync, ambience, and lip-sync workflows. Keep audio roles explicit and avoid promising exact platform behavior unless the active surface documents it.

For professional audio post, stems, M&E, dubbing, loudness, or delivery checks, also load `audio-post-delivery.md`.

## How the audio actually works (reason before you prompt)

Field-observed from 2026 community testing across Chinese, Russian, and English sources; test per surface and never promise results. Use these as a reasoning model, not guarantees.

- Audio and video are generated together in one pass, so timing is locked by construction - you are not adding a track, you are asking one model to commit to both at once.
- The model infers sound from what it sees whether or not you ask: a character on gravel gets footsteps, a street gets traffic. "Generic default audio" is therefore the resting state - you override it by naming the exact sound you want, because a sound cue acts as audio direction.
- Speech and lip articulation appear tightly coupled: asking for a moving mouth with no voice is unreliable, and the model tends to voice the line anyway. Plan around this instead of expecting silent lip-sync.
- Lip-sync is not always on by default. On some surfaces (for example Jimeng/即梦) it is a toggle that ships off; confirm the active surface enables voiced dialogue before blaming the prompt.
- Reliability is probabilistic. Reputable hands-on testing, including Chinese tech press, reports voice scrambling and garbled on-screen text on harder prompts, so budget retakes and keep dialogue simple.
- Language strength is uneven: field reports rank Mandarin strongest for lip-sync, English a close second, with Japanese, Korean, Russian, and others weaker and sometimes English-accented - a training-data effect, not something prompt wording alone fixes.

## Dialogue capacity (field-observed)

No official per-language word limit is published; the numbers below are field-observed ranges from 2026 community testing (cross-cited how-to blogs plus Chinese and Russian hands-on reports), not guarantees - test per surface.

Two budgets matter, and people confuse them. The acoustic budget is how many words fit at natural pace (English roughly 35-40 in 15 seconds). The reliable-sync budget - how much stays lip-synced and un-garbled - is much lower and is the real limit. "Words" also mislead across languages; the safer unit is one short sentence, about one breath (~1.5-2.5s, one idea).

| Language | Reliable-sync budget, ~15s clip | Per line | Note |
|---|---|---|---|
| English | ~16-20 words before the mix compresses | 5-10 words | close-second lip-sync |
| Mandarin | count in characters/syllables, not words; strongest sync | one short clause | best lip-sync, training-weighted |
| Japanese | not separately measured; treat as the weaker tier | one short line | mora-timed; word counts mislead |
| Korean | not separately measured, under-tested | one short line | flag uncertainty, do not assume parity |
| Russian | ~10-15 words maximum, shorter is better | under 10 words | weak, often English-accented |

Past the reliable-sync budget, especially in non-English, use the voice-reference lip-sync path below or plan a post-dub.

One budget trap is language-specific: **Korean has no neutral register**, and the speech level chosen for a line changes its syllable count. 감사합니다 (5 syllables) and 고마워 (3) are the same thanks at different levels, and 합니다체 runs roughly 1.5-2x 반말 across a line. On a tier already flagged as under-tested, picking the formal register by reflex can spend the budget on politeness endings rather than content. Decide the level deliberately - see Speech Level in `[ref:vocab/ko]`.

## Dialogue

- Keep lines short, preferably one sentence per speaker turn.
- Put spoken dialogue in quotes.
- Assign the speaker by tag.
- Use stable framing for lip-sync.
- Avoid head turns, large face movement, extreme camera moves, or busy hand action while mouth accuracy matters.
- If the line matters more than the environment, reduce music and SFX during the line.
- Non-English dialogue: keep lines even shorter - long non-English phrases are a field-reported weak spot. For a fully voiced non-English piece, plan a post-dub instead, and check the language's vocab file for dialogue notes.
- Inline audio tags (field-observed, surface-specific): some surfaces (for example Jimeng) let you append bracketed cues to the spoken line to steer voice timbre and insert SFX, e.g. `"..." [low warm voice][distant bell]`. Useful but unverified across surfaces - do not assume universal support.

## Audio reference mapping

`@Audio1` can be used for rhythm, pacing, mood, voice tone, ambience, music texture, or beat timing. Do not promise exact audio playback unless the active platform documents exact playback behavior. If the source contains a real voice or recognizable song, treat it as authorization-sensitive and convert it into broad sonic descriptors when rights are unclear.

On surfaces that accept a spoken-voice audio reference, field reports describe a stronger role than tempo or mood: attaching an actual voice clip can make the model lip-sync to that audio instead of synthesizing speech itself - effectively a lip-sync compiler. This is the most reliable field-reported path for non-English dialogue: record or commission the line, attach it, and let the model only move the mouth. Use only your own recorded, licensed, or rights-cleared voice; treat a real or recognizable person's voice as authorization-sensitive and route it through `[skill:seedance-copyright]` when rights are unclear. Verify the active surface actually exposes a voice audio reference before relying on this.

When an audio reference and video reference compete, silence or mute the video reference before upload when the audio should control timing. If the video must keep sound, state the priority: `@Video1 controls only camera/motion; @Audio1 controls tempo and energy`.

| Role | Good wording | Avoid |
|---|---|---|
| Tempo | `@Audio1 provides tempo only; foot taps match the downbeat` | copying a protected performance |
| Mood | `@Audio1 provides calm sparse atmosphere` | exact replay claim |
| Voice tone | `soft, breathy, close-mic delivery` | imitating a named real voice |
| Ambience | `rainy street room tone, distant traffic bed` | dense competing sound layers |
| Conflict repair | `@Video1 is muted and controls camera only; @Audio1 controls beat timing` | two sources both controlling rhythm |

## Multi-character dialogue

Use separate speaker turns when reliability matters. For two-person exchanges, generate controlled single-speaker clips and composite in post when necessary. If two speakers remain in one prompt, write: `Character A says... pause. Character B answers...` and keep the camera locked or gently motivated.

## Sound layer syntax

`Dialogue: Character A says "I found it." Sound: low room tone + distant rain. SFX: cup lands on table at 2s. Music: no music until after the line.`

## Beat-sync syntax

`@Audio1 provides tempo only. On each downbeat: back wall light pulses once, dancer hits one pose, camera remains locked wide.` Use visible beat changes rather than asking the model to understand an abstract groove.

## Audio as clock

Field-observed technique; test before promising results. Beyond mood and tempo, `@Audio1` can act as the master clock of the edit: `cut on the beat of @Audio1; the turn lands on the drop; the door slams on the final hit.`

- Tie each musical landmark to exactly one visible event - a cut, a pose, a light change, an object landing. One event per beat; stacked events smear.
- Works best with a single strong rhythm (clean drums, a metronomic pulse). Dense mixes or rubato material give the model no clock to follow.
- When the audio is the clock, make it the only clock: mute video references and avoid a second timing system, such as a timestamp list, in the same prompt.
- The clock works inside one generation only; audio is not continuous across calls, so multi-clip pieces get their unifying score in post.

## Troubleshooting

- Desync: shorten dialogue, stabilize camera, remove head motion, reduce competing sound, and clean up the source audio's role.
- Wrong speaker: split lines by speaker and use explicit character tags.
- Audio ignored: remove competing music/SFX instructions and make `@Audio1` role explicit.
- Overbusy mix: choose ambience plus one key SFX; remove music if dialogue matters.
- Lip-sync drift: use a locked medium close-up, no head turn, short quoted line, and simple expression.
- Audio-reference conflict: mute the video reference, remove competing SFX/music, and describe one visible event per beat.

## Post Handoff Boundary

Prompt audio can shape performance and visible timing, but final mixes need post-production review. For paid or delivery work, record spoken language, subtitle/dubbing needs, M&E/stem needs, sync cues, and buyer loudness target separately from the prompt.
