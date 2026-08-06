<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/hero-light.svg">
  <img alt="Seedance 2.0 Skill OS — Direct the model. Don't micro-manage the frame." src="assets/hero-dark.svg" width="100%">
</picture>

An agent that reads the scene before it writes the prompt: text, image, video, and reference-to-video for Seedance 2.0, with native audio, IP-safe rewrites, source-dated platform facts, and reader paths in six languages.

English · [中文](docs/README.zh.md) · [日本語](docs/README.ja.md) · [한국어](docs/README.ko.md)

[Start here](#start-here) · [Final hardening](#final-hardening-contract) · [Skill map](#skill-map) · [Reference library](#reference-library) · [Visual gallery](#visual-gallery) · [Install](#install)

---

`v6.7.0` · MIT · updated 2026-08-05 · [what changed](CHANGELOG.md)

Author: [Iamemily2050 (@iamemily2050)](https://github.com/Emily2040) · [Instagram](https://instagram.com/iamemily2050) · [X](https://x.com/iamemily2050) · [Website](https://iamemily2050.com)

Surfaces: [ByteDance Seedance 2.0](https://seed.bytedance.com/en/seedance2_0) · Dreamina · Jimeng · Doubao · [Volcengine Ark](https://www.volcengine.com/docs/82379/2291680?lang=zh) · [BytePlus ModelArk](https://docs.byteplus.com/en/docs/ModelArk/2291680) · [Runway Seedance 2](https://docs.dev.runwayml.com/guides/models/) · fal · provider/router surfaces tracked in [`platform-surface-matrix.md`](references/platform-surface-matrix.md)

---

## Direct the scene, don't decorate it

Most tools ask the model for a "cinematic look." A director asks what the scene is *doing* — then makes the camera, lens, light, blocking, performance, and sound all serve one intention, in a single recognizable voice, across an entire story.

The mandatory [**Director's Read**](references/directors-read.md) encodes that judgment before every narrative, story, or performance prompt: function, turn, POV, power shift, objective, obstacle/tactic, contradiction, one visible suppressed behavior, one non-transferable detail, and one explicit genre refusal.

Utility, packshot, functional product, and abstract work take a separate lane so the skill does not invent drama. The deeper [**directing engine**](references/directing-engine.md) then turns the read into a coherent camera, light, blocking, performance, and sound setup instead of stacking adjectives.

**Ask for "cinematic":** `epic cinematic shot of a woman reading a letter, emotional, beautiful lighting`

**Direct it:** `A woman at a kitchen table reads the letter twice, then her hands lower it and go still. Camera: medium close-up at eye level, a slow push-in that settles when her hands stop. Soft window light keeps her face plain. Sound: room tone, one chair scrape, near-silence — the realization lands in the stilled hands, not a word.`

The order is part of the direction: the subject and her action take the opening words — where the model locks in who the shot is about — and the camera, light, and sound follow.

It then holds one directorial voice across every short clip of a long story, and ships with **33 worked derivations** — product, music video, horror, anime, action, comedy, documentary, high fashion, sci-fi, and more — each shown end to end.

> A reveal is not lit, framed, blocked, or performed like a goodbye. The engine refuses the generic answer and derives the specific one.

## Multilingual Start / 多语言入门 / 多言語スタート / 다국어 시작

Seedance 2.0 Skill OS is English-readable, but the v6 line gives Chinese, Japanese, and Korean readers first-class entry points, active example skills, and language-specific prompt guidance.
Keep reference tags exactly as written (`@Image1`, `@Video1`, `@Audio1`, `@图片1`, `@视频1`) in every language.
Static checks preserve structure and tokens; linguistic and authorship questions follow the independent human-review protocol.
Use the independent [`multilingual language review`](references/multilingual-native-review.md) rubric for language-quality review.
Every material score must cite its pinned criterion-specific localized candidate text and carry a criterion-specific reason, never the common brief alone.
Completed records belong in the CI-validated evidence artifact; it is currently empty, so no completed native-language review is claimed.

| Language | Start path | Reader note |
|---|---|---|
| English | [`seedance-prompt`](skills/seedance-prompt/SKILL.md), [`seedance-sequence`](skills/seedance-sequence/SKILL.md), [`references/vocab/en.md`](references/vocab/en.md) | Use precise production English: one visible beat, one camera move, real light, and clear reference roles. |
| 中文 | [`中文指南`](docs/README.zh.md), [`seedance-vocab-zh`](skills/seedance-vocab-zh/SKILL.md), [`seedance-examples-zh`](skills/seedance-examples-zh/SKILL.md), [`references/vocab/zh.md`](references/vocab/zh.md) | 中文用户可从角色锁定、首尾帧、运镜、动作节奏开始；提示词要短、具体、保留参考标签，不把字幕交给模型生成。 |
| 日本語 | [`日本語ガイド`](docs/README.ja.md), [`seedance-vocab-ja`](skills/seedance-vocab-ja/SKILL.md), [`seedance-examples-ja`](skills/seedance-examples-ja/SKILL.md), [`references/vocab/ja.md`](references/vocab/ja.md) | 日本語では、人物の同一性、衣装、構図、動きの終点を明確に書き、字幕や広告コピーは後処理で追加します。 |
| 한국어 | [`한국어 가이드`](docs/README.ko.md), [`seedance-vocab-ko`](skills/seedance-vocab-ko/SKILL.md), [`seedance-examples-ko`](skills/seedance-examples-ko/SKILL.md), [`references/vocab/ko.md`](references/vocab/ko.md) | 한국어 프롬프트는 인물 고정, 카메라 움직임, 조명, 사운드를 짧게 분리하고 자막과 문구는 편집 단계에서 넣습니다. |

New here? Each language also has a 5-minute quickstart: [English](docs/QUICKSTART.md) · [中文](docs/QUICKSTART.zh.md) · [日本語](docs/QUICKSTART.ja.md) · [한국어](docs/QUICKSTART.ko.md) · [Español](docs/QUICKSTART.es.md) · [Русский](docs/QUICKSTART.ru.md).

For longer stories in any language, start with [`seedance-sequence`](skills/seedance-sequence/SKILL.md). For the next part of an accepted clip, use [`seedance-continuation`](skills/seedance-continuation/SKILL.md) and update the observed final state before writing the next prompt.

## Why this repository exists

Seedance 2.0 Skill OS is a modular agent-skill package for directing Seedance 2.0 video generations. It is built around a simple principle: **direct the model, do not micro-manage the frame**.

The repository gives an AI assistant a public, auditable operating system for Seedance work. It defines when to interview, when to write a compact prompt, when to load a technical reference, when to rewrite unsafe IP content, and when to troubleshoot a bad generation.

## What This Skill Does

This skill package turns Seedance 2.0 work into a repeatable assistant workflow:

- Routes vague ideas into short creative interviews instead of premature prompt dumps.
- Directs each scene before drafting: reads its dramatic function, sets one directorial voice, and makes camera, light, blocking, performance, and sound serve a single intention instead of a generic "cinematic" look - and holds that voice across every clip of a long story.
- Writes full or compressed prompts for T2V, I2V, V2V, R2V, FLF2V, edit, extend, audio-aware, and first/last-frame workflows.
- Separates every reference asset by role: identity, environment, motion, camera rhythm, audio tempo, style, or endpoint.
- Keeps model and platform claims source-dated so API, pricing, region, quota, and model-ID details are not guessed.
- Plans into model strengths before drafting: a capability map, a fidelity-allocation model, and a working model of the generator's mechanics that explains why every rule works.
- Runs the shoot like a producer after generation: five-verdict take triage, one-variable retakes, attempt budgets, and cost-aware drafting.
- Provides front-page reader paths plus deeper multilingual cinematic vocabulary in English, 中文, 日本語, 한국어, Spanish, and Russian, including role binding, first/last-frame phrasing, edit/extend wording, safety wording, audio cues, continuation wording, and post-production text handling.
- Adds original community-informed examples for Chinese, Japanese, Korean, Russian-English, and Spanish-English prompt structures.
- Adds professional filmmaker workflows for treatment-to-shot-list planning, shot contracts, continuity ledgers, ACES/color handoff, audio post, subtitles/localization, aspect-ratio variants, campaign cutdowns, delivery/QC, and client review packets.
- Handles safe false-positive repairs by clarifying benign production context, not by hiding unsafe intent.
- Rewrites unsafe celebrity, protected IP, private-person, brand, logo, song, or voice requests into safer creative equivalents.
- Diagnoses failed outputs with concrete repair levers: camera, lighting, motion, reference role, duration, framing, audio, or safety wording.
- Ships validation scripts, eval cases, source data, and design checks so maintainers can review changes before release.

## Final hardening contract

The 2026-08-05 audit closed four concrete gaps in the current v6.7.0 tree:

| Boundary | Current behavior |
|---|---|
| Frame extraction | `extract_last_frame.py` probes the selected FFmpeg binary once, prefers `-fps_mode passthrough`, and falls back to legacy `-vsync 0`. The real-frame path was verified with FFmpeg 8.1.1 and 9.0. |
| Copyable prompts | Generic reference-package examples use canonical `@Video1` and `@Image1` when the repository authors the tag; user- or interface-supplied spellings such as `[Video 1]` and `@Image 1` remain byte-preserved. Continuations begin from accepted footage's observed end state, and showcase prompts carry brief-specific behavior, props, timing, sound, and endpoints. |
| Evaluator ledgers | A new ledger is published from a retained file descriptor or handle relative to a retained directory descriptor or handle. Late destination claimants and namespace substitutes remain untouched; unsupported safe-publication paths fail closed. |
| Windows release tooling | Runner trust follows the exact venv launcher CPython installs across 3.11–3.13, including the 3.13 launcher variants. The Windows CI matrix exercises all three supported versions. |

These checks verify repository contracts, prompt structure, and the tested local tooling. They do not guarantee the subjective quality of every generated clip, prove that every third-party agent host auto-loads the skill, or replace a live Seedance generation benchmark. See the [v6.7.0 release note](docs/RELEASE_v6.7.0.md) for the full audit result.

## Making Videos Longer Than One Generation

Do not blindly ask the skill to extend the original prompt. A continuation must be based on accepted generated footage because Seedance may not end exactly where the original prompt expected.

1. Describe the complete idea and how it ends.
2. The skill divides it into connected clips.
3. Generate Clip 01.
4. Return the generated clip or its final frame.
5. The skill records what actually happened.
6. It writes Clip 02 from the real ending.
7. Repeat until the planned final outcome is reached.

The project state is the source of truth. The clip contract is the current production task. The prompt is a compiled instruction for only that task. Accepted generated footage determines what happens next.

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
| “This is a longer story / make it three connected clips.” | [`seedance-sequence`](skills/seedance-sequence/SKILL.md) | Full story spine, continuity bible, sequence map, Clip 01 contract, and Clip 01 prompt only. |
| “Continue this video / make the next part.” | [`seedance-continuation`](skills/seedance-continuation/SKILL.md) | A source-gated continuation from accepted footage or a request for the missing clip/final frame. |
| “I know the scene I want.” | [`seedance-prompt`](skills/seedance-prompt/SKILL.md) | A production-ready Seedance prompt. |
| “Make it actually feel directed, not just cinematic.” | [`directing-engine`](references/directing-engine.md) | One intention per scene, a coherent camera/light/blocking/performance/sound setup, and one directorial voice across the story. |
| “Make the story or performance specific before writing the prompt.” | [`directors-read`](references/directors-read.md) | A mandatory narrative read, a no-fabricated-drama utility boundary, and visible or audible prompt carriers. |
| “Make it short and strong.” | [`seedance-prompt-short`](skills/seedance-prompt-short/SKILL.md) | A compressed 30–100 word prompt. |
| “I have an image/video/audio reference.” | [`reference-workflow`](references/reference-workflow.md) | A role map for every reference asset. |
| “Use this as first frame and that as final frame.” | [`first-last-frame-guide`](references/first-last-frame-guide.md) | A continuous transition with endpoint locks. |
| “The take is 80% right - regenerate or keep?” | [`retake-protocol`](references/retake-protocol.md) | A triage verdict, the one-variable retake, and an attempt budget. |
| “It failed or looks bad.” | [`seedance-troubleshoot`](skills/seedance-troubleshoot/SKILL.md) | A root-cause diagnosis and repaired prompt. |
| “Why did that happen?” | [`model-mechanics`](references/model-mechanics.md) | The mechanism behind the failure and the lever that works with it. |
| “This uses a character, brand, celebrity, or real person.” | [`seedance-copyright`](skills/seedance-copyright/SKILL.md) | A safer rewrite preserving the creative function. |
| “I need this for a film, client, campaign, or delivery.” | [`pro-filmmaking-standards`](references/pro-filmmaking-standards.md) | A professional workflow plan, role-specific artifact, and prompt path. |
| “Turn this treatment into shots.” | [`shot-list-continuity`](references/shot-list-continuity.md) | Shot list, continuity ledger, and prompt batch structure. |
| “This needs subtitles, dubbing, color, sound, or QC.” | [`delivery-qc`](references/delivery-qc.md) | Post, localization, audio, color, and delivery checks. |
| “I need API, Runway, provider, pricing, model ID, or production workflow guidance.” | [`api-workflow`](references/api-workflow.md) | A source-gated operational checklist. |
| “Is this Seedance Pro/Fast/V2?” | [`model-name-map`](references/model-name-map.md) | Source-dated naming and surface caveats. |
| “I read or prompt in Chinese.” | [`中文指南`](docs/README.zh.md), [`seedance-vocab-zh`](skills/seedance-vocab-zh/SKILL.md), [`seedance-examples-zh`](skills/seedance-examples-zh/SKILL.md) | 中文角色锁定、首尾帧、运镜、动作、音频和安全改写路径。 |
| “I read or prompt in Japanese.” | [`日本語ガイド`](docs/README.ja.md), [`seedance-vocab-ja`](skills/seedance-vocab-ja/SKILL.md), [`seedance-examples-ja`](skills/seedance-examples-ja/SKILL.md) | 日本語の映画表現、参照ロール、動き、照明、音声、テキストレス納品の書き方。 |
| “I read or prompt in Korean.” | [`한국어 가이드`](docs/README.ko.md), [`seedance-vocab-ko`](skills/seedance-vocab-ko/SKILL.md), [`seedance-examples-ko`](skills/seedance-examples-ko/SKILL.md) | 한국어 카메라, 조명, 동작, 사운드, 안전한 참조 역할 작성법. |
| “I want Russian/Spanish or mixed-language prompt examples.” | [`multilingual-community-examples`](references/multilingual-community-examples.md) | Safe community-informed structures and false-positive repair patterns. |
| “I am installing or reviewing this as an agent skill.” | [`agent-compatibility`](references/agent-compatibility.md) | Codex/Agent Skills structure and distribution notes. |

## Current Status Rule

Seedance platform behavior changes quickly. Before making factual claims about API availability, face or portrait authorization, upload limits, pricing, regional availability, or model names, load [`references/api-status.md`](references/api-status.md) and check its `last_verified` date.

**This is a Seedance 2.0 skill.** ByteDance's [official Seedance 2.5 model page](https://seed.bytedance.com/en/seedance2_5)
confirms a separate newer line, and [Dreamina's official product page](https://dreamina.capcut.com/seedance/seedance-2-5) says it is live on Dreamina.
Neither primary page gives an exact launch date, and API or other-surface availability remained unconfirmed in the 2026-08-01 review.
The newer line is out of scope here — craft may transfer, but every platform number below is a 2.0 number.
Establish which line a surface runs before quoting one. See [`api-status.md`](references/api-status.md).

As of 2026-06-20, public official sources describe Seedance 2.0 as supporting text, image, audio, and video inputs. Official launch and model-card material says references can include up to 9 images, 3 video clips, and 3 audio clips.

Volcengine and BytePlus docs now expose Seedance 2.0 Mini as a surface-specific model lane. Treat `Seedance V2 Mini` as shorthand for Seedance 2.0 Mini only when the active surface confirms it. Current source-visible IDs include `doubao-seedance-2-0-mini-260615` on Volcengine and `dreamina-seedance-2-0-mini-260615` on BytePlus.

Volcengine docs also keep `doubao-seedance-2-0-260128` and `doubao-seedance-2-0-fast-260128` visible as Ark model IDs and document first/last-frame role usage on that surface. Runway documents `seedance2` with 5-15 second duration and optional image, video, and audio references.

Third-party provider/router pages tracked as of 2026-06-20 include EvoLink, OpenRouter, Kie.ai, PiAPI, LaoZhang, Runware, ModelsLab, AI/ML API, MuAPI, SeeGen, and Segmind.

Treat every endpoint, model ID, price, account requirement, face/reference policy, and output-rights claim as provider-specific and recheck live before implementation. China-facing searches should prefer official ByteDance, Volcengine, BytePlus, Doubao, Jimeng/Jianying, and CapCut/Jianying surfaces; workflow hosts or business-partner news are not public API providers unless they publish provider-owned API docs.

Access, pricing, upload limits, regions, resolution, audio-combination rules, and authorization requirements remain surface-specific.

## V6 Research and Claim Boundary

The v6 release line keeps a dated research layer for safer data mining, multilingual prompting, sequence-state work, and platform claims:

- [`research-2026-05-30.md`](references/research-2026-05-30.md) records official and field-observed signals.
- [`platform-surface-matrix.md`](references/platform-surface-matrix.md) separates model capability from Dreamina/Jimeng, Volcengine/Ark, BytePlus, ComfyUI, and provider/router behavior.
- [`model-name-map.md`](references/model-name-map.md) prevents `Seedance 2.0`, `Seedance 2.0 Fast`, `Seedance 2.0 Mini`, `Seedance V2`, and ambiguous Pro labels from being mixed together.
- [`community-source-methodology.md`](references/community-source-methodology.md) explains how to mine public prompt corpora without copying unsafe examples.
- [`multilingual-community-examples.md`](references/multilingual-community-examples.md) captures safe mixed-language and localized prompt structures from community pattern mining.
- [`pro-filmmaking-standards.md`](references/pro-filmmaking-standards.md) adds industry workflow boundaries for shot lists, continuity, color, audio, localization, and delivery.

## Operating System At A Glance

![Seedance 2.0 Skill OS operating diagram: seven gates feed the seedance-20 root, which routes to the core pipeline, governance, and multilingual vocabulary clusters, backed by the reference library and validators](assets/skill-map.svg)

The diagram is the contract: every request passes the gates, the root routes it, and the validators hold the line. Six lanes stay separate by design:

- Research sources: dated official, academic, platform, and community evidence.
- Production spine: brief, shot list, continuity, post handoff, localization, and delivery/QC.
- Prompt router: interview, prompt writing, compression, recipes, and troubleshooting.
- Multimodal references: image, video, audio, first-frame, last-frame, and role-bound assets.
- Safety gates: IP, likeness, voice, brand, real-person, filter, and platform-policy checks.
- Quality evals: schema checks, source freshness, vocabulary integrity, design audit, and behavior cases.

## Visual Gallery

<!-- installed-readme-gallery:start -->

Concept art for the system, generated and curated. Every image is paired with searchable alt text so the gallery stays auditable; the README's working visuals above are hand-built vector assets that follow the design standard.

### Hero Shots

![Seedance 2.0 command-center hero showing brief, references, prompt, post, QC, subtitles, audio waveform, and shot cards](assets/hero-command-center.png)

![Global filmmaker mode hero showing director, DP, editor, colorist, sound mixer, localization lead, and QC lead on a cinematic production stage](assets/hero-global-filmmaker-mode.png)

### Text-Rich Infographics

![What this skill can do infographic: brief, references, prompt, generate, post, deliver](assets/infographic-skill-capabilities.png)

![CDN video delivery map infographic: creator, origin, CDN edge, global review, delivery, fast playback, regional cache, version control, and QC before publish](assets/infographic-cdn-delivery-map.png)

![Reference role map infographic: image equals identity, video equals motion, audio equals timing](assets/infographic-reference-role-map.png)

![Production to delivery infographic: brief, shot list, generate, edit, localize, QC](assets/infographic-production-delivery.png)

![Professional QC stack infographic: picture, color, audio, text, rights, metadata](assets/infographic-professional-qc-stack.png)

### Operating-System Art

![Seedance 2.0 Skill OS infographic: source registry, prompt router, multimodal references, safety gates, and eval loop](assets/skill-os-infographic.png)

![Seedance 2.0 cinematic skill map: modular skill clusters around an AI filmmaking director console](assets/skill-map-cinematic.png)

<!-- installed-readme-gallery:end -->

## Skill Map

### Core Pipeline

| Skill | Use when |
|---|---|
| [`seedance-interview`](skills/seedance-interview/SKILL.md) | The idea is vague, undeveloped, or needs creative direction. |
| [`seedance-interview-short`](skills/seedance-interview-short/SKILL.md) | The user wants a fast brief, not a long interview. |
| [`seedance-sequence`](skills/seedance-sequence/SKILL.md) | The request is a long story, connected clip set, campaign sequence, or multi-generation scene. |
| [`seedance-continuation`](skills/seedance-continuation/SKILL.md) | The user wants to continue, extend, repair a tail, bridge known states, or re-anchor accepted footage. |
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
| [`seedance-examples-ja`](skills/seedance-examples-ja/SKILL.md) | Japanese working examples, continuation examples, textless localization patterns, or safe rewrites are needed. |
| [`seedance-examples-ko`](skills/seedance-examples-ko/SKILL.md) | Korean working examples, continuation examples, textless localization patterns, or safe rewrites are needed. |

## Reference Library

| Reference | Purpose |
|---|---|
| [`api-status.md`](references/api-status.md) | Current dated platform and API status. |
| [`source-registry.md`](references/source-registry.md) | Source hierarchy and evidence labels. |
| [`research-2026-05-30.md`](references/research-2026-05-30.md) | Dated source and field-observation snapshot. |
| [`agent-compatibility.md`](references/agent-compatibility.md) | Agent Skills structure, Codex compatibility, and packaging notes. |
| [`api-workflow.md`](references/api-workflow.md) | Volcengine, BytePlus, Runway, provider/router APIs, async task, reference-file, pricing, and production workflow checklist. |
| [`capability-map.md`](references/capability-map.md) | Design into model strengths and around known limits before prompting. |
| [`directors-read.md`](references/directors-read.md) | Mandatory narrative/story/performance read, non-narrative refusal boundary, and internal-to-visible compilation contract. |
| [`directing-engine.md`](references/directing-engine.md) | Read the scene, choose one intention, make every instrument cohere, hold one directorial voice, and shape the look across a long story. |
| [`directing-engine-genre-library.md`](references/directing-engine-genre-library.md) | 33 fully worked genre examples (product, music video, horror, anime, action, documentary, and more), loaded on demand. |
| [`model-mechanics.md`](references/model-mechanics.md) | Why the rules work: eight mechanisms of the generator, novel-case derivation, mechanism-indexed diagnosis. |
| [`retake-protocol.md`](references/retake-protocol.md) | The iteration economy: take triage, the one-variable rule, attempt budgets, cost awareness, the shot log. |
| [`sequence-project-state.md`](references/sequence-project-state.md) | Stateful project model, canon reconciliation, visual state fields, and Project State Capsule. |
| [`continuation-handoff.md`](references/continuation-handoff.md) | Accepted-source continuation gate, observed state capture, continuation types, and beat exclusions. |
| [`prompt-compiler.md`](references/prompt-compiler.md) | Compiles project state and current clip contract into one natural-language prompt. |
| [`reference-transfer-contract.md`](references/reference-transfer-contract.md) | Exact tag preservation, reference role separation, and transfer/ignore clauses. |
| [`surface-prompt-profiles.md`](references/surface-prompt-profiles.md) | Surface-specific duration, prompt budget, reference role, timeline, edit, extension, and audio constraints. |
| [`event-density.md`](references/event-density.md) | Clip-scope firewall for completed, current, reserved, and do-not-show-yet beats. |
| [`continuity-qc.md`](references/continuity-qc.md) | Boundary checks for immutable and transient continuity across accepted clips. |
| [`failure-atlas.md`](references/failure-atlas.md) | Sequence and continuation failure diagnoses with one primary repair variable. |
| [`sequence-worked-trace.md`](references/sequence-worked-trace.md) | One project walked end to end: plan, deviation, reconciliation, chain cap, re-anchor, and session resume - the prose half of the machine fixtures. |
| [`dense-storyboard-mode.md`](references/dense-storyboard-mode.md) | Dense multishot, phased single-take, and 2D storyboard contracts. |
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
| [`multilingual-native-review.md`](references/multilingual-native-review.md) | Independent human-review rubric and evidence contract for three zh-CN, ja-JP, and ko-KR fixture prompts; it is not authorship proof. |
| [`multilingual-native-review-evidence.json`](evals/multilingual-native-review-evidence.json) | CI-validated review-record structure; the shipped empty list means no language-quality review has been submitted. |
| [`interview-starters.md`](references/interview-starters.md) | Localized blank-slate starting-point menus and invites for the director interview in English, 中文, 日本語, 한국어, Spanish, and Russian. |
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
| [`vocab/en.md`](references/vocab/en.md) | English precision vocabulary, slop traps, and filter-trip repairs. |
| [`vocab/zh.md`](references/vocab/zh.md) | Chinese cinematic vocabulary for compact prompts. |
| [`vocab/ja.md`](references/vocab/ja.md) | Japanese cinematic vocabulary for compact prompts. |
| [`vocab/ko.md`](references/vocab/ko.md) | Korean cinematic vocabulary for compact prompts. |
| [`vocab/es.md`](references/vocab/es.md) | Spanish cinematic vocabulary for compact prompts. |
| [`vocab/ru.md`](references/vocab/ru.md) | Russian cinematic vocabulary for compact prompts. |

## Install

Client support for Agent Skills is still tool-specific. Codex documents a skill as a directory with a required `SKILL.md`, optional `scripts/`, `references/`, `assets/`, and optional `agents/` metadata.

Codex scans `.agents/skills` locations from the working directory upward, plus user/admin/system skill locations. A repository root with `SKILL.md` is shaped like a skill folder, but it still needs to be installed/copied under a scanned skills directory or distributed as a plugin for automatic discovery.

### Step 1 — get the files

Every install path below runs from inside a local copy of this repository, so start here:

```bash
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
```

Without `git` installed, use the green **Code → Download ZIP** button on the repository page, unzip it, and change into the unzipped folder instead. Nothing else on this page works until one of those two has happened.

### Step 2 — install it into your client

The installer is not Codex-only. It copies the skill into any client that reads a skills directory — point `--dest` at the directory yours scans:

```bash
# Codex (default: $CODEX_HOME/skills, else ~/.codex/skills)
python scripts/install_codex_skill.py

# Claude Code — personal install, available in every project
python scripts/install_codex_skill.py --dest ~/.claude/skills

# Any client — install into another project, run from that project
python /path/to/seedance-2.0/scripts/install_codex_skill.py --dest .claude/skills
```

The command stages and validates the repository before promoting it to
`<dest>/seedance-20`, then prints where it landed. Concurrent installers
sharing that destination are serialized. Add `--force` only to replace a
complete existing install. Automatic retry is limited to states for which every
authority record required by the phase reached is present, has flushed file
contents and, on POSIX, a flushed containing-directory publication, and still
validates. Each payload file is first written under a transaction-derived
sibling name, bounded by the recorded size, synced, checked against the recorded
digest, atomically published at its final stage pathname, and followed by a
containing-directory sync on POSIX. A crash therefore leaves that final pathname
absent or complete, never truncated. The copy-sibling basename is capped at 34
ASCII bytes, shorter than the provenance marker already created before copying;
on POSIX it shortens further if the stage reports a smaller component limit.
Shortened names retain a transaction-and-path digest, and any namespace
collision makes staging fail closed before payload copying begins. This bound
applies only to copy siblings: the installer still requires the filesystem to
represent its longer stage and authority names, so it makes no end-to-end claim
for unusually small component limits. Recoverable states include an
exact empty stage before provenance publication; after complete provenance
publication, source-identical final payload files plus the one exact transaction-
bound in-progress sibling; an exact torn prefix of the installer's expected
provenance or completion record; and a deletion workspace bound by its external
transaction journal (plus the exact empty terminal workspace left if that
journal was already removed). Malformed, swapped, or otherwise untrusted records
and late or unexpected bytes are preserved for inspection. A truncated file at
an expected final payload pathname and an unbound temp-like file are likewise
never claimed for automatic cleanup.
So are the deliberately fail-closed hard-death windows after a quarantine is
renamed but before its authority marker is published, or after a private
deletion workspace is created but before its external journal is published.
During replacement, the previous copy remains available for rollback until the
validated stage is promoted. Restart your client afterwards so `seedance-20`
appears in its skill list.

On Windows, authority and deletion handles share reads only and remain open
through their consuming action; a pre-existing or newly requested writable or
deletion handle therefore makes the installer fail closed. On POSIX, verified
objects are moved into a journal-bound mode-`0700` workspace before unlink,
which excludes other OS accounts and narrows the deletion namespace. POSIX
`flock` and owner-only directory permissions are not mandatory isolation from a
hostile process running as the same account. Such a process may retain or open
writable descriptors and mutate either the workspace or its containing skills
directory; all of those capabilities are outside the portable guarantee. The
installer preserves mismatches it observes, but makes no stronger exclusion
claim against that same-account adversary.

On POSIX, authority records are flushed before their containing directory, and
transaction namespace renames and removals are followed by directory `fsync`.
Each copied payload file is individually `fsync`ed before its atomic rename, and
that file's containing stage directory is `fsync`ed after the rename. The
transaction does not recursively flush the supplied skills-directory ancestry;
that ancestry is assumed to have the durability expected by the caller.

Only manifest-declared files and their implied directories are created. Source
permissions are not inherited: POSIX stage/live directories are normalized to
`0700` and files to `0600`. Named streams, extended attributes, and resource
forks on the source root, declared files, or implied directories are refused
before transaction authority is published, because the portable install
contract cannot represent them.
Installs skip the quarantined `references/migrated/` history, the image gallery (about 18 MB of PNGs), the test suite, and the network-capable evaluator. The installer replaces the omitted gallery embeds with one repository link, so the installed README does not contain broken local asset targets.

A destination inside this repository is refused rather than attempted because it would mutate the source authority domain while the payload is being authenticated. For a project-local install, run the script from the project you are installing into, by absolute path, as above.

This repository keeps dense facts in references so the active skill stays small.

If your client supports installing a skill directly from a GitHub repository, use this repository URL:

```text
https://github.com/Emily2040/seedance-2.0
```

For manual installation, copy this repository into the skill directory used by your agent client. The directory name should match the root skill name, `seedance-20`. Treat the table below as common local targets to verify in your own client, not a universal support guarantee.

| Platform | Typical install target (verify in your client) |
|---|---|
| Claude Code | `~/.claude/skills/seedance-20/` (personal) or `.claude/skills/seedance-20/` (project) — both via `scripts/install_codex_skill.py --dest` |
| Codex | `.agents/skills/seedance-20/` or `~/.codex/skills/seedance-20/` via `scripts/install_codex_skill.py` |
| Google Antigravity | `.agents/skills/seedance-20/` (workspace) or `~/.gemini/config/skills/seedance-20/` (global across Antigravity products) |
| OpenClaw | workspace `skills/seedance-20/` or `~/.openclaw/skills/seedance-20/` via `openclaw skills install` (ClawHub-compatible; skills already carry `openclaw:` metadata) |
| Hermes Agent | `~/.hermes/skills/seedance-20/` (primary); a project `skills/seedance-20/` directory is discovered only after its parent is added to `skills.external_dirs` in `~/.hermes/config.yaml` |
| Gemini CLI-style workspace | `.gemini/skills/seedance-20/` |
| GitHub Copilot workspace | `.github/skills/seedance-20/` |
| Cursor workspace | `.cursor/skills/seedance-20/` |
| Windsurf workspace | `.windsurf/skills/seedance-20/` |
| Trae (ByteDance) | `.trae/skills/seedance-20/` |
| Qwen Code (Alibaba) | `.qwen/skills/seedance-20/` or `~/.qwen/skills/seedance-20/` |
| OpenCode | `.opencode/skills/seedance-20/` (also reads `.claude/skills/` and `.agents/skills/`) |
| Amp (Sourcegraph) | `.agents/skills/seedance-20/` or `~/.config/agents/skills/seedance-20/` |
| Goose (Block) | `.agents/skills/seedance-20/` (also `.goose/skills/seedance-20/`) |
| Junie (JetBrains) | `.junie/skills/seedance-20/` or `~/.junie/skills/seedance-20/` |

Several of these clients share the `.agents/skills/` convention — Codex, Google Antigravity, OpenCode, Amp, and Goose all read it — so one install under `.agents/skills/seedance-20/` can serve them together, and `.claude/skills/` is read by many as a compatibility path. Install once as the `seedance-20` root skill; its sub-skills and references resolve by relative path.

## Validation

<!-- installed-readme-validation:start -->

The validation toolchain supports **CPython 3.11 through 3.13**. CI exercises
both endpoints on Ubuntu and Windows; intermediate CPython 3.12 releases remain
inside the supported range. Python 3.10 and 3.14 are outside this lock's
supported range.

Run these checks before every release. The offline source-metadata check runs with
`--enforce-freshness` here so an old checked-in registry stamp blocks a release;
per-pull-request validation deliberately omits the flag, because metadata age
depends on the calendar rather than on the change under test.

The checks themselves are offline after their build dependencies are installed.
Two maintainer checks need third-party libraries: `schema_check.py` executes JSON
Schema instances, while `build_masthead_outlines.py --check` reproduces the
outlined masthead type. Install both hash-pinned toolchains first — the masthead
installer rebuilds a dedicated checkout-specific temp venv, resolves the lock
from the checkout, and creates it with `--without-pip`. Before that new venv's
launcher can bootstrap pip or install anything, the parent publishes and re-reads
an external initialized trust record for the runner and config. Only that
verified path may run bundled `ensurepip` and force-reinstall the locked wheels.
The installer retains the exact selected wheel bytes, validates pip's
install-report hashes against the lock, and seals
every installed distribution file from `RECORD`. Each installed import payload
must also match the retained locked wheel byte-for-byte. Verification and
rendering then require an external, checkout-keyed trust record that binds the
venv runner, `pyvenv.cfg`, builder script, lock, and sealed marker; the runner
must independently match the current Python installation's stdlib venv launcher.
They run in a fresh `python -I -S -B` child that exposes the sealed site-packages
only after startup, so `PYTHONPATH`, `sitecustomize`, `.pth` processing, a forged
venv runner, a parent preload, or a same-version replacement cannot skip hash
verification or shape the output:

`schema_check.py` proves structure and record-local constraints; it does not and
cannot prove graph-wide lineage. `project_state_check.py` and
`continuity_chain_check.py` are mandatory alongside it for duplicate IDs,
parent existence and order, cycles, executable parent-state continuity, and
binding every post-review clip status to its current take history and sibling
take-review record. Both semantic validators share the same bounded review
index; authority candidates must be stable regular non-link files no larger
than 1 MiB, their captured bytes are capped at 16 MiB per directory, and neither
validator accepts a project-state document as its own review.
Passing the schema alone is never a valid release or handoff gate.

`source_registry_check.py` parses the explicit `last_verified` field, rejects
missing, malformed, duplicate, or future stamps, and compares the checked-in
metadata dates of freshness-critical references. It does not fetch URLs and it
does not prove that any upstream claim is still true. A human or separately
authorized live-verification process must re-read the cited sources and update
the claims before changing a stamp.

```bash
python -m pip install --require-hashes --requirement requirements-validation.lock
python -I -S -B scripts/build_masthead_outlines.py --install-build-deps
```

```bash
python -I -S -B scripts/build_masthead_outlines.py --check
python scripts/validate_repo.py --release
```

`validate_repo.py` resolves the repository from its own file location and does
not call Git, so this release path also works from a Download ZIP extraction,
from a nested caller directory, and from a path containing spaces. The separate
masthead-outline check preserves its sealed build-environment trust boundary;
the runner covers the remaining canonical validators, tests, and an in-memory
source compilation that writes no bytecode.

### Git checkout-only hygiene

After the archive-safe checks, a maintainer working in a Git checkout should
also run:

```bash
git diff --check
```

This whitespace check requires Git metadata. Do not run it in a Download ZIP
extraction.

`prompt_architecture_stress.py` is a deterministic failure gate, not a creativity
or originality judge. In strict mode, every applicable dimension on every
`skill_formula` case must score at least 3, the arm average must remain at least
3.5, and materially different briefs may not reuse duplicate or near-duplicate
prompts. Its mechanical checks cover shooting-brief structure, brief-specific
traceability beyond generic production words, explicit camera/light/sound/action
contradictions, and repetition or padding patterns. Comparative creative quality
still requires blinded model evaluation and native-language human review.

The CI workflow runs the same archive-safe runner on push and pull request, with
the one deliberate difference noted above: it omits `--enforce-freshness`.
Checkout-only whitespace hygiene remains a separate CI step. These checks are
deterministic and offline — they prove the package is well-formed.

The multilingual fixture check proves byte-exact reference-token preservation,
canonical common-brief and candidate bindings, non-derived complete review-input
pins, literal identical-string overlap across locale realizations, and the exact
path, bytes, and digest of the canonical limitation disclaimer. It also runs a
best-effort English known-phrase lint across declared public text surfaces. That
lint is defense in depth, not proof that arbitrary prose or every supported
language contains no semantic overclaim. Translated or paraphrased template
detection, semantic differentiation, and reviewer-reasoning adequacy remain
independent human-review questions under
[`multilingual-native-review.md`](references/multilingual-native-review.md).

### Checked-in source metadata age

Whether `references/source-registry.md` is stale depends on today's date, not on
the change being tested, so it is not asked per pull request — that would fail
unrelated work on a calendar boundary. It is asked in two places instead:

| Where | Behaviour |
|---|---|
| Release checklist above | `--enforce-freshness` blocks a release when the checked-in registry stamp is older than 30 days |
| `source-freshness-review.yml` | Runs Mondays 09:00 UTC on the default branch and reports metadata age as clean, drifting (past 14 days), or stale (past 30) |

Drift and staleness are tracked in a single automatically maintained issue. It
opens when the registry first drifts, is refreshed in place each week rather
than re-notifying, and closes itself once the registry is back inside the
window.

The scheduled job never edits the registry. Re-stamping `last_verified` without
actually re-reading the upstream sources would record a verification that never
happened, so refreshing it is deliberately a human step. A clean metadata-age
result means only that the recorded review date is recent enough; it is not a
live source or claim verification.

To prove the package is also *good*, run the model-in-the-loop harness. Its
discovery phase sees the root router and a safe catalog, not the expected route
labels; the responder receives only the sources it selected, and the judge then
scores the answer against [`eval-rubric.md`](references/eval-rubric.md):

```bash
export ANTHROPIC_API_KEY=...
python scripts/eval_run.py --ledger evals/eval-run-ledger.md --stamp 2026-06-28

# The harness defaults to the current documented MiniMax-M3. The endpoint also
# accepts the documented MiniMax-M2.7, M2.5, M2.1, M2 and highspeed variants.
export MINIMAX_API_KEY=...
python scripts/eval_run.py --provider minimax --region global_en \
  --ledger evals/eval-run-ledger.md --stamp 2026-06-28
python scripts/eval_run.py --provider minimax --region cn_zh --model MiniMax-M2.7 \
  --ledger evals/eval-run-ledger.md --stamp 2026-06-28
```

The harness uses `Authorization: Bearer <API_KEY>` as documented by both the
[global](https://platform.minimax.io/docs/api-reference/text-chat-anthropic) and
[CN](https://platform.minimaxi.com/docs/api-reference/text-chat-anthropic)
Anthropic-compatible Messages endpoints. Those provider contracts were checked
directly on 2026-08-01: both list the same eight supported models and the common
successful-response fields (`id`, `type`, `role`, `model`, `content`,
`stop_reason`, and `usage`), without requiring either `base_resp` or
`stop_sequence`. Anthropic's own response contract is validated separately,
including its required `stop_sequence` field.

Successful bodies are validated fail-closed: documented optional usage,
citation, thinking, and tool-call structures are type-checked with unknown
fields rejected, while optional MiniMax legacy `base_resp`/`stop_sequence`
fields cannot contradict an otherwise successful response. M2.x thinking
blocks are accepted only in their documented shape; unrequested tool calls and
Anthropic/M3 thinking are rejected as non-final evidence. Transport errors name
the failed open, context-entry, or read phase and redact API keys before console
or ledger output. Generated ledger commands are emitted separately for POSIX
shells and PowerShell, and are omitted when metadata is not safe to round-trip.

Before either offline or live evaluation starts, the harness resolves every eval
input through [`evals/source-manifest.json`](evals/source-manifest.json), rejects
unclassified files, symlinks/reparse aliases, hard-link aliases, and digest
drift, then freezes the verified UTF-8 bytes for the whole run. The root router,
rubric, eval suite, fixture data, evaluator harness, planner catalog, responder
context, judge, and ledger therefore share one immutable source view. State
fixtures are strict JSON objects under `evals/fixtures/`; models receive the data
but never the fixture path. The judge receives the rubric, case prompt, expected
output, checks, and candidate response, but never expected route labels or
selected source paths. The harness also compiles the frozen evaluator source and
requires it to equal the module code object Python actually executed, with the
same physical `scripts/eval_run.py` path. Every recheck derives path, role, and
digest metadata again from the frozen manifest so a constructed snapshot cannot
reclassify responder files as evaluator-only inputs. A post-run check plus checks
immediately before and after the atomic ledger replace refuse release evidence
if any input changed after the snapshot; a failed post-replace check restores the
prior ledger. For a newly created destination, it invalidates only the retained
published inode to zero length through its open descriptor; a concurrent
namespace substitute is preserved untouched. That first publication is also
source-descriptor-bound: Linux links an unnamed `O_TMPFILE`, while Windows
renames the retained file handle to a target derived from the retained directory
handle. Neither platform re-resolves a mutable staging pathname. Existing ledger permission modes
are bound before the copy and preserved on both replacement and rollback; a new
POSIX ledger remains owner-only, while the Windows read-only attribute is retained
without modifying linked inputs. Bootstrap failure ledgers also
refuse direct, hard-link, symlink, or source-boundary aliases of repository
inputs before writing.

Blind discovery is scored, not merely recorded: after the planner returns, its
selected skill paths must exactly match the hidden
`skills_expected_to_activate` oracle. Missing, wrong, extra, duplicate, unknown,
or non-responder selections fail before response generation. Generated ledger
rows bind every selected responder path to its frozen SHA-256 digest; fabricated,
non-canonical, missing, or mismatched provenance cannot produce a release pass.
The ledger also records one canonical SHA-256 over the complete frozen
path/role/hash map, including `SKILL.md`, fixtures, evaluator files, and the
source manifest itself, plus per-role file counts. Release assessment accepts
that provenance only from the verified `FrozenRepository`; caller-supplied
digest maps cannot stand in for the evaluated checkout.
The canonical eval-suite and rubric digests are pinned so a structurally valid
but semantically gutted replacement also fails closed.

Every declared case oracle reaches the judge through a stable opaque criterion
ID. Assertions, required output sections, forbidden behaviors, `expected_output`,
`failure_mode`, `expected_state_delta`, and `expected_prompt_architecture` are
scored as exact judge-only criteria; `expected_sequence_relation` is bound into
the routing dimension. These oracle values remain hidden from discovery and
response generation, so binding them does not undo the blind-selection boundary.

Result rows have an explicit evidence status. `scored` means the judge returned
a complete, strictly typed verdict with every criterion and dimension ID exactly
once; only these rows enter quality floors and averages. A judge transport error,
timeout, empty body, oversized body, malformed JSON, or incomplete/invalid
verdict becomes `harness_error` with no numeric score or pass value. The harness
continues the remaining selected cases, writes a fresh auditable ledger, excludes
the error row from quality arithmetic, marks release evidence `NOT ELIGIBLE`, and
exits 1. It never represents missing judge evidence as a poor-output score of 0.

Case-contract or response-envelope failures are different: they are known before
the first provider call, so the whole live run aborts with exit 2. If `--ledger`
was requested, the stale artifact is atomically replaced by a bootstrap
`harness_error` ledger. Post-run snapshot drift likewise makes every recorded row
a non-scored harness error and exits 2.

This is the model-response quality gate, not a shape gate or a language/rendering
certification, so it lives outside offline CI; the latest run evidence is
recorded in [`evals/eval-run-ledger.md`](evals/eval-run-ledger.md).
Language-quality review uses the independent evidence protocol in
[`multilingual-native-review.md`](references/multilingual-native-review.md). CI
validates recorded bindings and scoring, while the truth and adequacy of
reviewer reasoning remain manual judgments.

<!-- installed-readme-validation:end -->

## Design Standard

The front page follows an editorial design system rather than default AI styling: warm ink and paper themes, a serif display face paired with monospace specification labels, a single amber accent, and hairline rules — no gradients, no glow. Camera motifs are deliberately retired: no viewfinder marks, timecode, record dots, or aspect badges. They depict the tool rather than the work, and they are the visual cliché of every AI-video product.

The masthead is generated from one geometry by [`scripts/build_hero.py`](scripts/build_hero.py), so its dark and light variants cannot drift apart; the isolated `python -I -S -B scripts/build_hero.py --check` command proves the committed SVGs still match the generator, and it runs in CI.

The outlined display type has a separate, build-only toolchain. Before changing
the wordmark or tagline geometry, run `python -I -S -B scripts/build_masthead_outlines.py`
and then `python -I -S -B scripts/build_hero.py`. A writing run first recreates a
dedicated, marker-protected venv outside the checkout. The clear target is rejected when it
is inside the repository, trust directory, Python installation, or a non-temp
home subtree; equals a protected root; or would contain the repository, home
directory, Python prefix, system temp root, or external trust directory. A
dedicated descendant of the system temp directory remains allowed. The installer
then uses pip's `--force-reinstall --require-hashes` against the resolved lock.
The selected wheel artifacts are retained in the build venv; their hashes, pip's install
report, and the sha256 of every locked-distribution file are sealed together,
and the installed import bytes are compared directly with those retained wheel
archives. The venv is created with `--without-pip`, so creation never starts its
runner. The parent then stores and re-verifies a separate trust record outside
the venv that binds the runner, config, trusted base Python, current builder
script, lock, and initialized marker; the runner bytes must match the trusted
stdlib venv launcher. Only then can the verified runner bootstrap bundled pip and
perform the hash-locked installation. After sealing, the parent promotes that
record only if those inputs are unchanged and binds the sealed marker too. A
no-site `python -I -S -B` child verifies the package seal before adding the dedicated
site-packages path or importing FontTools and uharfbuzz.
Inherited loader, Python, pip, and virtualenv hooks are removed from child
environments. The generator records the exact lock digest plus the FontTools,
uharfbuzz, and HarfBuzz versions in
`assets/masthead-outlines.json`. The current lock pins `uharfbuzz==0.55.0`, the
latest stable release shown by [official PyPI metadata](https://pypi.org/project/uharfbuzz/0.55.0/)
when the lock was reviewed on 2026-08-02; the newer 0.56 line was prerelease-only.
Its six hashes are the published CPython abi3 wheels for Windows x86-64, Linux
glibc/musl on x86-64 and ARM64, and macOS universal2. Before either SVG is
written, `build_hero.py` independently requires the exact lock path, lock-byte
digest, install policy, and builder-version map recorded in the outline asset,
then renders both themes in memory so a second-theme failure cannot leave a
half-updated pair.
To prepare a later read-only check without regenerating, run
`python -I -S -B scripts/build_masthead_outlines.py --install-build-deps` once and then
use `python -I -S -B scripts/build_masthead_outlines.py --check` offline. Both commands
resolve the same checkout-specific temp venv by default; CI passes an explicit
run-attempt-specific `--build-env` under `/tmp`, because the hosted Linux
`$RUNNER_TEMP` is below `$HOME` and the clear guard deliberately rejects home
descendants. The wheelhouse remains under `$RUNNER_TEMP`; it is read, not cleared.
A changed distribution file, retained wheel, install report, lock, runner, venv
config, builder script, marker, startup hook, external trust record, or structured
child result makes the offline check fail closed and requires a fresh install.

The masthead and the hand-built operating diagram (`assets/hero-dark.svg`, `assets/hero-light.svg`, `assets/skill-map.svg`) are served through a `prefers-color-scheme` picture element; generated bitmap art lives only in the curated visual gallery, including the text-rich infographics.

The README must stay readable in GitHub mobile, dark mode, and narrow widths. SVG assets must include `<title>` and `<desc>` elements, use internal CSS only, and avoid external fonts, scripts, or resources. Tokens and rules live in [`references/frontend-design-system.md`](references/frontend-design-system.md) and [`docs/frontend-redesign.md`](docs/frontend-redesign.md).

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md). Current release: **v6.7.0**.

## License

MIT © 2026 Iamemily2050 (@iamemily2050)
