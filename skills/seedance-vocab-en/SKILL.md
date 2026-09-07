---
name: seedance-vocab-en
description: "This skill should be used when an English Seedance 2.0 prompt needs clearer production wording, less generic prose, or precise vocabulary for camera, lighting, motion, VFX, audio, and constraints. Route blocked prompts through seedance-filter for context and boundary review."
license: MIT
user-invocable: true
tags:
  - english
  - vocabulary
  - anti-slop
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

# seedance-vocab-en

Before producing prompt text, a prompt-ready block, a rewrite, an example, or a compiled clip, load the [Director's Read](../../references/directors-read.md), classify the brief, and complete its canonical narrative or non-narrative record. Translate that record into visible or audible carriers and keep its internal labels out of final generation prose.

Use this skill when the user chooses English prompt wording. Concrete production language can make the intended scene easier to review; it is not a demonstrated cure for moderation errors. This repository has no matched evidence that English receives heavier moderation than other languages. Preserve actual reference tags exactly; their spelling is independent of the prompt language.

Before adapting a reference example below, load [Using Reference Examples](../../references/surface-prompt-profiles.md#using-reference-examples). Bind its placeholders to real assets by the requested role, then preserve the actual token, including its script, case, spacing and punctuation. A written example token does not attach a file.

## Intent

Help the user express the intended action, camera, light and sound clearly. Preserve their chosen language, exact dialogue, reference bindings and creative constraints. Separate a wording clarification from a proposal to change what happens in the scene.

## Usage Rule

Use visible or audible detail when a phrase leaves a relevant production choice unclear. Keep useful genre, style and mood labels. The examples below are optional vocabulary, not required camera moves, lighting setups or limits on scene complexity.

| Function | English wording |
|---|---|
| Camera | `slow push-in`, `locked medium shot`, `stable lateral tracking`, `pull back to reveal`, `macro close-up` |
| Lighting | `soft backlight`, `warm practical light from the left`, `cool moonlight rim`, `wet asphalt reflecting neon` |
| Motion | `a slow head turn that stops`, `droplets merge and slide down`, `fabric settles after the gesture` |
| Audio | `quiet room tone`, `one clear spoken line in quotes`, `no music until after the line` |
| Constraints | `keep the logo, label, and shape unchanged`, `one action, one camera move`, `nothing else moves` |

## De-Slop Pass

Preserve the intended energy and useful style choices; clarify ambiguity and remove redundant praise in context. Do not turn every "cinematic" into a slow push-in or every "epic" into a crowd. Follow the [anti-slop lexicon](../../references/anti-slop-lexicon.md) for conditional repairs. Keep an explicit resolution target as a delivery requirement, using a supported setting when available and stating any gap. Prompt wording alone cannot guarantee output dimensions. Preserve exact dialogue, actual reference tokens, safety boundaries and chosen settings; respect decisions already delegated by the user.

## Filter-Aware Wording

For a blocked prompt, load [seedance-filter](../seedance-filter/SKILL.md) and assess the actual request before rewriting. A rejection alone does not establish a false positive or identify a trigger word. The examples in [filter-vocab](../../references/filter-vocab.md) clarify known benign meanings; they are not a tested trigger list or an approval guarantee. Do not invent ownership, consent, prop status or harmless intent. If an alternative changes the content, state that change and offer it as a choice; never disguise prohibited intent.

## Compact Pattern

`@Image1 is the reference; keep identity, color, and shape unchanged. Only [motion/light/camera] changes. Camera: [one move]. Sound: [one cue]. Constraints: [lock].`

Load [English vocabulary](../../references/vocab/en.md) for the full function-organized vocabulary, slop traps, and context-dependent wording examples. Load [anti-slop-lexicon](../../references/anti-slop-lexicon.md) for intent-preserving editorial guidance and [filter-vocab](../../references/filter-vocab.md) for the distinction between faithful clarification and a different content proposal.

## Output Contract

Return the English prompt with unchanged reference tags and a brief explanation of material edits. Identify any proposed content change separately. Do not label the result filter-approved or imply that a rewrite authorizes another submission.
