# Platform Constraints

last_verified: 2026-08-01

Reviewed 2026-08-01 against the official ByteDance Seedance 2.5 model page, the Dreamina product surface, and reports of a 2.0 4K tier. Nothing in the stable-constraint list below changed: these are 2.0 constraints, and they remain the working assumption for the model line this repository targets. Two cautions were added rather than edits made — a reported 4K tier on 2.0 does not lift the 480p/720p native baseline the model card documents, and none of these numbers may be carried across to Seedance 2.5. See [api-status](api-status.md).

## Stable constraints

- Do not assume every Seedance 2.0 surface has identical features.
- Do not assume API access, pricing, model IDs, regional access, upload limits, duration, or portrait authorization from memory.
- Do not infer consent from an uploaded image, voice, or video.
- Do not provide protected-character, celebrity, brand-logo, song-copying, exact-scene, or voice-imitation instructions without a safe rewrite or explicit authorization context.
- Do not treat real-face input as universally allowed or universally blocked. Some surfaces restrict direct human-face uploads while allowing verified virtual portrait assets, trusted same-account generated assets, or authorized material.
- Do not mix provider-specific field names: Volcengine first/last-frame roles, Runway `promptImage` positions, and wrapper schemas are not interchangeable.

## Surface-specific claims

When a user asks about Dreamina, Jimeng, Volcengine Ark, BytePlus ModelArk, Runway, ComfyUI, Replicate, Higgsfield, or another surface, answer with the surface name and date. Label unofficial/community tools clearly.

## User-facing default

Platform support varies by surface. Check current official documentation before production planning.
