---
name: seedance-recipes
description: "This skill should be used when the user asks for a Seedance 2.0 template, genre recipe, product ad, lifestyle video, drama scene, music video, landscape shot, commercial, animation scene, or reusable production pattern."
license: MIT
user-invocable: true
tags:
  - templates
  - genres
  - recipes
  - seedance-20
metadata:
  version: "5.4.7"
  updated: "2026-06-11"
  parent: "seedance-20"
  author: "Iamemily2050 (@iamemily2050)"
  repository: "https://github.com/Emily2040/seedance-2.0"
  openclaw:
    emoji: "🎬"
    homepage: "https://github.com/Emily2040/seedance-2.0"
---

# seedance-recipes

Use recipes as starting patterns, not rigid prompt templates. Pick the recipe that matches the user's outcome, then customize subject, action, camera, lighting, audio, and constraints. Recipes should preserve the one-beat discipline of a short clip.

Load `[ref:genre-guides]` for genre patterns, `[ref:examples-by-mode]` when the user needs copy-ready examples, `[ref:shot-list-continuity]` for professional multi-shot sequences or commercials, and `[ref:multilingual-community-examples]` when the recipe should reflect Chinese/Russian/Japanese/Korean/Spanish community-style structures.

## Recipe Families

| Family | Best use | Core pattern |
|---|---|---|
| Product | Ads, ecommerce, hero shots, material reveals. | `product anchor + one material change + controlled camera + logo preservation` |
| Lifestyle | Human use, food, travel, social clips. | `simple action + lived environment + handheld or natural light + ambient sound` |
| Drama | Emotion, dialogue, short narrative beats. | `character tag + gesture + motivated camera + silence or sparse sound` |
| Music video | Beat sync, dance, stylized edits. | `rhythm reference + visible beat changes + light pulses + clear character blocking` |
| Landscape | Establishing shots, nature, atmosphere. | `slow camera + weather motion + layered depth + natural sound` |
| Commercial | Brand-safe polish and function. | `problem/use/result beat + precise product constraint + clean light` |
| Animation | Original characters and stylized motion. | `medium + shape language + palette + elastic or weighted motion` |
| VFX | Transformations, particles, weather, energy. | `source + material behavior + interaction + dissipation endpoint` |
| First/last frame | In-between transitions, product state changes, character pose targets. | `first frame + last frame + continuous transition + identity locks` |
| Commercial campaign | 6/10/15/30s variants, vertical/social cutdowns, textless/localized masters. | `hook + product proof + end state + cutdown matrix + delivery notes` |

## Prompt Skeletons

**Product I2V:** `[Image1] is the product reference; preserve logo, label, shape, and materials exactly. [One material or light change]. Camera: [single move]. Lighting: [physical source]. Sound: [ambient/SFX].`

**Drama T2V:** `Character A [visible emotional action] in [specific setting]. Camera: [motivated framing]. Lighting: [motivated source]. Sound: [ambient or short dialogue]. End state: [changed expression/action].`

**Reference Motion:** `[Video1] provides only [camera/action/timing] reference; do not transfer identity, costume, logo, or environment. New subject: [authorized/original subject]. [Action and endpoint].`

**First/Last Frame:** `[Image1] is the first frame. [Image2] is the last frame. Preserve [identity/product/scene anchors]. Generate a continuous transition from [start state] to [end state]. Camera: [locked or one controlled move]. Sound: [ambient/SFX].`

**Animation:** `Original [character archetype] [action] in [environment]. Style: [medium, line quality, texture, palette]. Motion: [rhythm]. Camera and sound: [simple support].`

## Selection Rule

If a user gives many goals, choose the recipe that protects the most fragile requirement. Product identity beats camera spectacle; lip-sync beats large head motion; character consistency beats complex choreography; first/last-frame target accuracy beats extra style changes; safety and authorization beat style mimicry.

## Output Contract

Return one selected recipe, why it fits, the customized prompt skeleton, compact final prompt, and campaign/delivery notes when relevant.
