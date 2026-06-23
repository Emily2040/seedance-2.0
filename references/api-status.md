# Seedance 2.0 API and Platform Status

last_verified: 2026-06-20
confidence: public-source snapshot as of the verification date; per-section dates apply where noted (Seedance 2.0 Mini, additional provider/router, and China-facing search recorded 2026-06-20, platform safeguards and resolution recorded 2026-06-14, overseas-API status and Replicate recorded 2026-06-13, fal section re-verified 2026-06-11, earlier surface sections verified 2026-05-30); not a guarantee of access, pricing, model IDs, upload limits, authorization behavior, or regional availability on every surface

## Confirmed From Public Sources

- ByteDance's official Seedance 2.0 page describes a unified multimodal audio-video architecture that supports text, image, audio, and video inputs.
- ByteDance's launch post says Seedance 2.0 can use up to 9 images, 3 video clips, 3 audio clips, plus natural-language instructions.
- Official material says references can guide visual composition, camera language, motion rhythm, visual effects, and sound characteristics.
- Official material describes video extension and editing as supported creative workflows.
- Official material describes 15-second multi-shot audio-video output and dual-channel audio.
- The arXiv model card is useful for model-family context, including 4-15 second audio-video generation, native 480p/720p framing in the paper, and a Fast variant.
- Volcengine/Ark docs publish Seedance 2.0 tutorial and video-generation API navigation, including create/query/list/cancel-delete task flows, but exact schemas, prices, model IDs, regions, and limits must be rechecked live.
- Volcengine's model-list page was observed updated on 2026-05-29.
- Volcengine's Seedance 2.0 tutorial now lists the Mini trial notice and `doubao-seedance-2-0-mini-260615` alongside the earlier `doubao-seedance-2-0-260128` and `doubao-seedance-2-0-fast-260128` model IDs.
- Volcengine's general video-generation tutorial was observed updated on 2026-05-29 and is the current first-party place to recheck task lifecycle, first/last-frame roles, return-last-frame, web-search tools, and file/reference combinations.
- Volcengine's prompt guide was observed updated on 2026-05-15 and reinforces multimodal reference prompting.
- Volcengine's pricing page was observed updated on 2026-05-28. Quote Volcengine prices only with surface, date, currency, model/resolution/duration context, and a recheck warning. Keep the stronger no-quote caveat for JavaScript-rendered BytePlus pages that are not live-verified.
- A Volcengine developer-community article says Seedance 2.0 API service is online and mentions portrait/copyright safety standards, face verification, portrait authorization, virtual portrait assets, and BytePlus overseas API service. Treat this as official ecosystem/news evidence, not the API contract.
- Public BytePlus pages may be JavaScript-rendered in static fetches. Do not quote Seedance 2.0 BytePlus pricing or model IDs from such pages without live official verification.
- Runway's official Seedance 2 guide and stable Models, API Changelog, Inputs, and help pages list Seedance 2.0/Seedance 2.0 Fast on the Runway surface. The Seedance-specific guide documents `seedance2` examples and reference-field caveats; if a raw HTTP checker reports 404, verify through the browser/indexed doc before dropping the source.
- BytePlus ModelArk docs now list Dreamina Seedance 2.0 Mini, `dreamina-seedance-2-0-mini-260615`, and pricing rows for `dreamina-seedance-2.0-mini`. Treat the hyphenated ID and dotted pricing label as surface-specific BytePlus names, not canonical names for every provider.
- Additional provider/router pages visible on 2026-06-20 include EvoLink, OpenRouter, Kie.ai, PiAPI, LaoZhang, Runware, ModelsLab, AI/ML API, MuAPI, SeeGen, and Segmind. Treat them as surface-specific access routes, not official ByteDance/Volcengine/BytePlus contracts.
- China-facing searches on 2026-06-20 confirm the strongest sources remain official ByteDance Seed, Volcengine Ark, BytePlus ModelArk, Doubao, Jimeng/Jianying, and CapCut/Jianying surfaces. Chinese-language workflow posts, business-partner news, or hosted ComfyUI workflows are not public API providers unless they publish provider-owned API docs.
- Partner workflow docs such as ComfyUI expose T2V, R2V, and FLF2V workflow vocabulary, but those docs are surface-specific.
- Recent AV-generation benchmark papers, including AVBench and VABench, are useful for eval vocabulary around audio-video consistency, but they are not Seedance platform-access sources.

## Overseas API Status — Copyright Suspension *(recorded 2026-06-13)*

Authoritative reporting (Variety and CNBC, Feb–Mar 2026) documents that after Seedance 2.0's China launch on 2026-02-12, Disney, Warner Bros., Paramount, Netflix, and the Motion Picture Association sent ByteDance cease-and-desist letters over alleged IP infringement, and ByteDance **suspended the planned overseas API rollout (~2026-03-15)** pending resolution and added safeguards. What this means for guidance:

- Treat overseas/global Seedance 2.0 API access as **contested and volatile**, not guaranteed-available. Verify live access, region, and rights posture before relying on any surface.
- Third-party surfaces (fal, Atlas Cloud, Replicate, EvoLink, OpenRouter, Kie.ai, PiAPI, LaoZhang, Runware, ModelsLab, AI/ML API, MuAPI, SeeGen, Segmind, and others) have shown live Seedance 2.0 endpoints at various dates; that does not establish stable official global availability - access has shifted and may shift again. Recheck immediately before production.
- The dispute makes the repo's standing rule operational, not hypothetical: never reproduce protected characters, scenes, or real-person likenesses — that exact behavior triggered the suspension.

## Platform Safeguards — Now Live *(recorded 2026-06-14)*

Authoritative reporting (SCMP, CNBC, The Next Web, Feb–Apr 2026) documents safeguards ByteDance added to Seedance 2.0 in response to the dispute. These are no longer hypothetical — treat them as current platform behavior on official surfaces, and design prompts to work *with* them:

- **Real-face input blocking:** generation from images or videos containing real human faces is restricted (anti-deepfake). Do not assume a real-person reference will be accepted; route likeness work through `[skill:seedance-copyright]`.
- **Copyrighted-character blocking:** generation of recognizable protected characters (e.g. Shrek, SpongeBob, Darth Vader) is blocked. This is enforcement, not just policy — `[skill:seedance-filter]`'s original-character rewrites are the working path.
- **Visible watermark + C2PA Content Credentials** on output, and **invisible watermarking** with proactive IP monitoring (ByteDance states it can identify and act on model output even after it is shared or altered).

Implication for the skill: false-positive repair and IP-safe rewriting are not optional polish — they are how a prompt clears live guardrails. Surface-specific behavior still varies; verify on the active surface.

## Resolution — Model vs Surface *(recorded 2026-06-14)*

Primary sources (the arXiv model card and the ByteDance Seed page) state Seedance 2.0's **native output resolution is 480p/720p**. Higher resolutions are **surface-specific, not a model-native guarantee**, and even a single surface's docs can disagree: Volcengine/Ark (Pro), BytePlus, Atlas Cloud, Runway, and WaveSpeed expose **1080p**; fal's prose guide says 480p/720p while its model and pricing pages list 1080p (see the fal section below). Treat 480p/720p as the baseline capability and any 1080p/“2K” claim as a per-surface feature to verify per endpoint at call time — never as a universal model spec.

## fal — Authorized Provider, Global *(added 2026-06-10; fields, resolution, and pricing re-verified 2026-06-11)*

**Endpoints:** `text-to-video`, `image-to-video` (start image + optional `end_image_url` for A→B), `reference-to-video` — each with a `/fast` tier.
**Duration:** 4–15s or `auto` (model sizes to prompt complexity; multi-shot → longer). **Aspect:** 21:9 / 16:9 / 4:3 / 1:1 / 3:4 / 9:16 / auto.
**Params (t2v):** `prompt`, `resolution`, `duration`, `aspect_ratio`, `generate_audio` (default on; **audio included at no extra generation cost**), `seed` (**reproducibility aid, not a hard lock** — output may vary even with the same seed).
**Params (i2v):** the t2v fields plus `image_url` (start frame) and optional `end_image_url` (A→B). Do not send image fields to the t2v endpoint.
**Params (r2v):** reference assets go in array fields `image_urls`, `video_urls`, `audio_urls` (verified 2026-06-11) — do not reuse the i2v `image_url`/`end_image_url` fields for references; recheck the live schema before implementation.
**References (r2v):** @Image×9, @Video×3, @Audio×3, ≤12 files. Images JPEG/PNG/WebP ≤30 MB; videos 480–720p, combined ≤15s, <50 MB total; audio MP3/WAV ≤15 MB each, combined ≤15s; **audio requires ≥1 image or video.**
**Resolution (verified 2026-06-11):** standard endpoints list 480p/720p/**1080p (~$0.682/s)**; fast endpoints cap at 720p. Prose guides have lagged the schema before — verify per endpoint at call time.
**Pricing (verify live before quoting):** 720p standard ≈$0.30/s · fast ≈$0.24/s · video-reference ×0.6 · 1080p ≈$0.682/s.
**Prompting:** prose direction; `Shot 1:/Shot 2:` labels for multi-shot; r2v docs also accept timestamp pacing phrases as secondary hints. **Fast tier:** official fal docs give fast endpoints the same schema and multi-shot support; field reports still favor the Standard tier for multi-shot, slow motion, and dolly moves — treat that as field guidance, not provider doc.
**No dedicated extend endpoint** — extend is a Dreamina-app feature. To continue a clip on fal, prefer reference-to-video with the previous clip as a video reference (keeps motion and audio context); chaining image-to-video from the previous clip's last frame is the fallback.

## Seedance 2.0 Mini *(recorded 2026-06-20)*

Official Volcengine and BytePlus docs now expose Seedance 2.0 Mini as a lighter Seedance 2.0 series lane. Use the canonical public wording `Seedance 2.0 Mini`, not `Seedance V2 Mini`, unless quoting a user or wrapper label.

- **Volcengine Ark:** visible model ID `doubao-seedance-2-0-mini-260615`. Volcengine's notice says that from June 15 to June 22, 2026, it is available only through the console experience center with concurrency limited to 1, and that API support is expected after June 22 Beijing time. Recheck this after June 22 before giving API instructions.
- **BytePlus ModelArk:** visible model ID `dreamina-seedance-2-0-mini-260615`; BytePlus docs describe the same June 15-June 22, 2026 trial-window limitation through Model Playground. BytePlus pricing pages also show a `dreamina-seedance-2.0-mini` row and state 1080p is not supported for that row. Recheck pricing live before quoting numbers.
- **Dreamina/CapCut web:** official Dreamina page describes Seedance 2.0 Mini as faster/lower-cost and available in Dreamina. Treat its workflow claims as Dreamina web-surface behavior, not an API schema.

Do not confuse Seedance Mini IDs with `doubao-seed-2-0-mini-*`, which belongs to the non-Seedance Seed/Doubao model naming lane.

## Additional Provider/Router Surfaces *(recorded 2026-06-20)*

These are third-party or router surfaces. They are useful for integration planning, but each one can rename modes, alter schemas, hide fields, change pricing, or impose its own moderation and account rules.

- **EvoLink:** public page documents `POST /v1/videos/generations`, polling through `GET /v1/tasks/{task_id}`, Bearer auth, `seedance-2.0-text-to-video`, 4-15s duration, 480p/720p/1080p quality options, and per-second billing.
- **OpenRouter:** model page lists `bytedance/seedance-2.0` as a video model with text-to-video, image-to-video with first/last-frame control, and multimodal reference-to-video. Treat provider routing, token/second accounting, and supported providers as OpenRouter-specific.
- **Kie.ai, PiAPI, and LaoZhang:** public pages or docs list Seedance 2.0 API access, but schemas differ. PiAPI documents a generic task API with `seedance` as the model and `seedance-2-preview` / `seedance-2-fast-preview` task types; LaoZhang documents a `/seedance/api/v3` base path; Kie.ai's public page emphasizes API access and multimodal support. Recheck exact fields before implementation.
- **Runware, ModelsLab, AI/ML API, MuAPI, SeeGen, and Segmind:** provider pages list Seedance 2.0, Seedance 2.0 Fast, or related ByteDance video routes. Treat them as additional provider/router candidates only; do not copy their model IDs, face handling, watermark, rights, or price claims into official examples without live verification.

## China-Facing Provider Search *(recorded 2026-06-20)*

For Chinese-provider questions, start with official or ByteDance-owned surfaces: ByteDance Seed, Volcengine Ark, BytePlus ModelArk, Doubao, Jimeng/Jianying, and CapCut/Jianying. RunningHub-style hosted workflows can be useful workflow evidence, and business-partner reports can show commercial adoption, but neither should be treated as a public API provider unless the provider publishes its own API docs, model IDs, pricing, account access rules, and moderation terms.

## Operational Wording

Use this wording unless newer primary sources say otherwise:

> As of 2026-06-20, public ByteDance sources describe Seedance 2.0 as a unified multimodal audio-video generation model with text, image, audio, and video inputs. Official launch and model-card material says references can include up to 9 images, 3 video clips, and 3 audio clips. Volcengine/Ark, Runway, fal, and additional provider/router pages publish Seedance 2 documentation or access routes, but access, model IDs, pricing, file limits, regional availability, resolution, audio-combination rules, face/reference handling, and portrait authorization remain surface-specific and must be rechecked before production use.

## Model Naming Rule

- Use `Seedance 2.0` for the official video model line.
- Use `Seedance 2.0 Fast` only when the active surface exposes a Fast variant.
- Use `Seedance 2.0 Mini` only when the active surface exposes the Mini lane; treat `Seedance V2 Mini` as shorthand, not canonical naming.
- Use `seedance2` only for Runway's API surface.
- Use provider/router model IDs only on that provider's surface, for example EvoLink's `seedance-2.0-text-to-video`, OpenRouter's `bytedance/seedance-2.0`, PiAPI task types, or Runware's `bytedance:seedance@2.0`.
- Do not call `Seedance 2.0 Pro` the official video-model name without a current source. Treat it as ambiguous wrapper or community wording.
- Do not confuse `Seed2.0 Pro` or Doubao/Seed general model names with Seedance video generation.

See [`model-name-map.md`](model-name-map.md).

## Claim Boundaries

- Say that API availability, pricing, model IDs, upload limits, entitlement rules, rate limits, and regional availability must be checked against current primary sources.
- Avoid claiming that an API is globally available or unavailable unless a current primary source says so.
- Avoid claiming that face or portrait uploads are universally supported or universally blocked unless a current primary source says so.
- Separate model capability from product-surface behavior. Dreamina/Jimeng, Doubao, Volcengine/Ark, BytePlus/ModelArk, ComfyUI, fal, provider/router surfaces, and third-party wrappers can differ.
- Treat third-party wrapper prices and model aliases as wrapper-specific, not official.

## Known Limit Categories

Official/provider material and field observations point to these areas as fragile:

- detail stability,
- hyper-realism,
- dynamic vitality,
- multi-subject consistency,
- text rendering,
- complex editing,
- audio distortion,
- multi-speaker lip-sync,
- product/logo preservation,
- real-person authorization and surface gating.

## Real-Person, Portrait, and Voice Rule

Real-person face, portrait, and voice workflows require authorization, legal/ethical compliance, and platform-specific support. Do not infer permission from an uploaded asset. Do not help imitate a public figure, private person, celebrity, or voice without a clearly authorized workflow that complies with applicable rules and user consent requirements.

## Primary Sources To Recheck

- https://seed.bytedance.com/en/seedance2_0
- https://seed.bytedance.com/en/blog/seedance-2-0-official-launch
- https://replicate.com/bytedance/seedance-2.0
- https://variety.com/2026/film/news/paramount-disney-bytedance-cease-and-desist-seedance-ai-infringement-ip-1236663663/
- https://www.cnbc.com/2026/02/16/bytedance-safeguards-seedance-ai-copyright-disney-mpa-netflix-paramount-sony-universal.html
- https://arxiv.org/abs/2604.14148
- https://www.volcengine.com/docs/82379/1330310?redirect=1&lang=zh
- https://www.volcengine.com/docs/82379/1520757?lang=zh
- https://www.volcengine.com/docs/82379/2291680?lang=zh
- https://www.volcengine.com/docs/82379/2298881?lang=zh
- https://www.volcengine.com/docs/82379/2222480?lang=zh
- https://www.volcengine.com/docs/82379/1544106?lang=zh
- https://developer.volcengine.com/articles/7628567056649125942
- https://docs.byteplus.com/en/docs/ModelArk/2291680
- https://docs.byteplus.com/en/docs/ModelArk/1520757
- https://docs.byteplus.com/en/docs/ModelArk/1544106
- https://docs.byteplus.com/en/docs/ModelArk/1099320
- https://fal.ai/models/bytedance/seedance-2.0/text-to-video
- https://fal.ai/models/bytedance/seedance-2.0/image-to-video
- https://fal.ai/models/bytedance/seedance-2.0/reference-to-video
- https://docs.dev.runwayml.com/guides/seedance/
- https://docs.dev.runwayml.com/assets/inputs/
- https://evolink.ai/seedance-2-0
- https://openrouter.ai/bytedance/seedance-2.0
- https://kie.ai/seedance-2-0
- https://piapi.ai/seedance-2-0
- https://piapi.ai/docs/seedance-api/seedance-2
- https://docs.laozhang.ai/en/api-capabilities/seedance2-video-generation
- https://runware.ai/docs/models
- https://modelslab.com/seedance-2
- https://docs.aimlapi.com/api-references/video-models/bytedance/seedance-2.0
- https://muapi.ai/
- https://seegen.ai/
- https://www.segmind.com/models/seedance-2.0
- https://docs.dev.runwayml.com/guides/models/
- https://docs.dev.runwayml.com/api-details/api_changelog/
- https://help.runwayml.com/hc/en-us/articles/50488490233363-Creating-with-Seedance-2-0
- https://docs.comfy.org/zh/tutorials/partner-nodes/bytedance/seedance-2-0
- https://arxiv.org/abs/2605.24652
- https://openaccess.thecvf.com/content/CVPR2026/papers/Hua_VABench_A_Comprehensive_Benchmark_for_Audio-Video_Generation_CVPR_2026_paper.pdf
