![Seedance 2.0 Skill OS cinematic command-center hero: brief, references, prompt, post, QC, subtitles, audio waveform, and shot cards](assets/hero-command-center.png)

# Seedance 2.0 Skill OS

**Intent-first AI filmmaking for Seedance 2.0.**

Text-to-video · Image-to-video · Video-to-video · Reference-to-video · Audio-aware prompting · Copyright-safe rewrites · Agent Skills

[![Version](https://img.shields.io/badge/version-5.4.7-111827?labelColor=0f172a)](#changelog)
[![Skills](https://img.shields.io/badge/sub--skills-24-0ea5e9?labelColor=0f172a)](#skill-map)
[![References](https://img.shields.io/badge/references-45-8b5cf6?labelColor=0f172a)](#reference-library)
[![Evals](https://img.shields.io/badge/evals-58-22c55e?labelColor=0f172a)](#validation)
[![License](https://img.shields.io/badge/license-MIT-f59e0b?labelColor=0f172a)](LICENSE)

Author: [Iamemily2050 (@iamemily2050)](https://github.com/Emily2040) · [Instagram](https://instagram.com/iamemily2050) · [X](https://x.com/iamemily2050) · [Website](https://iamemily2050.com)

Platform context: [ByteDance Seedance 2.0](https://seed.bytedance.com/en/seedance2_0) · Dreamina · Jimeng · Doubao · [Volcengine Ark](https://www.volcengine.com/docs/82379/2291680?lang=zh) · [BytePlus ModelArk](https://docs.byteplus.com/en/docs/ModelArk/2291680) · [Runway Seedance 2](https://docs.dev.runwayml.com/guides/seedance/) · fal

Updated: **2026-06-11** · **v5.4.7 multilingual anti-slop layer, English vocabulary, and fact-check hardening**

---

## Why this repository exists

Seedance 2.0 Skill OS is a modular agent-skill package for directing Seedance 2.0 video generations. It is built around a simple principle: **direct the model, do not micro-manage the frame**.

The repository gives an AI assistant a public, auditable operating system for Seedance work. It defines when to interview, when to write a compact prompt, when to load a technical reference, when to rewrite unsafe IP content, and when to troubleshoot a bad generation.

## What This Skill Does

This skill package turns Seedance 2.0 work into a repeatable assistant workflow:

- Routes vague ideas into short creative interviews instead of premature prompt dumps.
- Writes full or compressed prompts for T2V, I2V, V2V, R2V, FLF2V, edit, extend, audio-aware, and first/last-frame workflows.
- Separates every reference asset by role: identity, environment, motion, camera rhythm, audio tempo, style, or endpoint.
- Keeps model and platform claims source-dated so API, pricing, region, quota, and model-ID details are not guessed.
- Provides deeper multilingual cinematic vocabulary in English, Chinese, Japanese, Korean, Spanish, and Russian, including role binding, first/last-frame phrasing, edit/extend wording, safety wording, and audio cues.
- Adds original community-informed examples for Chinese-English, Russian-English, Japanese-English, Korean-English, and Spanish-English prompt structures.
- Adds professional filmmaker workflows for treatment-to-shot-list planning, shot contracts, continuity ledgers, ACES/color handoff, audio post, subtitles/localization, aspect-ratio variants, campaign cutdowns, delivery/QC, and client review packets.
- Handles safe false-positive repairs by clarifying benign production context, not by hiding unsafe intent.
- Rewrites unsafe celebrity, protected IP, private-person, brand, logo, song, or voice requests into safer creative equivalents.
- Diagnoses failed outputs with concrete repair levers: camera, lighting, motion, reference role, duration, framing, audio, or safety wording.
- Ships validation scripts, eval cases, source data, and design checks so maintainers can review changes before release.

## Professional Filmmaker Scope

This package is designed for working film and commercial teams, not only for casual prompt writing. It can help an agent produce the artifact the role actually needs:

| Role | What the skill should produce |
|---|---|
| Director | treatment, scene beat, performance intent, coverage, shot endpoint, review notes |
| Cinematographer / DP | shot contract, shot size, lens feel, camera support, movement, blocking, lighting continuity |
| Producer / agency | client brief, rights map, approval gates, campaign variants, risk log, review packet |
| Editor | selects plan, edit/extend decision, continuity handoff, handles, textless needs, conform notes |
| Colorist | color intent, ACES-aware handoff, show-look notes, HDR/SDR caveats, product-color checks |
| Sound team | dialogue map, ambience/SFX/music layers, sync cues, stems, M&E, dubbing and loudness notes |
| Localization team | subtitles, SDH captions, forced narratives, dubbing guide, market copy, textless plates |
| Delivery/QC | frame rate, aspect ratio, crop, color, loudness, captions, metadata, naming, human QC checklist |

For these requests, the skill should not stop at a single prompt. It should return the production object first, then the Seedance prompt or prompt batch that fits inside that plan.

## Start Here

| User situation | Load first | Output |
|---|---|---|
| “I have a vague idea.” | [`seedance-interview`](skills/seedance-interview/SKILL.md) | A focused creative brief and next prompt path. |
| “I know the scene I want.” | [`seedance-prompt`](skills/seedance-prompt/SKILL.md) | A production-ready Seedance prompt. |
| “Make it short and strong.” | [`seedance-prompt-short`](skills/seedance-prompt-short/SKILL.md) | A compressed 30–100 word prompt. |
| “I have an image/video/audio reference.” | [`reference-workflow`](references/reference-workflow.md) | A role map for every reference asset. |
| “Use this as first frame and that as final frame.” | [`first-last-frame-guide`](references/first-last-frame-guide.md) | A continuous transition with endpoint locks. |
| “It failed or looks bad.” | [`seedance-troubleshoot`](skills/seedance-troubleshoot/SKILL.md) | A root-cause diagnosis and repaired prompt. |
| “This uses a character, brand, celebrity, or real person.” | [`seedance-copyright`](skills/seedance-copyright/SKILL.md) | A safer rewrite preserving the creative function. |
| “I need this for a film, client, campaign, or delivery.” | [`pro-filmmaking-standards`](references/pro-filmmaking-standards.md) | A professional workflow plan, role-specific artifact, and prompt path. |
| “Turn this treatment into shots.” | [`shot-list-continuity`](references/shot-list-continuity.md) | Shot list, continuity ledger, and prompt batch structure. |
| “This needs subtitles, dubbing, color, sound, or QC.” | [`delivery-qc`](references/delivery-qc.md) | Post, localization, audio, color, and delivery checks. |
| “I need API, Runway, pricing, model ID, or production workflow guidance.” | [`api-workflow`](references/api-workflow.md) | A source-gated operational checklist. |
| “Is this Seedance Pro/Fast/V2?” | [`model-name-map`](references/model-name-map.md) | Source-dated naming and surface caveats. |
| “I want Chinese/Russian/Japanese/Korean/Spanish or mixed-language prompt examples.” | [`multilingual-community-examples`](references/multilingual-community-examples.md) | Safe community-informed structures and false-positive repair patterns. |
| “I am installing or reviewing this as an agent skill.” | [`agent-compatibility`](references/agent-compatibility.md) | Codex/Agent Skills structure and distribution notes. |

## Current Status Rule

Seedance platform behavior changes quickly. Before making factual claims about API availability, face or portrait authorization, upload limits, pricing, regional availability, or model names, load [`references/api-status.md`](references/api-status.md) and check its `last_verified` date.

As of 2026-06-11, public official sources describe Seedance 2.0 as supporting text, image, audio, and video inputs. Official launch and model-card material says references can include up to 9 images, 3 video clips, and 3 audio clips.

Volcengine's May 29 docs keep `doubao-seedance-2-0-260128` and `doubao-seedance-2-0-fast-260128` visible as current Ark model IDs and document first/last-frame role usage on that surface. Runway documents `seedance2` with 5-15 second duration and optional image, video, and audio references.

Access, pricing, upload limits, regions, resolution, audio-combination rules, and authorization requirements remain surface-specific.

## Research Snapshot

The v5.4 release line adds a dated research layer for safer data mining and platform claims:

- [`research-2026-05-30.md`](references/research-2026-05-30.md) records official and field-observed signals.
- [`platform-surface-matrix.md`](references/platform-surface-matrix.md) separates model capability from Dreamina/Jimeng, Volcengine/Ark, BytePlus, ComfyUI, and wrapper behavior.
- [`model-name-map.md`](references/model-name-map.md) prevents `Seedance 2.0`, `Seedance 2.0 Fast`, `Seedance V2`, and ambiguous Pro labels from being mixed together.
- [`community-source-methodology.md`](references/community-source-methodology.md) explains how to mine public prompt corpora without copying unsafe examples.
- [`multilingual-community-examples.md`](references/multilingual-community-examples.md) captures safe mixed-language and localized prompt structures from community pattern mining.
- [`pro-filmmaking-standards.md`](references/pro-filmmaking-standards.md) adds industry workflow boundaries for shot lists, continuity, color, audio, localization, and delivery.

## Operating System At A Glance

![Seedance 2.0 Skill OS infographic: source registry, prompt router, multimodal references, safety gates, and eval loop](assets/skill-os-infographic.png)

The operating-system map stays simple for GitHub readability; the visual gallery below adds the text-rich professional infographics. Together they represent the six lanes this package keeps separate:

- Research sources: dated official, academic, platform, and community evidence.
- Production spine: brief, shot list, continuity, post handoff, localization, and delivery/QC.
- Prompt router: interview, prompt writing, compression, recipes, and troubleshooting.
- Multimodal references: image, video, audio, first-frame, last-frame, and role-bound assets.
- Safety gates: IP, likeness, voice, brand, real-person, filter, and platform-policy checks.
- Quality evals: schema checks, source freshness, vocabulary integrity, design audit, and behavior cases.

## Visual Gallery

The README now includes a committed visual set rather than a single generic hero. These generated bitmap assets are paired with searchable Markdown so the images can be cinematic while the repo remains auditable.

### Hero Shots

![Seedance 2.0 command-center hero showing brief, references, prompt, post, QC, subtitles, audio waveform, and shot cards](assets/hero-command-center.png)

![Global filmmaker mode hero showing director, DP, editor, colorist, sound mixer, localization lead, and QC lead on a cinematic production stage](assets/hero-global-filmmaker-mode.png)

### Text-Rich Infographics

![What this skill can do infographic: brief, references, prompt, generate, post, deliver](assets/infographic-skill-capabilities.png)

![CDN video delivery map infographic: creator, origin, CDN edge, global review, delivery, fast playback, regional cache, version control, and QC before publish](assets/infographic-cdn-delivery-map.png)

![Reference role map infographic: image equals identity, video equals motion, audio equals timing](assets/infographic-reference-role-map.png)

![Production to delivery infographic: brief, shot list, generate, edit, localize, QC](assets/infographic-production-delivery.png)

![Professional QC stack infographic: picture, color, audio, text, rights, metadata](assets/infographic-professional-qc-stack.png)

## Skill Map

![Seedance 2.0 cinematic skill map: modular skill clusters around an AI filmmaking director console](assets/skill-map-cinematic.png)

### Core Pipeline

| Skill | Use when |
|---|---|
| [`seedance-interview`](skills/seedance-interview/SKILL.md) | The idea is vague, undeveloped, or needs creative direction. |
| [`seedance-interview-short`](skills/seedance-interview-short/SKILL.md) | The user wants a fast brief, not a long interview. |
| [`seedance-prompt`](skills/seedance-prompt/SKILL.md) | The user needs a complete prompt from a clear concept. |
| [`seedance-prompt-short`](skills/seedance-prompt-short/SKILL.md) | The prompt must be compressed for stronger Seedance performance. |
| [`seedance-camera`](skills/seedance-camera/SKILL.md) | Camera behavior, lens feel, shot scale, or movement must be specified. |
| [`seedance-motion`](skills/seedance-motion/SKILL.md) | Body movement, object motion, choreography, or physical action matters. |
| [`seedance-lighting`](skills/seedance-lighting/SKILL.md) | Mood, time of day, atmosphere, or light transition drives the shot. |
| [`seedance-characters`](skills/seedance-characters/SKILL.md) | Character identity, multi-character blocking, or consistency matters. |
| [`seedance-style`](skills/seedance-style/SKILL.md) | The user needs a visual style without unsafe studio/franchise borrowing. |
| [`seedance-vfx`](skills/seedance-vfx/SKILL.md) | Particles, destruction, energy, weather, magic, or transformation effects matter. |
| [`seedance-audio`](skills/seedance-audio/SKILL.md) | Dialogue, lip-sync, music, ambience, or audio-reference behavior matters. |
| [`seedance-pipeline`](skills/seedance-pipeline/SKILL.md) | The user asks about API, web workflow, ComfyUI, post-production, or integration. |
| [`seedance-recipes`](skills/seedance-recipes/SKILL.md) | The user wants a genre template or repeatable production recipe. |
| [`seedance-troubleshoot`](skills/seedance-troubleshoot/SKILL.md) | Output quality is poor, unstable, blurry, off-prompt, or blocked. |

### Governance and Quality

| Skill | Use when |
|---|---|
| [`seedance-copyright`](skills/seedance-copyright/SKILL.md) | Protected IP, public figures, real people, brands, logos, songs, or exact scenes appear. |
| [`seedance-antislop`](skills/seedance-antislop/SKILL.md) | Prompt language is generic, bloated, or filled with empty quality boosters. |
| [`seedance-filter`](skills/seedance-filter/SKILL.md) | A benign prompt is blocked or degraded by over-broad filtering. Repairs false positives by clarifying legitimate production context, never by hiding intent. |

### Multilingual Vocabulary

| Skill | Use when |
|---|---|
| [`seedance-vocab-en`](skills/seedance-vocab-en/SKILL.md) | English wording is slop-heavy, padded with empty quality words, or tripping false-positive filters. |
| [`seedance-vocab-zh`](skills/seedance-vocab-zh/SKILL.md) | Chinese prompt compression or Mandarin cinematic vocabulary is needed. |
| [`seedance-vocab-ja`](skills/seedance-vocab-ja/SKILL.md) | Japanese cinematic vocabulary is needed. |
| [`seedance-vocab-ko`](skills/seedance-vocab-ko/SKILL.md) | Korean cinematic vocabulary is needed. |
| [`seedance-vocab-es`](skills/seedance-vocab-es/SKILL.md) | Spanish cinematic vocabulary is needed. |
| [`seedance-vocab-ru`](skills/seedance-vocab-ru/SKILL.md) | Russian cinematic vocabulary is needed. |
| [`seedance-examples-zh`](skills/seedance-examples-zh/SKILL.md) | Chinese working examples or example-safe rewrites are needed. |

## Reference Library

| Reference | Purpose |
|---|---|
| [`api-status.md`](references/api-status.md) | Current dated platform and API status. |
| [`source-registry.md`](references/source-registry.md) | Source hierarchy and evidence labels. |
| [`research-2026-05-30.md`](references/research-2026-05-30.md) | Dated source and field-observation snapshot. |
| [`agent-compatibility.md`](references/agent-compatibility.md) | Agent Skills structure, Codex compatibility, and packaging notes. |
| [`api-workflow.md`](references/api-workflow.md) | Volcengine, BytePlus, Runway, async task, reference-file, pricing, and production workflow checklist. |
| [`capability-map.md`](references/capability-map.md) | Design into model strengths and around known limits before prompting. |
| [`allocation-model.md`](references/allocation-model.md) | Where one generation spends its fidelity budget: identity vs motion vs scene density. |
| [`multishot-grammar.md`](references/multishot-grammar.md) | Shot labels, the shots-times-seconds budget, and cut grammar inside one generation. |
| [`2d-anime-grammar.md`](references/2d-anime-grammar.md) | Cel/anime medium grammar: layers, burst-vs-held motion, the no-lens rule. |
| [`pro-filmmaking-standards.md`](references/pro-filmmaking-standards.md) | Professional production spine and source boundaries for film, commercial, post, localization, and delivery work. |
| [`cinematography-shot-language.md`](references/cinematography-shot-language.md) | Shot contracts, shot size, lens feel, camera support, movement, blocking, and coverage language. |
| [`shot-list-continuity.md`](references/shot-list-continuity.md) | Treatment-to-shot-list workflow, continuity ledger, and professional handoff fields. |
| [`color-pipeline-aces.md`](references/color-pipeline-aces.md) | ACES-aware color intent, show-look notes, HDR/SDR handoff, and color QC boundaries. |
| [`aspect-ratio-delivery.md`](references/aspect-ratio-delivery.md) | Creative framing, delivery containers, social cutdowns, safe areas, and textless/version planning. |
| [`subtitles-localization.md`](references/subtitles-localization.md) | Subtitle, SDH, forced narrative, dubbing, textless, and cultural localization planning. |
| [`audio-post-delivery.md`](references/audio-post-delivery.md) | Dialogue, SFX, music, stems, M&E, loudness, dubbing, and sync handoff guidance. |
| [`delivery-qc.md`](references/delivery-qc.md) | Professional preflight for picture, color, audio, captions, rights, metadata, versioning, and human QC. |
| [`examples-by-mode.md`](references/examples-by-mode.md) | Mode-specific prompt examples for T2V, I2V, V2V, R2V, FLF2V, edit, extend, and troubleshooting. |
| [`multilingual-community-examples.md`](references/multilingual-community-examples.md) | Original Chinese, Russian, Japanese, Korean, Spanish, and mixed-language prompt structures from safe community pattern mining. |
| [`platform-surface-matrix.md`](references/platform-surface-matrix.md) | Model-vs-surface claim boundaries. |
| [`model-name-map.md`](references/model-name-map.md) | Seedance naming, Fast variant, and Pro-label caveats. |
| [`first-last-frame-guide.md`](references/first-last-frame-guide.md) | FLF2V, first-frame, and last-frame prompting. |
| [`field-observed-tips.md`](references/field-observed-tips.md) | Safe practitioner workflow patterns. |
| [`community-source-methodology.md`](references/community-source-methodology.md) | Safe public corpus mining and labeling rules. |
| [`platform-constraints.md`](references/platform-constraints.md) | Stable platform-risk rules. |
| [`quick-ref.md`](references/quick-ref.md) | Compact routing and prompt checklist. |
| [`reference-workflow.md`](references/reference-workflow.md) | How to map image, video, audio, and storyboard references. |
| [`i2v-guide.md`](references/i2v-guide.md) | Image-to-video best practices. |
| [`prompt-examples.md`](references/prompt-examples.md) | Safe copy-paste prompt examples. |
| [`genre-guides.md`](references/genre-guides.md) | Genre-specific prompt patterns. |
| [`storytelling-framework.md`](references/storytelling-framework.md) | Narrative design and visual layering. |
| [`intent-vs-precision.md`](references/intent-vs-precision.md) | The intent-first philosophy. |
| [`audio-guide.md`](references/audio-guide.md) | Audio, dialogue, beat-sync, and lip-sync guidance. |
| [`anti-slop-lexicon.md`](references/anti-slop-lexicon.md) | Weak phrase replacement table. |
| [`filter-vocab.md`](references/filter-vocab.md) | Safer wording for blocked/degraded prompts. |
| [`frontend-design-system.md`](references/frontend-design-system.md) | README and SVG design standards. |
| [`json-schema.md`](references/json-schema.md) | Structured prompt wrapper for pipelines. |
| [`eval-rubric.md`](references/eval-rubric.md) | How to judge eval outputs. |
| [`progressive-disclosure.md`](references/progressive-disclosure.md) | Root, sub-skill, and reference boundaries. |
| [`vocab/zh.md`](references/vocab/zh.md) | Chinese cinematic vocabulary for compact prompts. |
| [`vocab/ja.md`](references/vocab/ja.md) | Japanese cinematic vocabulary for compact prompts. |
| [`vocab/ko.md`](references/vocab/ko.md) | Korean cinematic vocabulary for compact prompts. |
| [`vocab/es.md`](references/vocab/es.md) | Spanish cinematic vocabulary for compact prompts. |
| [`vocab/ru.md`](references/vocab/ru.md) | Russian cinematic vocabulary for compact prompts. |

## Install

Client support for Agent Skills is still tool-specific. Codex documents a skill as a directory with a required `SKILL.md`, optional `scripts/`, `references/`, `assets/`, and optional `agents/` metadata.

Codex scans `.agents/skills` locations from the working directory upward, plus user/admin/system skill locations. A repository root with `SKILL.md` is shaped like a skill folder, but it still needs to be installed/copied under a scanned skills directory or distributed as a plugin for automatic discovery.

This repository now includes `agents/openai.yaml` and a local Codex installer. To install it for this Windows workstation or any local Codex profile, run:

```bash
python scripts/install_codex_skill.py --force
```

The installer copies the repository into `$CODEX_HOME/skills/seedance-20` when `CODEX_HOME` is set, otherwise into `~/.codex/skills/seedance-20`. Restart Codex after installation so `$seedance-20` appears in the available skills list.

This repository keeps dense facts in references so the active skill stays small.

If your client supports installing a skill directly from a GitHub repository, use this repository URL:

```text
https://github.com/Emily2040/seedance-2.0
```

For manual installation, copy this repository into the skill directory used by your agent client. The directory name should match the root skill name, `seedance-20`. Treat the table below as common local targets to verify in your own client, not a universal support guarantee.

| Platform | Typical workspace path |
|---|---|
| Claude Code / OpenClaw | `.claude/skills/seedance-20/` |
| Codex-style agent workspace | `.agents/skills/seedance-20/` |
| Gemini CLI-style workspace | `.gemini/skills/seedance-20/` |
| GitHub Copilot workspace | `.github/skills/seedance-20/` |
| Cursor workspace | `.cursor/skills/seedance-20/` |
| Windsurf workspace | `.windsurf/skills/seedance-20/` |

## Validation

Run these checks before every release:

```bash
python scripts/validate_skills.py --strict
python scripts/content_audit.py --strict
python scripts/eval_schema_check.py --strict
python scripts/design_audit.py --strict
python scripts/source_registry_check.py --strict
python scripts/vocab_schema_check.py --strict
```

The CI workflow runs the same checks on push and pull request.

## Design Standard

The v5.4.5 front page uses multiple generated cinematic bitmap hero shots, text-rich infographics, a generated operating-system infographic, a generated cinematic skill-map infographic, and the cleaned v5.2 information architecture. The README should stay readable in GitHub mobile, dark mode, and narrow widths. SVG assets must include `<title>` and `<desc>` elements, use internal CSS only, and avoid external fonts or scripts. See [`docs/frontend-redesign.md`](docs/frontend-redesign.md).

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md). Current release: **v5.4.7**.

## License

MIT © 2026 Iamemily2050 (@iamemily2050)
