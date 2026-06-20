---
name: seedance-style
description: "This skill should be used when the user asks for visual style, art direction, render feel, period aesthetic, texture, animation style, realism level, or style-safe alternatives to studio or franchise references."
license: MIT
user-invocable: true
tags:
  - style
  - art-direction
  - ip-safe
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

# seedance-style

Translate style requests into production descriptors. Style should describe medium, texture, palette, lens or render behavior, period cues, and composition. Do not rely on studio, franchise, artist, or living-creator names when a safer descriptive style can preserve the user's intent.

## Intent

Users point at art they love and ask to stand near it. The soul of this skill is honoring the love while refusing the theft: find what the love is made of - light, texture, rhythm, era - and rebuild it as something the user owns. They should feel their taste was understood, not corrected.

## Style Safety Rule

Do not use studio, franchise, artist, or living-creator names as style anchors unless the user has a clearly authorized workflow. Preserve the intended visual function by describing medium, texture, palette, lighting, composition, era, line quality, and motion rhythm.

| User intent | Safe production descriptor |
|---|---|
| Cozy hand-drawn fantasy | `hand-painted 2D animation, soft watercolor backgrounds, rounded character silhouettes, warm pastel palette, gentle parallax` |
| Sharp cyberpunk action | `neon noir city, wet pavement reflections, high-contrast magenta and cyan light, fast lateral tracking, angular silhouettes` |
| Premium product realism | `clean commercial realism, controlled reflections, shallow depth of field, neutral background, polished material detail` |
| Retro documentary | `1970s documentary texture, muted film grain, practical daylight, handheld observational framing` |
| Children's animation | `soft clay-like characters, simple expressive faces, bright primary palette, bouncy squash-and-stretch motion` |

## Layered Style Method

Separate style into layers instead of one broad label: **medium** (live action, stop-motion, 2D, 3D, miniature), **surface** (paper grain, clay, brushed metal, glass, fabric), **palette** (pastel, monochrome, sodium orange), **camera/render** (macro, shallow focus, orthographic, handheld), and **motion rhythm** (gentle, staccato, elastic, realistic weight).

## Hybrid Style Rule

If the user asks for a hybrid, assign each style to a layer: `live-action product photography with illustrated UI overlays` is clearer than mixing many named influences. Keep character design, environment, lighting, and VFX in compatible registers.

Load `[ref:2d-anime-grammar]` when the style is 2D, anime, or cel-based — it covers layer grammar, burst-versus-held motion, impact frames, smears, rostrum-camera language, and the no-lens rule for stylized work.

## Source-Look Lock

Field-observed from Chinese practice: realism styles stabilize when the prompt names the capture source and embraces its artifacts instead of fighting them. Classify the intended look, then lock its signature flaws deliberately:

| Source look | Lock its artifacts |
|---|---|
| Phone-shot daily / UGC | `vertical handheld phone footage, slight grip sway, auto-exposure shifts, ambient room sound` |
| Livestream | `fixed webcam framing, flat ring light, mild compression, real-time caption pacing` |
| Security / dashcam | `locked high-angle camera, timestamp burn-in feel, low-light noise, no camera response to events` |
| Vintage film | `grainy film texture, gate weave, halation around highlights, era-correct contrast` |
| Studio commercial | `controlled reflections, clean background, polished material detail, zero handheld motion` |

The flaw vocabulary is the style: faux-UGC that looks too clean reads as fake twice over.

## Sequence State

When sequence state is present, inherit medium grammar, current clip scope, continuity locks, exact reference tags, canonical design, accepted transient state, and reserved future beats. Style may color the clip, but it cannot change identity, wardrobe, product design, surface profile, or events reserved for later.

## Output Contract

Return a safe style descriptor, any protected-name rewrite, and one integrated prompt sentence.
