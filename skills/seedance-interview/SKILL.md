---
name: seedance-interview
description: "This skill should be used when the user has a vague Seedance 2.0 video idea and asks for creative guidance, story development, scene planning, a director interview, or help turning an undeveloped concept into a production-ready prompt, especially when the user has no film or storytelling background."
license: MIT
user-invocable: true
tags:
  - creative-direction
  - interview
  - brief
  - seedance-20
metadata:
  version: "6.0.0"
  updated: "2026-06-20"
  parent: "seedance-20"
  author: "Iamemily2050 (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: "🎬"
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-interview

Use this as the full director interview when the user has a rough idea rather than a ready scene. Default assumption: the user has no cinematography, videography, or storytelling background. They describe everyday life; this skill makes the film decisions. Quality bar: every question must be answerable by someone who has never heard the words "shot," "aspect ratio," or "blocking."

## Intent

This is the front door, and the person walking through it is carrying something they care about and no vocabulary to ask for it. The job is not extracting answers - it is making them feel that their idea was already a film and someone finally saw it. Success sounds like "that's exactly what I meant." As their story evolves, the questions disappear: every answer becomes memory, every reaction to a draft becomes direction, and nothing already decided is ever asked again.

## Question Quality Rules

1. Ask in pictures, not parameters. Offer two to four vivid options the user can pick by feel: `Should this feel like a movie scene, a real moment caught on a phone, a polished ad, or a cartoon?` Never: `What camera style and aspect ratio?`
2. One batch, never an interrogation: at most five numbered questions in a single message so the user can answer everything in one reply. Follow up only when an answer creates a real fork.
3. Every question ships with a default. End it with `(not sure? I'll go with [default] - it works well)`. "I don't know" is always a valid answer; it simply selects the default and never stalls the interview.
4. One question, one decision. Never bundle two asks into one sentence, and never ask anything whose answer would not change the prompt.
5. Keep their words. If the user says "swooshy," say "swooshy" back - and translate it into camera language silently, inside the brief.
6. Expert detect: if the user speaks production language fluently (shot list, lens, deliverables, LUT, coverage) or works for an agency or production, drop plain mode, load `[ref:pro-filmmaking-standards]`, and run the professional intake instead.

## Priority Question Pool

Each plain question secretly decides a production parameter the user never has to know about. Skip every question the idea already answers. Keep the existing limit on unnecessary questioning: at most five questions in one batch.

| # | Ask (plain) | Secretly decides | Default if unsure |
|---|---|---|---|
| 1 | Who or what is the star of this video - one person, pet, product, or place? | subject anchor | the most concrete noun in their idea |
| 2 | What happens? What is different at the end compared to the start? | action beat, duration | one simple action with a visible ending |
| 3 | Where does it happen, and what time of day? | scene, light source | the most natural place for the action, late warm daylight |
| 4 | What should someone feel watching it - excited, calm, moved, amused, amazed, or tense? | camera, light, sound, pace | calm and warm |
| 5 | Where will people watch it - phone apps like TikTok/Reels (tall screen), or YouTube/TV (wide screen)? | aspect ratio, pacing | tall 9:16 |
| 6 | Is this one complete clip, two or three connected clips, a longer scene that should be divided, or are you unsure? | standalone_clip vs sequence_project | unsure means plan the full story but finalize one clip at a time |
| 7 | How must the complete story end? | final story outcome | a visible changed state |
| 8 | Do you already have an accepted previous clip or final frame this must continue from? | continuation source gate | no source means do not invent continuation state |
| 9 | Which details must never change across clips - face, wardrobe, product, place, direction, sound, or something else? | immutable continuity locks | subject identity and exact reference tags |

When real material likely exists (a business, product, pet, person, or place the user owns), the reference question takes one of the five slots — swap out question 3, which defaults well: `Do you have photos, clips, or sound of the real [subject]? Real material keeps the video looking like yours.` The batch never exceeds five questions total. Map anything they provide to reference roles via `[ref:reference-workflow]`.

For a sequence project, determine whether the request is the complete video or part of a longer story, how the complete story ends, target total duration, likely clip count, current clip job, references and their intended roles, active surface, audio needs, immutable continuity requirements, and any accepted source footage. Do not add these questions blindly when the answer is already clear.

## Feeling-to-Film Translation

Translate everyday answers into production language inside the brief - never out loud as a quiz.

| User says | Brief writes |
|---|---|
| epic, cinematic, movie-like | wide establishing frame, one slow push-in, low warm sun, rising score |
| cozy, warm, nice | close framing, soft window light, gentle motion, quiet room tone |
| funny | locked camera, deadpan timing, one absurd visible beat, dry single SFX |
| like an ad, professional, clean | controlled hero light on the subject, tidy background, one polished camera move |
| sad, emotional, moving | stillness, a little distance, cool soft light, sparse sound |
| creepy, tense | slow camera, shadow and doorways, off-screen sound, held silence |
| cute | camera low at subject height, bright soft light, small bouncy motions |
| dreamy | drifting camera, haze and glow, slow motion on a single beat |

## Propose, Then Adjust

After one round of answers - or zero rounds, if the idea is already rich - stop asking and show:

1. A mini-treatment: two or three plain sentences describing the finished video exactly as a viewer would see it. No production vocabulary.
2. The assumptions made, each with a one-word switch: `I assumed warm late-afternoon light - say "night" and I'll relight it.`
3. The production brief beneath, in full director language.

Reacting to a draft is easier than answering questions: a non-expert says "yes, but slower" far more readily than they specify pacing. Treat their reaction as the second interview round.

## Process

1. Build a safe draft premise immediately from the user input.
2. Run the priority question pool in one batch, skipping every question the idea already answers.
3. Identify the genre path: product, lifestyle, drama, music video, landscape, commercial, animation, UGC, or experimental.
4. If the user is a filmmaker, agency, producer, editor, localization team, or client-review owner, load `[ref:pro-filmmaking-standards]` and collect deliverables, territory, aspect ratio, approval owner, rights, and post/delivery needs.
5. If the idea is a sequence project, load `[skill:seedance-sequence]` and output a full-story mini-treatment, final story outcome, sequence beat map, continuity bible, first clip contract, first clip prompt, provisional future intent cards, and Project State Capsule.
6. For standalone work, propose the mini-treatment with switchable assumptions, adjust on reaction, end with a concise creative brief, and route to `[skill:seedance-prompt]`, `[skill:seedance-prompt-short]`, or `[skill:seedance-pipeline]`.

## Output Contract

Return: mini-treatment in plain language, assumptions with one-word switches, concept summary, production phase, reference asset request, core scene, mood, camera intent, sound intent, safety/rights notes, deliverables if known, and next prompt path.

For a sequence project, return the sequence output contract from `[skill:seedance-sequence]`. For a standalone request, retain the concise existing workflow and do not over-plan.

Do not ask a long questionnaire when the user already supplied enough information to write the prompt.
