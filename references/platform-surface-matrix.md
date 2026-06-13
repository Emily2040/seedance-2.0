# Platform Surface Matrix

last_verified: 2026-06-13

Seedance 2.0 capability claims must separate the model from the product surface. A feature can be true for the model while still being gated, unavailable, renamed, priced differently, or policy-limited on a specific surface.

Access note (2026-06-13): the overseas Seedance 2.0 API is contested following a copyright-driven suspension — see `api-status.md`. Verify live access on any third-party surface before relying on it, and add no surface here without independently confirming it hosts Seedance 2.0.

| Surface | Evidence type | Typical use | Current guidance |
|---|---|---|---|
| ByteDance Seed official model page | official | Broad capability framing | Use for high-level model positioning only. It confirms multimodal audio-video generation, references, performance, lighting, shadow, and camera control. |
| ByteDance official launch post | official | Capability details and known limits | Use for the strongest public claims about input modalities, reference counts, video extension/editing, dual-channel audio, and remaining weaknesses. |
| Volcengine Ark / ModelArk docs | official platform docs | API task flow and model surface | Recheck before giving endpoints, regions, quotas, pricing, or file limits. The May 29 model list/tutorial pages are current signals, but still date-bound. |
| Volcengine video-generation tutorial | official platform docs | Async task lifecycle, first/last-frame roles, return-last-frame, web-search tools, and reference-file combinations | Current May 29 signal for Volcengine fields. Use for Volcengine only; recheck exact schema, entitlement, pricing, and face-reference behavior before implementation. |
| Volcengine developer-community article | official ecosystem/news article | API availability, safety, and adoption context | Useful for noting API-service rollout, portrait/copyright standards, face verification, virtual portraits, and BytePlus overseas service. Do not treat it as an API schema, pricing table, or account entitlement guarantee. |
| BytePlus ModelArk docs | official platform docs | International API and docs surface | Recheck before production guidance. Some pages require JavaScript, so cite only visible or independently verified claims. Do not quote Seedance 2.0 BytePlus pricing from JS-only pages without live verification. |
| Runway Seedance 2 | official third-party surface | API/web generation with Seedance 2 model access | Runway documents `seedance2`, 5-15s duration, image/video/audio references, upload URIs, audio-combination rules, and plan/region caveats. Treat as Runway surface behavior, not Volcengine or BytePlus behavior. |
| Runway MCP | official agent connector surface | Agent-accessible image/video generation | Useful for agent workflow planning. It does not prove ByteDance API access or alter Seedance model limits. |
| fal | official third-party surface | API generation through fal's Seedance 2.0 endpoints | Verified 2026-06-09: fal documents text-to-video, image-to-video (start image plus optional end image), and reference-to-video, each with a /fast tier, 4-15s or auto duration, six aspect ratios plus auto, and per-second pricing. fal's prose guide says 480p/720p while model and pricing pages list 1080p - verify resolution per endpoint at call time. No extend endpoint on this surface. Treat as fal surface behavior, not Volcengine or BytePlus behavior. |
| Atlas Cloud | third-party aggregator surface | Hosted Seedance 2.0 via an async video-generation API | Verified 2026-06-13: Atlas Cloud hosts live Seedance 2.0 (text-to-video, image-to-video, reference-to-video, plus fast variants). Its OpenAI-compatible endpoint covers LLM/chat only; **Seedance video generation uses Atlas Cloud's own async API** - `POST /api/v1/model/generateVideo` with a model id such as `bytedance/seedance-2.0/text-to-video`, returning a prediction id polled at `/api/v1/model/prediction/{id}` - not the OpenAI SDK shape. One of several aggregators reselling Seedance access; treat endpoints, pricing, model IDs, quotas, and guardrails as aggregator-specific, recheck before use, and never present them as official ByteDance behavior. The repo endorses no reseller; listed for completeness. |
| Replicate | third-party model-host surface | Hosted Seedance 2.0 under the official `bytedance` namespace | Verified 2026-06-13: Replicate lists `bytedance/seedance-2.0` (text-to-video, image-to-video, multimodal reference inputs `[Image1]/[Video1]/[Audio1]`, native audio) behind its standard async prediction API; check the model page for supported resolutions rather than assuming model-level maximums. A reputable, widely-used model host — but still surface-specific: recheck pricing, limits, and live access (see the overseas-API status note in `api-status.md`), and never present its behavior as official ByteDance behavior. The repo endorses no host; listed for completeness. |
| Dreamina / Jimeng web UI | official product surface | Creator workflow | Behavior may differ from API. Do not generalize web UI limits, credits, face checks, or upload rules to every surface. |
| ComfyUI partner node docs | partner workflow docs | T2V, R2V, FLF2V workflows | Useful for workflow vocabulary and surface caveats. Label as ComfyUI-specific rather than universal Seedance behavior. |
| Third-party wrappers | community/commercial wrapper | Access abstraction | Useful for field patterns and integration ideas only. Do not present wrapper model names, prices, or guardrail behavior as official. |
| Community prompt corpora | field-observed | Prompt pattern mining | Mine structures, timing syntax, vocab, and failure modes. Do not copy unsafe, IP-sensitive, or real-person examples directly. |
| Agent Skills docs | agent packaging docs | Repository layout and install language | Use for skill structure and progressive-disclosure guidance. Do not treat repository install paths as universal client guarantees. |

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
