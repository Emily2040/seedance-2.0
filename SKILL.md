---
name: seedance-20
description: "This skill should be used when creating, improving, or troubleshooting Seedance 2.0 video on any surface - Dreamina, Jimeng, CapCut, Doubao, Volcengine/Ark, BytePlus, Runway's Seedance route, or fal - including text/image/video/reference-to-video prompts, first/last frame, dialogue, lip-sync and audio, IP-safe rewrites, API, pricing and model-ID questions, and zh/ja/ko/es/ru prompt work. Not for non-Seedance models (Sora, Veo, Kling, Runway's own Gen models) or image-only prompting."
license: MIT
user-invocable: true
tags: [seedance]
metadata:
  version: "5.4.7"
---

# seedance-20

Seedance 2.0 operating loop for agent-directed video work. Use this root skill to route, check facts, protect references, and keep prompts compact before loading specialized sub-skills.

## Operating Loop

1. Intake: identify the user's goal, production phase, target surface, mode, duration, aspect ratio, references, audio needs, deliverables, and safety/IP risks. If intake surfaces a clear safety, IP, likeness, or evasion risk, jump straight to the safety gate (step 8) before any planning.
2. Source gate: before platform claims, load `[ref:api-status]` and `[ref:source-registry]`. For Runway, Volcengine, or fal specifics, also load `[ref:platform-surface-matrix]`.
3. Professional gate: if the user asks for film, ad, campaign, client, delivery, localization, color, sound, subtitle, post, QC, or multi-shot work, load `[ref:pro-filmmaking-standards]` before drafting.
4. Mode gate: choose T2V, I2V, V2V, R2V, FLF2V, edit, extend, or troubleshoot before writing prose.

   Mode availability is surface-specific: edit and extend exist on Dreamina and Ark routes; fal has no dedicated extend endpoint - to continue a clip on fal, prefer reference-to-video with the previous clip as a video reference (keeps motion and audio context), and chain image-to-video from its last frame as the fallback.

5. Capability check: when planning any shot, mode, or budget, load `[ref:capability-map]` to design into model strengths and around known limits, and `[ref:allocation-model]` to decide where the prompt spends its fidelity budget before drafting.
6. Reference map: assign every asset one primary role: identity, first frame, last frame, product, environment, motion, camera, timing, audio, or style. State what must not transfer.
7. Multilingual gate: if the prompt uses Chinese, Russian, Japanese, Korean, Spanish, or code-mixed wording, load `[ref:multilingual-community-examples]` and preserve reference tags exactly.
8. Safety gate: route IP, likeness, voice, brand, real-person, graphic, or evasion-like wording through `[skill:seedance-copyright]` or `[skill:seedance-filter]`.
9. Prompt build: route to `[skill:seedance-interview]`, `[skill:seedance-prompt]`, `[skill:seedance-prompt-short]`, or a domain skill for camera, motion, audio, characters, VFX, style, recipes, or pipeline.
10. Quality pass: run anti-slop, check one visible beat, one primary camera move, physical light, sound intent, continuity anchors, constraints, delivery caveats, and source-date caveats.
11. Repair loop: if output fails, diagnose root cause before adding adjectives; use `[skill:seedance-troubleshoot]`.

## Load Map

| Situation | Load |
|---|---|
| Vague idea or missing brief | `[skill:seedance-interview]` or `[skill:seedance-interview-short]` |
| Production prompt | `[skill:seedance-prompt]`, `[ref:quick-ref]`, `[ref:prompt-examples]` |
| Planning any shot, mode, or budget | `[ref:capability-map]` |
| Where the prompt spends fidelity: identity vs motion vs scene density | `[ref:allocation-model]`, `[ref:intent-vs-precision]` |
| Multi-shot prompt, cuts inside one clip, or shots-per-duration budget | `[ref:multishot-grammar]` |
| 2D, anime, or cel-style motion | `[ref:2d-anime-grammar]`, `[skill:seedance-style]` |
| Professional film, commercial, campaign, or delivery workflow | `[ref:pro-filmmaking-standards]`, `[ref:shot-list-continuity]`, `[ref:delivery-qc]` |
| Compact prompt or Chinese compression | `[skill:seedance-prompt-short]`, language vocab reference |
| Camera, lens, blocking, shot contract | `[skill:seedance-camera]`, `[ref:cinematography-shot-language]` |
| Image reference / first frame | `[ref:i2v-guide]`, `[ref:reference-workflow]` |
| First and last frame | `[ref:first-last-frame-guide]` |
| API, Runway, Volcengine, fal, workflow, pricing, model IDs | `[skill:seedance-pipeline]`, `[ref:api-workflow]`, `[ref:model-name-map]` |
| Color, ACES, HDR/SDR, aspect ratio, subtitles, audio post, or QC | `[ref:color-pipeline-aces]`, `[ref:aspect-ratio-delivery]`, `[ref:subtitles-localization]`, `[ref:audio-post-delivery]`, `[ref:delivery-qc]` |
| Genre template or examples | `[skill:seedance-recipes]`, `[ref:examples-by-mode]`, `[ref:genre-guides]` |
| Chinese/Russian/Japanese/Korean/Spanish or mixed-language examples | `[ref:multilingual-community-examples]`, language vocab reference |
| Slop-heavy or filter-tripping English wording | `[skill:seedance-vocab-en]`, `[skill:seedance-antislop]` |
| Bad result | `[skill:seedance-troubleshoot]` |

Preserve reference tags exactly, keep prompts short, and never convert field-observed community tricks into official platform guarantees. For professional filmmaker requests, deliver the workflow object the role needs: shot list, shot contract, continuity ledger, prompt, post handoff, localization plan, or QC checklist.
