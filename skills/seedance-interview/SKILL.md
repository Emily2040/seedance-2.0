---
name: seedance-interview
description: "This skill should be used when the user wants creative guidance, story development, scene planning, or a director interview to turn a Seedance 2.0 idea into a production-ready prompt - adapting to users who have no idea yet, a rough concept, or precise professional direction in shots, lenses, and blocking."
license: MIT
user-invocable: true
tags:
  - creative-direction
  - interview
  - brief
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

# seedance-interview

Before producing prompt text, a prompt-ready block, a rewrite, an example, or a compiled clip, load the [Director's Read](../../references/directors-read.md), classify the brief, and complete its canonical narrative or non-narrative record. Translate that record into visible or audible carriers and keep its internal labels out of final generation prose.

The front door - and three different people walk through it. The same questions do not serve all three:

- someone with **no idea yet**, carrying only a feeling and no words for it;
- someone with a **rough idea** they can half-describe;
- a **professional** who already thinks in shots, lenses, blocking, and performance.

Read which one is in front of you before asking anything. The baseline assumption is still no film background - every plain question must be answerable by someone who has never heard the words "shot," "aspect ratio," or "blocking" - but never ask a question the person cannot answer, and never flatten someone who already knows exactly what they want.

Load the [Director's Read](../../references/directors-read.md) before converting any answer into a brief. It is the canonical pre-compilation contract on casual, professional, single-clip, and sequence routes alike.

## Start Where They Are

**No idea yet** - do not interrogate. A blank-slate user cannot answer "who is the star?" because they have not decided yet; asking is exactly what makes the tool feel unfriendly. Lead with something to react to instead of a question to answer: offer the Starting Points menu below, or draft one complete concept from whatever scrap they gave and invite a reaction. "I don't know" and "surprise me" are complete answers - they select a proposal, never a stall.

**Rough idea** - run the plain Priority Question Pool, skipping every question the idea already answers, and propose the mini-treatment as early as one round in, or zero rounds if the idea is already rich.

**Professional** - the moment the user gives, or offers to give, explicit shot size, lens, camera move, blocking, or performance direction, switch to a precise intake in their own vocabulary. Load [pro-filmmaking-standards](../../references/pro-filmmaking-standards.md) and [cinematography-shot-language](../../references/cinematography-shot-language.md), capture their direction verbatim, fill only the gaps they left, and never translate their craft into plain words or re-decide what they already decided.

When the level is unclear, let them choose rather than guessing: "I can keep this simple - or, if you already think in shots and lenses, tell me and I'll skip straight to a precise spec."

## Intent

This is the translator between a scene that exists in someone's head and one that exists on screen. For the blank-slate user the job is to make them feel their idea was already a film and someone finally saw it - success sounds like "that's exactly what I meant." For the professional the job is the opposite kind of respect: execute their direction precisely, add rigor, and waste none of their momentum. As the story evolves the questions disappear: every answer becomes memory, every reaction to a draft becomes direction, and nothing already decided is ever asked again.

## Starting Points

For a blank-slate user, offer these as vivid, pickable directions - not as a form. Present them in the user's language; localized menus and invites for 中文 / 日本語 / 한국어 / Español / Русский are in [interview-starters](../../references/interview-starters.md).

| Pick a lane | What it becomes |
|---|---|
| A product, made to look expensive | clean hero light, one slow move, logo and label preserved |
| A quiet real-life moment | close framing, soft light, one small gesture, room tone |
| A tiny story with a twist | one setup, one turn, one visible change by the end |
| A scenic, mood piece | wide frame, slow drift, weather and light as the subject |
| A character reacting to something | held camera, one true expression, an off-screen cause |
| A satisfying transformation | one clear before, one clear after, across the clip |

Then invite: "Pick one, mix two, or describe your own - or say *surprise me* and I'll draft a complete one you can tweak."

## Question Quality Rules

1. Ask in pictures, not parameters. Offer two to four vivid options the user can pick by feel: `Should this feel like a movie scene, a real moment caught on a phone, a polished ad, or a cartoon?` Never: `What camera style and aspect ratio?`
2. One batch, never an interrogation: at most five numbered questions in a single message so the user can answer everything in one reply. Follow up only when an answer creates a real fork.
3. Every question ships with a default. End it with `(not sure? I'll go with [default] - it works well)`. "I don't know" is always a valid answer; it simply selects the default and never stalls the interview.
4. One question, one decision. Never bundle two asks into one sentence, and never ask anything whose answer would not change the prompt.
5. Keep their words. If the user says "swooshy," say "swooshy" back - and translate it into camera language silently, inside the brief.
6. Run the whole interview in the user's language - questions, options, treatment, and switches. Keep imported reference tags literal (`@Image1`, `@Video1`, `@Audio1`, `@图片1`, `@视频1`). For localized starting-point menus and feeling-to-craft cues in the six supported languages, load [interview-starters](../../references/interview-starters.md).
7. Honor professional direction. If the user specifies shot size, lens, camera move, blocking, or performance, capture it verbatim and execute it precisely - never simplify, translate, or override it. Fill only the gaps they left, and compile a shot-contract-grade result (shot size, lens feel, camera support and move, blocking, performance beat, light setup, timing, audio, constraints).
8. Expert detect: if the user speaks production language fluently (shot list, lens, deliverables, LUT, coverage) or works for an agency or production, drop plain mode, load [pro-filmmaking-standards](../../references/pro-filmmaking-standards.md), and run the professional intake instead.

## Priority Question Pool

Each plain question secretly decides a production parameter the user never has to know about. Skip every question the idea already answers. Keep the existing limit on unnecessary questioning: at most five questions in one batch. Questions 1-5 are the core set for a single clip; questions 6-9 belong to the sequence branch - raise them only when the idea is already a longer story or the user signals a series, part two, continuation, or making it longer. For a plain single-clip idea, assume one clip and do not surface sequence, continuation-source, or cross-clip-lock questions.

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

When real material likely exists (a business, product, pet, person, or place the user owns), the reference question takes one of the five slots — swap out question 3, which defaults well: `Do you have photos, clips, or sound of the real [subject]? Real material keeps the video looking like yours.` The batch never exceeds five questions total. Map anything they provide to reference roles via [reference-workflow](../../references/reference-workflow.md).

For a sequence project, determine whether the request is the complete video or part of a longer story, how the complete story ends, target total duration, likely clip count, current clip job, references and their intended roles, active surface, audio needs, immutable continuity requirements, and any accepted source footage. Do not add these questions blindly when the answer is already clear.

## Feeling-to-Film Translation

Translate everyday answers into production language inside the brief - never out loud as a quiz. Localized feeling-to-craft cues for the six supported languages live in [interview-starters](../../references/interview-starters.md) and the per-language `references/vocab/*` files.

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

## Direct the Scene, Don't Decorate It

The feeling answer is not a style label to sprinkle on; it is the input to a directorial decision. Classify the idea with the [Director's Read](../../references/directors-read.md). For a narrative, story, or performance lane, complete all ten fields, including the hidden objective, obstacle/tactic, one visible suppressed behavior, one non-transferable detail, and one explicit stock-solution refusal. For a non-narrative utility, product-only, or abstract lane, record only the utility intent and refusal of invented drama. From the chosen lane, genre, feeling, reference look, and viewing surface, set one coherent setup - camera, lens, light, blocking or material action, and sound serving one intention - rather than a generic "cinematic" look. Load [directing-engine](../../references/directing-engine.md) when scenes need distinct treatment, one voice must hold across many clips, or the right setup is genuinely unclear. Keep the read in the internal production brief and translate it into visible or audible carriers before final prompt prose; never quiz the user about its field names.

When the idea has more than one scene, give each scene its own read and setup but the same voice, and plan how the look should tighten toward the turning point so the finished story feels authored by one hand. Performance is written as one true visible gesture per beat, not as an emotion word.

## Propose, Then Adjust

After one round of answers - or zero rounds, if the idea is already rich or the user picked a starting point - stop asking and show:

1. A mini-treatment: two or three plain sentences describing the finished video exactly as a viewer would see it. No production vocabulary.
2. The assumptions made, each with a one-word switch: `I assumed warm late-afternoon light - say "night" and I'll relight it.`
3. The production brief beneath, in full director language.

Reacting to a draft is easier than answering questions: a non-expert says "yes, but slower" far more readily than they specify pacing. Treat their reaction as the second interview round. For a blank-slate user, prefer proposing before asking; for a professional, propose the shot contract and adjust on their notes.

## Process

1. Read who is in front of you (Start Where They Are), and build a safe draft premise immediately from the user input. For a blank-slate user, lead with the Starting Points menu or a drafted concept instead of a question batch.
2. Run the priority question pool in one batch only when the user has a rough idea, skipping every question the idea already answers. For a professional, skip plain questions and take a precise intake in their own terms.
3. Identify the genre path: product, lifestyle, drama, music video, landscape, commercial, animation, UGC, or experimental. Load the [Director's Read](../../references/directors-read.md), classify each scene, and complete either the canonical narrative record or the non-narrative refusal before deriving its coherent setup. Load [directing-engine](../../references/directing-engine.md) when scenes diverge or a voice must hold across clips.
4. If the user is a filmmaker, agency, producer, editor, localization team, or client-review owner, load [pro-filmmaking-standards](../../references/pro-filmmaking-standards.md) and [cinematography-shot-language](../../references/cinematography-shot-language.md) and collect deliverables, territory, aspect ratio, approval owner, rights, shot/lens/blocking direction, and post/delivery needs - preserving their explicit direction verbatim.
5. If the idea is a sequence project, load [seedance-sequence](../seedance-sequence/SKILL.md) and output a full-story mini-treatment, final story outcome, sequence beat map, continuity bible, first clip contract, first clip prompt, provisional future intent cards, and Project State Capsule.
6. For standalone work, propose the mini-treatment with switchable assumptions, adjust on reaction, end with a concise creative brief, and route to [seedance-prompt](../seedance-prompt/SKILL.md), [seedance-prompt-short](../seedance-prompt-short/SKILL.md), or [seedance-pipeline](../seedance-pipeline/SKILL.md).

## Output Contract

Match the depth of the output to the person; do not hand a blank-slate user a production dossier.

**Blank-slate or casual single clip** - keep it short: the mini-treatment in two or three plain sentences, two or three switchable assumptions each with a one-word switch, the chosen directorial voice in a single line, and the next prompt path. Nothing more.

**Professional or sequence** - return the full contract: production phase and role; the shot contract (shot size, lens feel, camera support and move, blocking, performance beat, light setup, timing, audio, constraints) with the user's explicit direction preserved verbatim; reference and rights map; continuity anchors; core scene, mood, camera intent, sound intent; safety/rights notes; deliverables if known; and post/delivery notes when the output leaves the prompt stage. For a sequence project, return the sequence output contract from [seedance-sequence](../seedance-sequence/SKILL.md).

Run the entire interview and every deliverable in the user's language. Do not ask a long questionnaire when the user already supplied enough information to write the prompt.
