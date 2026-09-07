# Audio Guide

Use this reference for detailed audio, dialogue, beat-sync, ambience, and lip-sync workflows. Keep audio roles explicit and avoid promising exact platform behavior unless the active surface documents it.

For professional audio post, stems, M&E, dubbing, loudness, or delivery checks, also load [audio-post-delivery](audio-post-delivery.md).

## What the evidence supports

The [Seedance 2.0 model card](https://arxiv.org/abs/2604.14148), v1 dated 2026-04-15 and rechecked 2026-09-07, describes joint audio-video generation. Joint generation does **not** guarantee synchronization, exact dialogue, or reference playback. Inspect the active surface's audio controls; do not assume a named toggle exists or is off by default.

Table 20 reports developer-run I2V evaluations on a 1–5 scale, with separate audio quality (AQ), audio-visual sync (AVS), and audio prompt-following (APF) scores:

| Language | AQ | AVS | APF |
|---|---:|---:|---:|
| English | 4.00 | 3.93 | 4.20 |
| Japanese | 4.00 | 3.63 | 3.13 |
| Korean | 3.75 | 3.38 | 3.38 |
| Indonesian | 3.71 | 3.71 | 4.14 |
| Portuguese | 3.50 | 3.63 | 3.63 |
| Spanish | 4.14 | 4.14 | 4.00 |

These task-specific averages are not success percentages, universal language rankings, or this skill's results. Table 19 evaluates different Chinese-voice categories; do not combine the tables into a Mandarin-first hierarchy. Russian is absent from Table 20: that is an evidence gap, not proof of poor Russian support. The tables do not establish training-data causes or a reliable maximum line length.

## Dialogue capacity: measure the performance

This repository has no validated per-language word, character, mora, or syllable ceiling. Earlier numerical limits and language tiers lacked a reproducible dataset and are withdrawn. Distinguish **spoken duration** from **returned speech accuracy and visible sync**: a line can fit and still fail either check.

Preserve the user's language, script, exact quoted words, and intended relationship. For new dialogue, one short speaker turn is a useful starting heuristic. Read or record the actual line at the intended pace, including pauses, and leave time for the reaction. Written counts help describe a sample; they are not seconds or a universal sync budget. Use [sync-budget-protocol](sync-budget-protocol.md) only if the user wants a bounded calibration test.

Register changes character and wording. Choose it from the relationship and the user's intent, not to minimize syllables. If a line is too long, offer a shorter alternative, more time where supported, or post production. Do not silently replace formal language with casual speech. See [Japanese register](vocab/ja.md) and [Korean speech level](vocab/ko.md).

## Dialogue

- Keep lines short, preferably one sentence per speaker turn.
- Put spoken dialogue in quotes.
- Assign the speaker by tag.
- Use stable framing for lip-sync.
- Avoid head turns, large face movement, extreme camera moves, or busy hand action while mouth accuracy matters.
- If the line matters more than the environment, reduce music and SFX during the line.
- For any language, assess the actual line and performance. Offer native generation, a supported voice-reference workflow, or post dubbing according to the user's priorities; do not force a post-dub solely because the line is non-English.
- Inline audio tags (field-observed, surface-specific): some surfaces (for example Jimeng) let you append bracketed cues to the spoken line to steer voice timbre and insert SFX, e.g. `"..." [low warm voice][distant bell]`. Useful but unverified across surfaces - do not assume universal support.

## Audio reference mapping

`@Audio1` can be used for rhythm, pacing, mood, voice tone, ambience, music texture, or beat timing. Do not promise exact audio playback unless the active platform documents exact playback behavior. If the source contains a real voice or recognizable song, treat it as authorization-sensitive and convert it into broad sonic descriptors when rights are unclear.

A spoken-voice reference is an option only when the active operation supports the intended use. A reference-input feature alone does not promise verbatim playback or exact mouth motion. Compare the returned words, performance, and sync with the source. Use only your own recorded, licensed, or rights-cleared voice; route unclear real-person voice authorization through [seedance-copyright](../skills/seedance-copyright/SKILL.md). Post dubbing is a separate option when exact delivery matters.

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
