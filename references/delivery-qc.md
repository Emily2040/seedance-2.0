# Delivery And QC

Use this reference when output must be reviewed, handed to a client, prepared for platform upload, localized, archived, or delivered as part of a professional campaign.

## Delivery Preflight

| Area | Check |
|---|---|
| Picture | frame rate, resolution, aspect ratio, crop, safe area, stabilization, flicker, banding |
| Color | working space, look notes, HDR/SDR target, product/brand color, legal range if required |
| Audio | sync, loudness, true peak, dialogue clarity, stems, M&E, silence where intended |
| Text | captions, subtitles, forced narrative, on-screen copy, title-safe placement, script variant for languages that have one (Chinese: 简体 zh-Hans vs 繁體 zh-Hant) |
| Continuity | wardrobe, props, screen direction, product orientation, light direction, last-frame handoffs |
| Rights | references, music, voice, likeness, product/brand authorization, stock licenses |
| Metadata | job ID, model/surface, prompt version, seed/settings if available, source URLs, approval owner |
| Versioning | hero, cutdown, vertical, square, textless, localized, archival |
| Human QC | watch all outputs at normal speed and pause on fragile frames |

## Naming Pattern

Use consistent names:

`PROJECT_CAMPAIGN_VERSION_RATIO_LANG_DATE_STATUS`

Example:

`LUMA_BOTTLE_HERO_15S_9x16_TEXTLESS_2026-05-30_REVIEW01`

`LANG` must carry the script variant where the language has one, because two Chinese deliverables are not interchangeable: use `ZH-HANS` and `ZH-HANT` (or `ZH-TW` / `ZH-HK`) rather than a bare `ZH`. A file named `ZH` cannot be checked against its market, and the variant is not recoverable from the video. See Script Variant in `[ref:vocab/zh]`.

## Client Review Packet

Include:

- concept/treatment;
- shot list and accepted prompts;
- reference role map and rights notes;
- exported review links/files;
- known issues and recommended fixes;
- approval questions;
- delivery spec assumptions.

## QC Failure Routing

| Failure | Route |
|---|---|
| face/product/text drift | I2V lock, edit pass, composite in post, or regenerate from stable frame |
| continuity mismatch | update continuity ledger and regenerate only affected shot |
| color mismatch | grade/conform first; only regenerate if lighting intent is wrong |
| caption/text issue | remove generated text and add typography in post |
| loudness/sync issue | fix mix or edit timing; do not rely on prompt repair alone |
| unsafe or rights issue | rewrite to original/authorized material and document rights |

## Done Definition

A professional Seedance asset is done only when the creative owner approves the shot, the rights map is clean, continuity is tracked, the post handoff is explicit, and the delivery target has passed human QC.
