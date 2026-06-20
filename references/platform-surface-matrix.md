# Platform Surface Matrix

last_verified: 2026-06-20

Seedance 2.0 capability claims must separate the model from the product surface. A feature can be true for the model while still being gated, unavailable, renamed, priced differently, or policy-limited on a specific surface.

Access note (2026-06-13): the overseas Seedance 2.0 API is contested following a copyright-driven suspension — see `api-status.md`. Verify live access on any third-party surface before relying on it, and add no surface here without independently confirming it hosts Seedance 2.0.

| Surface | Evidence type | Typical use | Current guidance |
|---|---|---|---|
| ByteDance Seed official model page | official | Broad capability framing | Use for high-level model positioning only. It confirms multimodal audio-video generation, references, performance, lighting, shadow, and camera control. |
| ByteDance official launch post | official | Capability details and known limits | Use for the strongest public claims about input modalities, reference counts, video extension/editing, dual-channel audio, and remaining weaknesses. |
| Volcengine Ark / ModelArk docs | official platform docs | API task flow and model surface | Recheck before giving endpoints, regions, quotas, pricing, or file limits. As of 2026-06-20, Volcengine exposes Seedance 2.0 Mini as `doubao-seedance-2-0-mini-260615`, but official docs say it is trial-gated until June 22. |
| Volcengine video-generation tutorial | official platform docs | Async task lifecycle, first/last-frame roles, return-last-frame, web-search tools, and reference-file combinations | Current May 29 signal for Volcengine fields. Use for Volcengine only; recheck exact schema, entitlement, pricing, and face-reference behavior before implementation. |
| Volcengine developer-community article | official ecosystem/news article | API availability, safety, and adoption context | Useful for noting API-service rollout, portrait/copyright standards, face verification, virtual portraits, and BytePlus overseas service. Do not treat it as an API schema, pricing table, or account entitlement guarantee. |
| BytePlus ModelArk docs | official platform docs | International API and docs surface | Recheck before production guidance. BytePlus exposes Seedance 2.0 Mini as `dreamina-seedance-2-0-mini-260615` and a `dreamina-seedance-2.0-mini` pricing row, but cite only visible or independently verified claims. |
| Runway Seedance 2 | official third-party surface | API/web generation with Seedance 2 model access | Runway documents `seedance2`, 5-15s duration, image/video/audio references, upload URIs, audio-combination rules, and plan/region caveats. Treat as Runway surface behavior, not Volcengine or BytePlus behavior. |
| Runway MCP | official agent connector surface | Agent-accessible image/video generation | Useful for agent workflow planning. It does not prove ByteDance API access or alter Seedance model limits. |
| fal | official third-party surface | API generation through fal's Seedance 2.0 endpoints | Verified 2026-06-09: fal documents text-to-video, image-to-video (start image plus optional end image), and reference-to-video, each with a /fast tier, 4-15s or auto duration, six aspect ratios plus auto, and per-second pricing. fal's prose guide says 480p/720p while model and pricing pages list 1080p - verify resolution per endpoint at call time. No extend endpoint on this surface. Treat as fal surface behavior, not Volcengine or BytePlus behavior. |
| Atlas Cloud | third-party aggregator surface | Hosted Seedance 2.0 via an async video-generation API | Verified 2026-06-13: Atlas Cloud hosts live Seedance 2.0 (text-to-video, image-to-video, reference-to-video, plus fast variants). Its OpenAI-compatible endpoint covers LLM/chat only; **Seedance video generation uses Atlas Cloud's own async API** - `POST /api/v1/model/generateVideo` with a model id such as `bytedance/seedance-2.0/text-to-video`, returning a prediction id polled at `/api/v1/model/prediction/{id}` - not the OpenAI SDK shape. One of several aggregators reselling Seedance access; treat endpoints, pricing, model IDs, quotas, and guardrails as aggregator-specific, recheck before use, and never present them as official ByteDance behavior. The repo endorses no reseller; listed for completeness. |
| Replicate | third-party model-host surface | Hosted Seedance 2.0 under the official `bytedance` namespace | Verified 2026-06-13: Replicate lists `bytedance/seedance-2.0` (text-to-video, image-to-video, multimodal reference inputs `[Image1]/[Video1]/[Audio1]`, native audio) behind its standard async prediction API; check the model page for supported resolutions rather than assuming model-level maximums. A reputable, widely-used model host — but still surface-specific: recheck pricing, limits, and live access (see the overseas-API status note in `api-status.md`), and never present its behavior as official ByteDance behavior. The repo endorses no host; listed for completeness. |
| WaveSpeedAI / Higgsfield / Pollo | third-party host surfaces | Additional verified Seedance 2.0 hosts | Verified 2026-06-14 (provider-own pages): WaveSpeedAI (async job API, t2v/i2v + fast/turbo/"spicy" variants, 480p/720p/1080p tiers), Higgsfield (creator UI, multimodal inputs; no clearly documented public API found), Pollo (web model page + unified job API). Same rules as every host: async submit/poll for video, recheck live, aggregator/host-specific not official. The repo endorses none. |
| EvoLink / OpenRouter / Kie.ai / PiAPI / LaoZhang | third-party provider/router surfaces | Additional Seedance 2.0 API access routes | Verified 2026-06-20 from provider-owned pages or docs: EvoLink documents `/v1/videos/generations` plus `/v1/tasks/{task_id}`; OpenRouter lists `bytedance/seedance-2.0`; PiAPI documents a generic task API with Seedance task types; LaoZhang documents a `/seedance/api/v3` base path; Kie.ai publishes Seedance 2.0 API access. Treat model IDs, auth, base URL, polling, pricing, face/reference support, output URLs, and content policy as provider-specific. The repo endorses no reseller. |
| Runware / ModelsLab / AI/ML API / MuAPI / SeeGen / Segmind | third-party provider/router surfaces | Additional Seedance 2.0 or Seedance 2 Fast model-host routes | Verified 2026-06-20 from provider-owned pages or docs. These pages list Seedance 2.0, Seedance 2.0 Fast, or related ByteDance video routes, but their fields and model names differ. Use them as candidates for provider-specific integration only after live docs and account access are checked. The repo endorses no reseller. |
| Dreamina / Jimeng web UI | official product surface | Creator workflow | Behavior may differ from API. Do not generalize web UI limits, credits, face checks, or upload rules to every surface. |
| Dreamina Seedance 2.0 Mini | official product surface | Lower-cost/faster Dreamina web generation lane | Use as Dreamina web-surface evidence only. Do not infer API fields, model IDs, pricing, or 1080p support from marketing copy without checking Volcengine/BytePlus docs or console. |
| ComfyUI partner node docs | partner workflow docs | T2V, R2V, FLF2V workflows | Useful for workflow vocabulary and surface caveats. Label as ComfyUI-specific rather than universal Seedance behavior. |
| Third-party wrappers | community/commercial wrapper | Access abstraction | Useful for field patterns and integration ideas only. Do not present wrapper model names, prices, or guardrail behavior as official. |
| Community prompt corpora | field-observed | Prompt pattern mining | Mine structures, timing syntax, vocab, and failure modes. Do not copy unsafe, IP-sensitive, or real-person examples directly. |
| Agent Skills docs | agent packaging docs | Repository layout and install language | Use for skill structure and progressive-disclosure guidance. Do not treat repository install paths as universal client guarantees. |

## API Shape Rule

Verified 2026-06-20 across every developer surface checked here (fal, Replicate, Volcengine Ark, BytePlus ModelArk, Atlas Cloud, Runway, WaveSpeed, Pollo, EvoLink, OpenRouter, Kie.ai, PiAPI, LaoZhang, Runware, ModelsLab, AI/ML API, MuAPI, SeeGen, Segmind): Seedance 2.0 **video generation is always an async job** - submit a task, get an id, poll until ready, fetch the URL. Some routers wrap the job in a unified or OpenAI-compatible surface, but the video generation itself still uses provider-specific async semantics. Never hand a user an LLM/chat request shape for Seedance video.

## China-Facing Search Note

Searches in Chinese on 2026-06-20 found official China-facing surfaces already represented here: ByteDance Seed, Volcengine Ark, BytePlus ModelArk, Doubao, Jimeng/Jianying, and CapCut/Jianying. RunningHub-style hosted ComfyUI workflows and Chinese business-partner news can be useful context, but they are not self-serve API surfaces unless a provider-owned API page exposes endpoints, model IDs, pricing, account access, and policy terms.

## Surface-Specific Claims

When answering a question about production use, include:

- surface name,
- verification date,
- model or workflow name if known,
- whether the claim is official, partner, wrapper, or field-observed,
- what must be rechecked before use.

## Real-Person Rule

Real-person images, portraits, and voices are authorization-sensitive. Some surfaces may provide identity verification flows, and others may reject or restrict real-person references. Do not infer consent from an uploaded asset.

## V2V, R2V, and FLF2V Boundary

Official ByteDance material supports multimodal references, I2V/R2V examples, editing, and extension. Volcengine now documents first-frame and last-frame roles on its video-generation surface. Keep `FLF2V` as a label caveat because workflow names differ by product surface, but do not say first/last-frame itself is partner-only.
